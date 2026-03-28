"""Render scored papers into a Markdown daily report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template
from zoneinfo import ZoneInfo

try:
    from .utils import ensure_directory, parse_datetime
except ImportError:
    from utils import ensure_directory, parse_datetime


REPORT_TEMPLATE = Template(
    """# 论文雷达 - {{ report_date }}

{% if must_read %}
## 必看
{% for paper in must_read %}
### {{ loop.index }}. {{ paper.title }}
- 分数：{{ paper.score }}
- 发布时间：{{ paper.published_date }}
- 来源：{{ paper.sources }}
- 标签：{{ paper.tags_text }}
- 作者：{{ paper.authors_text }}
- 链接：{{ paper.abs_url }}
- 一句话总结：{{ paper.one_line_summary }}
- 推荐理由：
{% for reason in paper.recommendation_reasons %}
  - {{ reason }}
{% endfor %}
{% endfor %}
{% endif %}
{% if quick_scan %}
## 值得扫摘要
{% for paper in quick_scan %}
### {{ loop.index }}. {{ paper.title }}
- 分数：{{ paper.score }}
- 发布时间：{{ paper.published_date }}
- 来源：{{ paper.sources }}
- 标签：{{ paper.tags_text }}
- 作者：{{ paper.authors_text }}
- 链接：{{ paper.abs_url }}
- 一句话总结：{{ paper.one_line_summary }}
- 推荐理由：
{% for reason in paper.recommendation_reasons %}
  - {{ reason }}
{% endfor %}
{% endfor %}
{% endif %}
"""
)


def _decorate_paper(paper: dict[str, Any], timezone: str) -> dict[str, Any]:
    published = parse_datetime(paper.get("published_at"), timezone)
    sources = ["arXiv"]
    if paper.get("in_hf_daily"):
        sources.append("HF Daily")
    if paper.get("in_hf_trending"):
        sources.append("HF Trending")
    return {
        **paper,
        "published_date": published.date().isoformat() if published else "unknown",
        "sources": ", ".join(sources),
        "tags_text": ", ".join(paper.get("tags", [])) or "无",
        "authors_text": ", ".join(paper.get("authors", [])) or "未知",
    }


def render_report(
    papers: list[dict[str, Any]],
    settings: dict[str, Any],
    output_path: Path,
    now: datetime | None = None,
) -> str:
    """Render a Markdown report and write it to disk."""
    timezone = settings["timezone"]
    must_read_threshold = settings["push_threshold_must_read"]
    quick_scan_threshold = settings["push_threshold_quick_scan"]
    max_items = settings["max_items_in_report"]
    report_now = now or datetime.now(ZoneInfo(timezone))
    if report_now.tzinfo is None:
        report_now = report_now.replace(tzinfo=ZoneInfo(timezone))
    else:
        report_now = report_now.astimezone(ZoneInfo(timezone))
    report_date = report_now.date().isoformat()

    must_read = [
        _decorate_paper(paper, timezone) for paper in papers if paper.get("score", 0) >= must_read_threshold
    ][:max_items]
    remaining_slots = max(0, max_items - len(must_read))
    quick_scan = [
        _decorate_paper(paper, timezone)
        for paper in papers
        if quick_scan_threshold <= paper.get("score", 0) < must_read_threshold
    ][:remaining_slots]

    content = REPORT_TEMPLATE.render(report_date=report_date, must_read=must_read, quick_scan=quick_scan).strip() + "\n"
    ensure_directory(output_path.parent)
    output_path.write_text(content, encoding="utf-8")
    return content
