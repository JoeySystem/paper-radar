# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project aims to follow Semantic Versioning for tagged releases.

## [Unreleased]

### Added
- `bootstrap.sh` for one-command local setup.
- `Dockerfile` for containerized runs.
- Config validation with clearer startup errors.
- Bilingual one-line summaries in `zh-CN` and `en-US`.
- arXiv API fallback when RSS feeds return empty results.
- Report size control to keep the daily digest within 3 to 5 papers.
- Initial contributor-facing project docs and templates.

### Changed
- Ranking now requires topic or priority-author alignment before a paper enters the report.
- Markdown output is now a curated shortlist instead of a long scan list.
- CLI output now includes a short human-readable run summary.

## [0.1.0] - 2026-03-28

### Added
- Initial public release of `paper-radar`.
- arXiv, Hugging Face Papers, scoring, matching, storage, and Markdown rendering pipeline.
- SQLite storage with JSON fallback.
- Local run, cron, and GitHub Actions support.
- Basic pytest coverage for matching, scoring, rendering, utility helpers, and arXiv fallback behavior.
