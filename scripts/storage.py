"""Persistence layer for paper-radar with SQLite and JSON fallback."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .utils import dump_json, ensure_directory, utc_now
except ImportError:
    from utils import dump_json, ensure_directory, utc_now


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_status_json TEXT NOT NULL,
    total_papers INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id TEXT,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL,
    summary TEXT,
    published_at TEXT,
    abs_url TEXT,
    pdf_url TEXT,
    source_category TEXT,
    score REAL,
    in_hf_daily INTEGER NOT NULL DEFAULT 0,
    in_hf_trending INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id TEXT,
    hf_match_confidence REAL,
    matched_at TEXT NOT NULL
);
"""


class StorageBackend:
    """Persist papers and metadata into SQLite or JSON."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.raw_dir = base_dir / "raw"
        self.processed_dir = base_dir / "processed"
        self.db_path = base_dir / "radar.db"
        self.mode = "sqlite"
        self.connection: sqlite3.Connection | None = None

    def initialize(self) -> str:
        """Initialize persistence and return the active mode."""
        ensure_directory(self.base_dir)
        ensure_directory(self.raw_dir)
        ensure_directory(self.processed_dir)
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.executescript(SCHEMA)
            self.connection.commit()
            self.mode = "sqlite"
        except sqlite3.Error:
            self.mode = "json"
            self.connection = None
        return self.mode

    def save_raw(self, payload: dict[str, Any], name: str) -> None:
        """Write raw source payloads to JSON."""
        timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        dump_json(self.raw_dir / f"{timestamp}_{name}.json", payload)

    def save_processed(
        self,
        papers: list[dict[str, Any]],
        source_status: dict[str, Any],
        started_at: datetime,
    ) -> None:
        """Persist processed papers and run metadata."""
        timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        dump_json(self.processed_dir / f"{timestamp}_papers.json", papers)
        if self.mode == "sqlite" and self.connection is not None:
            self._save_sqlite(papers, source_status, started_at)

    def _save_sqlite(
        self,
        papers: list[dict[str, Any]],
        source_status: dict[str, Any],
        started_at: datetime,
    ) -> None:
        assert self.connection is not None
        created_at = utc_now().isoformat()
        self.connection.execute(
            """
            INSERT INTO runs (started_at, created_at, source_status_json, total_papers)
            VALUES (?, ?, ?, ?)
            """,
            (started_at.isoformat(), created_at, json.dumps(source_status), len(papers)),
        )
        for paper in papers:
            self.connection.execute(
                """
                INSERT INTO papers (
                    arxiv_id, title, authors_json, summary, published_at, abs_url, pdf_url,
                    source_category, score, in_hf_daily, in_hf_trending, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper.get("arxiv_id"),
                    paper.get("title"),
                    json.dumps(paper.get("authors", []), ensure_ascii=False),
                    paper.get("summary"),
                    paper.get("published_at"),
                    paper.get("abs_url"),
                    paper.get("pdf_url"),
                    paper.get("source_category"),
                    paper.get("score"),
                    int(bool(paper.get("in_hf_daily"))),
                    int(bool(paper.get("in_hf_trending"))),
                    created_at,
                ),
            )
            self.connection.execute(
                """
                INSERT INTO matches (arxiv_id, hf_match_confidence, matched_at)
                VALUES (?, ?, ?)
                """,
                (
                    paper.get("arxiv_id"),
                    paper.get("hf_match_confidence", 0.0),
                    created_at,
                ),
            )
        self.connection.commit()
