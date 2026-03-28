"""Shared utilities for paper-radar."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import yaml
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo


LOGGER = logging.getLogger("paper_radar")
DEFAULT_HEADERS = {
    "User-Agent": "paper-radar/0.1 (+https://github.com/example/paper-radar)"
}


def configure_logging(level: str = "INFO") -> None:
    """Configure project-wide logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def project_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parent.parent


def ensure_directory(path: Path) -> None:
    """Create a directory when it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def dump_json(path: Path, payload: Any) -> None:
    """Write JSON to disk."""
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_json(path: Path, default: Any) -> Any:
    """Read JSON from disk or return a default value."""
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_datetime(value: str | datetime | None, timezone: str = "UTC") -> datetime | None:
    """Parse a datetime-like value and normalize it to the configured timezone."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = date_parser.parse(value)
    tz = ZoneInfo(timezone)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(tz=ZoneInfo("UTC"))


def normalize_title(title: str) -> str:
    """Normalize a title for exact and fuzzy matching."""
    lowered = title.lower().strip()
    lowered = re.sub(r"[\W_]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def collapse_whitespace(text: str) -> str:
    """Collapse repeated whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def summarize_text(text: str, max_length: int = 80) -> str:
    """Produce a short one-line summary snippet from a longer text."""
    compact = collapse_whitespace(text)
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "…"


def within_lookback(
    published_at: str | datetime | None,
    lookback_days: int,
    timezone: str,
    now: datetime | None = None,
) -> bool:
    """Check whether a timestamp falls within the lookback window."""
    dt = parse_datetime(published_at, timezone)
    if dt is None:
        return False
    current = now.astimezone(ZoneInfo(timezone)) if now else datetime.now(ZoneInfo(timezone))
    return dt >= current - timedelta(days=lookback_days)


def request_with_retry(
    url: str,
    timeout: int = 20,
    retries: int = 2,
    session: requests.Session | None = None,
) -> requests.Response:
    """Fetch a URL with simple retry handling."""
    client = session or requests.Session()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= retries:
                break
            LOGGER.warning("request failed for %s (attempt %s/%s): %s", url, attempt + 1, retries + 1, exc)
    assert last_error is not None
    raise last_error


def extract_arxiv_id(url: str) -> str:
    """Extract an arXiv identifier from a URL."""
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", url)
    return match.group(1).replace(".pdf", "") if match else ""


def infer_tags(title: str, summary: str, keywords: dict[str, list[str]]) -> list[str]:
    """Infer a small set of tags from configured keywords."""
    haystack = f"{title} {summary}".lower()
    tags: list[str] = []
    for keyword in keywords.get("high_priority", []) + keywords.get("medium_priority", []):
        if keyword.lower() in haystack and keyword not in tags:
            tags.append(keyword)
    return tags[:5]
