"""Fetch Daily and Trending paper hints from Hugging Face Papers."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

try:
    from .utils import collapse_whitespace, request_with_retry
except ImportError:
    from utils import collapse_whitespace, request_with_retry


LOGGER = logging.getLogger("paper_radar.fetch_hf")


def _extract_score_hint(text: str) -> float | None:
    """Extract a basic numeric heat hint from text."""
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _infer_section(url: str) -> str:
    """Infer the HF section from the page URL."""
    return "trending" if "trending" in url else "daily"


def _extract_candidates(soup: BeautifulSoup, url: str) -> list[dict[str, Any]]:
    """Extract candidate paper cards from the current HF HTML structure."""
    section = _infer_section(url)
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        if not href.startswith("/papers/"):
            continue
        title = collapse_whitespace(anchor.get_text(" ", strip=True))
        if len(title) < 12:
            continue
        container = anchor.parent
        surrounding_text = collapse_whitespace(container.get_text(" ", strip=True)) if container else title
        paper_url = ""
        for nested in container.select("a[href]") if container else []:
            nested_href = nested.get("href", "")
            if "arxiv.org/abs/" in nested_href or "arxiv.org/pdf/" in nested_href:
                paper_url = nested_href
                break
        item = {
            "title": title,
            "hf_url": f"https://huggingface.co{href}",
            "paper_url": paper_url,
            "score_hint": _extract_score_hint(surrounding_text),
            "section": section,
            "date": datetime.utcnow().date().isoformat(),
            "authors": [],
        }
        if item["hf_url"] and (item["title"], item["hf_url"]) not in seen:
            results.append(item)
            seen.add((item["title"], item["hf_url"]))
    return results


def fetch_hf(
    page_urls: list[str],
    timeout: int = 20,
    retries: int = 2,
) -> list[dict[str, Any]]:
    """Fetch Hugging Face paper lists. Failures degrade to warnings and empty results."""
    results: list[dict[str, Any]] = []
    for page_url in page_urls:
        try:
            response = request_with_retry(page_url, timeout=timeout, retries=retries)
            soup = BeautifulSoup(response.text, "lxml")
            page_results = _extract_candidates(soup, page_url)
            if not page_results:
                LOGGER.warning("no HF paper items extracted from %s", page_url)
            results.extend(page_results)
        except Exception as exc:
            LOGGER.warning("failed to fetch HF papers page %s: %s", page_url, exc)
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in results:
        key = (item["title"].lower(), item["section"])
        deduped[key] = item
    return list(deduped.values())
