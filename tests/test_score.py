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
    settings = {"timezone": "UTC", "must_contain_any_keyword": False}

    result = score_paper(
        paper,
        keywords,
        authors,
        settings,
        now=datetime.fromisoformat("2026-03-28T00:00:00+00:00"),
    )

    assert result["score"] >= 11
    assert "命中高优先级关键词" in result["recommendation_reasons"]
