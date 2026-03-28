"""Fetch and normalize arXiv RSS entries."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus
from typing import Any

import feedparser

try:
    from .utils import extract_arxiv_id, request_with_retry, within_lookback
except ImportError:
    from utils import extract_arxiv_id, request_with_retry, within_lookback


LOGGER = logging.getLogger("paper_radar.fetch_arxiv")
ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _parse_description(description: str) -> str:
    """Extract the abstract text from an RSS description field."""
    match = re.search(r"Abstract:\s*(.*)", description, flags=re.DOTALL)
    return match.group(1).strip() if match else description.strip()


def _category_from_feed_url(feed_url: str) -> str:
    """Infer an arXiv category from a feed URL."""
    return feed_url.rstrip("/").split("/")[-1]


def _entry_to_paper(entry: Any, feed_url: str) -> dict[str, Any]:
    """Convert a feedparser entry into the project paper schema."""
    abs_url = entry.get("link", "")
    arxiv_id = extract_arxiv_id(abs_url) or entry.get("id", "").split(":")[-1]
    categories = entry.get("tags", []) or []
    source_categories = [item.get("term", "") for item in categories if item.get("term")]
    creator = entry.get("dc_creator") or entry.get("author", "")
    authors = [author.strip() for author in creator.split(",") if author.strip()]
    summary = _parse_description(entry.get("description", ""))
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""
    return {
        "source": "arXiv",
        "source_method": "rss",
        "source_feed": feed_url,
        "source_category": source_categories[0] if source_categories else "",
        "source_categories": source_categories,
        "title": entry.get("title", "").strip(),
        "authors": authors,
        "summary": summary,
        "published_at": entry.get("published") or entry.get("pubDate"),
        "updated_at": entry.get("updated") or entry.get("published") or entry.get("pubDate"),
        "arxiv_id": arxiv_id,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
    }


def _api_entry_to_paper(entry: Any, category: str, api_url: str) -> dict[str, Any]:
    """Convert an arXiv API Atom entry into the project paper schema."""
    abs_url = entry.get("id", "").strip()
    arxiv_id = extract_arxiv_id(abs_url)
    links = entry.get("links", []) or []
    pdf_url = ""
    for link in links:
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href", "")
            break
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    authors = [author.get("name", "").strip() for author in entry.get("authors", []) if author.get("name")]
    source_categories = [item.get("term", "") for item in entry.get("tags", []) if item.get("term")]
    return {
        "source": "arXiv",
        "source_method": "api",
        "source_feed": api_url,
        "source_category": category,
        "source_categories": source_categories or [category],
        "title": (entry.get("title") or "").strip(),
        "authors": authors,
        "summary": (entry.get("summary") or "").strip(),
        "published_at": entry.get("published"),
        "updated_at": entry.get("updated") or entry.get("published"),
        "arxiv_id": arxiv_id,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
    }


def _fetch_api_fallback(
    category: str,
    lookback_days: int,
    timezone: str,
    timeout: int,
    retries: int,
    max_results: int,
) -> list[dict[str, Any]]:
    """Fetch recent papers from the official arXiv API when RSS is empty."""
    query = quote_plus(f"cat:{category}")
    api_url = (
        f"{ARXIV_API_URL}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    try:
        response = request_with_retry(api_url, timeout=timeout, retries=retries)
        parsed = feedparser.parse(response.content)
    except Exception as exc:
        LOGGER.warning("failed to fetch arXiv API fallback for %s: %s", category, exc)
        return []

    papers: list[dict[str, Any]] = []
    for entry in parsed.entries:
        paper = _api_entry_to_paper(entry, category, api_url)
        if not within_lookback(paper["published_at"], lookback_days, timezone):
            continue
        papers.append(paper)
    LOGGER.info("arXiv API fallback returned %s papers for %s", len(papers), category)
    return papers


def fetch_arxiv(
    feed_urls: list[str],
    lookback_days: int,
    timezone: str,
    timeout: int = 20,
    retries: int = 2,
    api_max_results: int = 200,
) -> list[dict[str, Any]]:
    """Fetch arXiv RSS feeds and return normalized papers."""
    deduped: dict[str, dict[str, Any]] = {}
    for feed_url in feed_urls:
        category = _category_from_feed_url(feed_url)
        papers_from_source: list[dict[str, Any]] = []
        try:
            response = request_with_retry(feed_url, timeout=timeout, retries=retries)
            parsed = feedparser.parse(response.content)
        except Exception as exc:
            LOGGER.warning("failed to fetch arXiv feed %s: %s", feed_url, exc)
            parsed = None

        if parsed and parsed.entries:
            for entry in parsed.entries:
                paper = _entry_to_paper(entry, feed_url)
                if within_lookback(paper["published_at"], lookback_days, timezone):
                    papers_from_source.append(paper)
        else:
            LOGGER.warning("arXiv RSS returned no items for %s; falling back to API", category)
            papers_from_source.extend(
                _fetch_api_fallback(
                    category=category,
                    lookback_days=lookback_days,
                    timezone=timezone,
                    timeout=timeout,
                    retries=retries,
                    max_results=api_max_results,
                )
            )

        for paper in papers_from_source:
            identity = paper["arxiv_id"] or paper["abs_url"] or paper["title"].lower()
            existing = deduped.get(identity)
            if existing is None:
                deduped[identity] = paper
                continue
            merged_categories = sorted(
                set(existing.get("source_categories", [])) | set(paper.get("source_categories", []))
            )
            existing["source_categories"] = merged_categories
            if not existing.get("source_category") and merged_categories:
                existing["source_category"] = merged_categories[0]
            if existing.get("source_method") != "rss" and paper.get("source_method") == "rss":
                existing["source_method"] = "rss"
                existing["source_feed"] = paper.get("source_feed", existing.get("source_feed"))
    return list(deduped.values())
