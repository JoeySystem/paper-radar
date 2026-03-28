from datetime import datetime

from scripts.utils import normalize_title, within_lookback


def test_normalize_title_strips_punctuation_and_case():
    assert normalize_title("Attention Residuals: A Study!!") == "attention residuals a study"


def test_within_lookback_filters_old_items():
    now = datetime.fromisoformat("2026-03-28T00:00:00+00:00")
    assert within_lookback("2026-03-25T12:00:00+00:00", 7, "UTC", now=now) is True
    assert within_lookback("2026-03-10T12:00:00+00:00", 7, "UTC", now=now) is False
