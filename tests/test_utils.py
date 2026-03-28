from datetime import datetime

from scripts.utils import normalize_title, validate_config, within_lookback


def test_normalize_title_strips_punctuation_and_case():
    assert normalize_title("Attention Residuals: A Study!!") == "attention residuals a study"


def test_within_lookback_filters_old_items():
    now = datetime.fromisoformat("2026-03-28T00:00:00+00:00")
    assert within_lookback("2026-03-25T12:00:00+00:00", 7, "UTC", now=now) is True
    assert within_lookback("2026-03-10T12:00:00+00:00", 7, "UTC", now=now) is False


def test_validate_config_detects_invalid_thresholds():
    config = {
        "keywords": {
            "high_priority": [],
            "medium_priority": [],
            "negative_keywords": [],
        },
        "authors": {
            "priority_orgs": [],
            "priority_authors": [],
        },
        "sources": {
            "arxiv_feeds": ["https://rss.arxiv.org/rss/cs.CL"],
            "hf_pages": [],
        },
        "settings": {
            "lookback_days": 7,
            "push_threshold_must_read": 5,
            "push_threshold_quick_scan": 8,
            "max_items_in_report": 15,
            "min_items_in_report": 3,
            "request_timeout": 20,
            "request_retries": 2,
            "arxiv_api_max_results": 200,
            "fuzzy_match_threshold": 0.9,
            "timezone": "UTC",
            "require_topic_or_priority_for_report": True,
        },
    }

    errors = validate_config(config)

    assert any("push_threshold_quick_scan" in error for error in errors)
