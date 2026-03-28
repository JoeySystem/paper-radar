"""Main entrypoint for the paper-radar pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .fetch_arxiv import fetch_arxiv
    from .fetch_hf import fetch_hf
    from .match_sources import match_papers
    from .render_md import render_report
    from .score import score_paper
    from .storage import StorageBackend
    from .utils import configure_logging, load_yaml, project_root, validate_config
except ImportError:
    from fetch_arxiv import fetch_arxiv
    from fetch_hf import fetch_hf
    from match_sources import match_papers
    from render_md import render_report
    from score import score_paper
    from storage import StorageBackend
    from utils import configure_logging, load_yaml, project_root, validate_config


LOGGER = logging.getLogger("paper_radar.main")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Daily paper radar for LLM and architecture research.")
    parser.add_argument("--lookback-days", type=int, default=None, help="Override lookback days from config.")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without persisting data.")
    parser.add_argument("--output-path", type=str, default=None, help="Override Markdown output path.")
    parser.add_argument("--fuzzy-threshold", type=float, default=None, help="Override title fuzzy match threshold.")
    return parser


def load_config(root: Path) -> dict[str, Any]:
    """Load project configuration from config directory."""
    config_dir = root / "config"
    return {
        "keywords": load_yaml(config_dir / "keywords.yaml"),
        "authors": load_yaml(config_dir / "authors.yaml"),
        "sources": load_yaml(config_dir / "sources.yaml"),
        "settings": load_yaml(config_dir / "settings.yaml"),
    }


def print_run_summary(
    output_path: Path,
    arxiv_count: int,
    hf_count: int,
    scored_count: int,
    dry_run: bool,
) -> None:
    """Print a short, user-friendly run summary."""
    mode = "dry-run" if dry_run else "full run"
    print("")
    print("paper-radar run summary")
    print(f"- Mode: {mode}")
    print(f"- arXiv papers fetched: {arxiv_count}")
    print(f"- Hugging Face paper hints fetched: {hf_count}")
    print(f"- Papers scored: {scored_count}")
    print(f"- Report written to: {output_path}")
    print("- Next step: open the Markdown report in Obsidian or your editor.")


def dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate arXiv papers, keeping the highest score candidate later in the pipeline."""
    deduped: dict[str, dict[str, Any]] = {}
    for paper in papers:
        key = paper.get("arxiv_id") or paper.get("abs_url") or paper.get("title", "").lower()
        existing = deduped.get(key)
        if existing is None or paper.get("score", 0) > existing.get("score", 0):
            deduped[key] = paper
    return list(deduped.values())


def run(args: argparse.Namespace) -> int:
    """Execute the full radar pipeline."""
    root = project_root()
    try:
        config = load_config(root)
    except Exception as exc:
        LOGGER.error("failed to load config: %s", exc)
        return 1
    config_errors = validate_config(config)
    if config_errors:
        LOGGER.error("configuration validation failed")
        for error in config_errors:
            LOGGER.error("%s", error)
        print("")
        print("paper-radar configuration errors")
        for error in config_errors:
            print(f"- {error}")
        print("- Fix the files above, then rerun `paper-radar --dry-run`.")
        return 1

    settings = config["settings"]
    if args.lookback_days is not None:
        settings["lookback_days"] = args.lookback_days
    if args.fuzzy_threshold is not None:
        settings["fuzzy_match_threshold"] = args.fuzzy_threshold

    output_path = Path(args.output_path) if args.output_path else root / "output" / "papers_today.md"
    started_at = datetime.now(UTC)
    source_status = {"arxiv_ok": False, "hf_ok": False}

    arxiv_papers = fetch_arxiv(
        config["sources"].get("arxiv_feeds", []),
        lookback_days=settings["lookback_days"],
        timezone=settings["timezone"],
        timeout=settings.get("request_timeout", 20),
        retries=settings.get("request_retries", 2),
        api_max_results=settings.get("arxiv_api_max_results", 200),
    )
    source_status["arxiv_ok"] = bool(arxiv_papers)

    hf_papers = fetch_hf(
        config["sources"].get("hf_pages", []),
        timeout=settings.get("request_timeout", 20),
        retries=settings.get("request_retries", 2),
    )
    source_status["hf_ok"] = bool(hf_papers)

    if not any(source_status.values()):
        LOGGER.error("all data sources failed")
        return 2

    matched = match_papers(
        dedupe_papers(arxiv_papers),
        hf_papers,
        fuzzy_threshold=settings.get("fuzzy_match_threshold", 0.9),
    )
    scored = [
        score_paper(
            paper,
            config["keywords"],
            config["authors"],
            settings,
        )
        for paper in matched
    ]
    scored = dedupe_papers(scored)
    scored.sort(key=lambda item: (item.get("score", 0), item.get("published_at", "")), reverse=True)

    if not args.dry_run:
        storage = StorageBackend(root / "data")
        storage_mode = storage.initialize()
        LOGGER.info("storage mode: %s", storage_mode)
        storage.save_raw({"arxiv": arxiv_papers, "hf": hf_papers}, "sources")
        storage.save_processed(scored, source_status, started_at)
    else:
        LOGGER.info("storage skipped due to dry-run")

    try:
        render_report(scored, settings, output_path)
    except Exception as exc:
        LOGGER.error("failed to render report: %s", exc)
        return 3

    LOGGER.info(
        "run completed: arxiv=%s hf=%s scored=%s output=%s",
        len(arxiv_papers),
        len(hf_papers),
        len(scored),
        output_path,
    )
    print_run_summary(
        output_path=output_path,
        arxiv_count=len(arxiv_papers),
        hf_count=len(hf_papers),
        scored_count=len(scored),
        dry_run=args.dry_run,
    )
    return 0


def main() -> int:
    """CLI entrypoint."""
    configure_logging()
    parser = build_arg_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
