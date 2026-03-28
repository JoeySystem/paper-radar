from datetime import datetime

from scripts.score import score_paper


def test_score_paper_combines_relevance_freshness_and_heat():
    paper = {
        "title": "Linear Attention with Residual Connection",
        "summary": "This work studies training dynamics and memory efficiency.",
        "authors": ["Jane Doe"],
        "published_at": "2026-03-27T00:00:00+00:00",
        "in_hf_daily": True,
        "in_hf_trending": False,
    }
    keywords = {
        "high_priority": ["linear attention", "residual connection", "training dynamics"],
        "medium_priority": ["memory"],
        "negative_keywords": [],
    }
    authors = {"priority_authors": ["Jane Doe"], "priority_orgs": []}
    settings = {
        "timezone": "UTC",
        "must_contain_any_keyword": False,
        "require_topic_or_priority_for_report": True,
    }

    result = score_paper(
        paper,
        keywords,
        authors,
        settings,
        now=datetime.fromisoformat("2026-03-28T00:00:00+00:00"),
    )

    assert result["score"] >= 11
    assert "命中高优先级关键词" in result["recommendation_reasons"]
    assert "zh-CN" in result["one_line_summary"]
    assert "en-US" in result["one_line_summary"]
    assert "核心内容是" in result["one_line_summary"]["zh-CN"]
    assert "centers on" in result["one_line_summary"]["en-US"]


def test_off_topic_hot_paper_is_not_report_eligible():
    paper = {
        "title": "PixelSmile Toward Fine-Grained Facial Expression Editing",
        "summary": "A computer vision paper about facial editing.",
        "authors": ["Jane Doe"],
        "published_at": "2026-03-27T00:00:00+00:00",
        "in_hf_daily": True,
        "in_hf_trending": True,
    }
    keywords = {
        "high_priority": ["linear attention", "residual connection", "training dynamics"],
        "medium_priority": ["memory"],
        "negative_keywords": [],
    }
    authors = {"priority_authors": [], "priority_orgs": []}
    settings = {
        "timezone": "UTC",
        "must_contain_any_keyword": False,
        "require_topic_or_priority_for_report": True,
    }

    result = score_paper(
        paper,
        keywords,
        authors,
        settings,
        now=datetime.fromisoformat("2026-03-28T00:00:00+00:00"),
    )

    assert result["is_report_eligible"] is False
    assert result["score"] < 8
