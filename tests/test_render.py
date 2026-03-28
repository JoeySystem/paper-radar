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
            "one_line_summary": {
                "zh-CN": "改的是层间 residual。",
                "en-US": "The paper focuses on inter-layer residual paths.",
            },
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
            "one_line_summary": {
                "zh-CN": "建议快速扫摘要。",
                "en-US": "A quick abstract scan is enough for the first pass.",
            },
            "in_hf_daily": False,
            "in_hf_trending": False,
        },
    ]
    settings = {
        "timezone": "America/Los_Angeles",
        "push_threshold_must_read": 8,
        "push_threshold_quick_scan": 5,
        "max_items_in_report": 5,
        "min_items_in_report": 3,
    }

    output_path = tmp_path / "papers_today.md"
    content = render_report(papers, settings, output_path, now=datetime(2026, 3, 28))

    assert "## 必看" in content
    assert "## 值得扫摘要" in content
    assert "一句话总结（中文）" in content
    assert "One-line summary (en-US)" in content
    assert output_path.exists()


def test_render_report_limits_total_items_to_five(tmp_path: Path):
    papers = []
    for index in range(6):
        papers.append(
            {
                "title": f"Paper {index}",
                "score": 7 - index * 0.1,
                "published_at": "2026-03-27T10:00:00+00:00",
                "abs_url": f"https://arxiv.org/abs/2603.12{index}",
                "authors": ["Jane Doe"],
                "tags": ["routing"],
                "recommendation_reasons": ["命中中优先级关键词"],
                "one_line_summary": {
                    "zh-CN": "测试中文摘要。",
                    "en-US": "Test English summary.",
                },
                "in_hf_daily": False,
                "in_hf_trending": False,
                "is_report_eligible": True,
            }
        )

    settings = {
        "timezone": "America/Los_Angeles",
        "push_threshold_must_read": 8,
        "push_threshold_quick_scan": 5,
        "max_items_in_report": 5,
        "min_items_in_report": 3,
    }

    output_path = tmp_path / "papers_today.md"
    content = render_report(papers, settings, output_path, now=datetime(2026, 3, 28))

    assert content.count("### ") == 5
