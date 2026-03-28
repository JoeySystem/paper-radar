"""Fetch and normalize arXiv RSS entries."""

from __future__ import annotations

import logging
import re
from typing import Any

import feedparser

try:
    from .utils import extract_arxiv_id, request_with_retry, within_lookback
except ImportError:
    from utils import extract_arxiv_id, request_with_retry, within_lookback


LOGGER = logging.getLogger("paper_radar.fetch_arxiv")


def _parse_description(description: str) -> str:
    """Extract the abstract text from an RSS description field."""
    match = re.search(r"Abstract:\s*(.*)", description, flags=re.DOTALL)
    return match.group(1).strip() if match else description.strip()


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


def fetch_arxiv(
    feed_urls: list[str],
    lookback_days: int,
    timezone: str,
    timeout: int = 20,
    retries: int = 2,
) -> list[dict[str, Any]]:
    """Fetch arXiv RSS feeds and return normalized papers."""
    deduped: dict[str, dict[str, Any]] = {}
    for feed_url in feed_urls:
        try:
            response = request_with_retry(feed_url, timeout=timeout, retries=retries)
            parsed = feedparser.parse(response.content)
        except Exception as exc:
            LOGGER.warning("failed to fetch arXiv feed %s: %s", feed_url, exc)
            continue
        for entry in parsed.entries:
            paper = _entry_to_paper(entry, feed_url)
            identity = paper["arxiv_id"] or paper["abs_url"] or paper["title"].lower()
            if not within_lookback(paper["published_at"], lookback_days, timezone):
                continue
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
    return list(deduped.values())
