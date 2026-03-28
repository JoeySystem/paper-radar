from datetime import datetime
from pathlib import Path

from scripts.render_md import render_report


def test_render_report_groups_items(tmp_path: Path):
    papers = [
        {
            "title": "Attention Residuals",
            "score": 9,
            "published_at": "2026-03-27T10:00:00+00:00",
            "abs_url": "https://arxiv.org/abs/2603.12345",
            "authors": ["Jane Doe"],
            "tags": ["residual connection"],
            "recommendation_reasons": ["命中高优先级关键词"],
            "one_line_summary": "改的是层间 residual。",
            "in_hf_daily": True,
            "in_hf_trending": False,
        },
        {
            "title": "Efficient Attention Tricks",
            "score": 5,
            "published_at": "2026-03-26T10:00:00+00:00",
            "abs_url": "https://arxiv.org/abs/2603.23456",
            "authors": ["John Doe"],
            "tags": ["efficient attention"],
            "recommendation_reasons": ["命中中优先级关键词"],
            "one_line_summary": "建议快速扫摘要。",
            "in_hf_daily": False,
            "in_hf_trending": False,
        },
    ]
    settings = {
        "timezone": "America/Los_Angeles",
        "push_threshold_must_read": 8,
        "push_threshold_quick_scan": 5,
        "max_items_in_report": 15,
    }

    output_path = tmp_path / "papers_today.md"
    content = render_report(papers, settings, output_path, now=datetime(2026, 3, 28))

    assert "## 必看" in content
    assert "## 值得扫摘要" in content
    assert output_path.exists()
