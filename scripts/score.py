"""Scoring logic for paper-radar."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from .utils import infer_tags, parse_datetime
except ImportError:
    from utils import infer_tags, parse_datetime


@dataclass
class ScoreBreakdown:
    """Detailed score components for a paper."""

    freshness_score: float = 0.0
    relevance_score: float = 0.0
    author_score: float = 0.0
    heat_score: float = 0.0
    penalty_score: float = 0.0

    @property
    def total(self) -> float:
        return self.freshness_score + self.relevance_score + self.author_score + self.heat_score - self.penalty_score


def _count_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword and keyword.lower() in lowered)


def _freshness_score(published_at: str | None, timezone: str, now: datetime | None) -> float:
    if not published_at:
        return 0.0
    current = now or datetime.now(parse_datetime(published_at, timezone).tzinfo)
    published = parse_datetime(published_at, timezone)
    if published is None:
        return 0.0
    age_days = (current - published).total_seconds() / 86400
    if age_days <= 3:
        return 3.0
    if age_days <= 7:
        return 2.0
    return 0.0


def _author_score(paper: dict[str, Any], authors_cfg: dict[str, list[str]]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    authors = [author.lower() for author in paper.get("authors", [])]
    text_fields = " ".join(
        [
            paper.get("title", ""),
            paper.get("summary", ""),
            " ".join(paper.get("authors", [])),
        ]
    ).lower()
    priority_authors = [item.lower() for item in authors_cfg.get("priority_authors", []) if item]
    priority_orgs = [item.lower() for item in authors_cfg.get("priority_orgs", []) if item]
    if any(candidate in author for author in authors for candidate in priority_authors):
        score += 3.0
        reasons.append("命中重点作者")
    if any(org in text_fields for org in priority_orgs):
        score += 3.0
        reasons.append("命中重点团队")
    return score, reasons


def _heat_score(paper: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if paper.get("in_hf_daily"):
        score += 3.0
        reasons.append("出现在 HF Daily")
    if paper.get("in_hf_trending"):
        score += 5.0
        reasons.append("出现在 HF Trending")
    score_hint = paper.get("hf_score_hint")
    if isinstance(score_hint, (int, float)):
        if score_hint >= 100:
            score += 2.0
        elif score_hint >= 30:
            score += 1.0
    return score, reasons


def _relevance_and_penalty(
    paper: dict[str, Any],
    keywords_cfg: dict[str, list[str]],
    settings: dict[str, Any],
) -> tuple[float, float, int, list[str]]:
    title = paper.get("title", "")
    summary = paper.get("summary", "")
    reasons: list[str] = []
    relevance = 0.0
    penalty = 0.0

    high_priority = keywords_cfg.get("high_priority", [])
    medium_priority = keywords_cfg.get("medium_priority", [])
    negative_keywords = keywords_cfg.get("negative_keywords", [])

    title_high_hits = _count_hits(title, high_priority)
    summary_high_hits = _count_hits(summary, high_priority)
    title_medium_hits = _count_hits(title, medium_priority)
    summary_medium_hits = _count_hits(summary, medium_priority)
    negative_hits = _count_hits(f"{title} {summary}", negative_keywords)

    relevance += title_high_hits * 2.0
    relevance += summary_high_hits * 1.0
    relevance += title_medium_hits * 1.0
    relevance += summary_medium_hits * 0.5
    penalty += negative_hits * 2.0

    if title_high_hits or summary_high_hits:
        reasons.append("命中高优先级关键词")
    if title_medium_hits or summary_medium_hits:
        reasons.append("命中中优先级关键词")
    if negative_hits:
        reasons.append("命中负向关键词")

    total_positive_hits = title_high_hits + summary_high_hits + title_medium_hits + summary_medium_hits
    if total_positive_hits == 0:
        penalty += 3.0
        reasons.append("与关注方向弱相关")
    return relevance, penalty, total_positive_hits, reasons


def score_paper(
    paper: dict[str, Any],
    keywords_cfg: dict[str, list[str]],
    authors_cfg: dict[str, list[str]],
    settings: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compute scores and attach ranking metadata."""
    breakdown = ScoreBreakdown()
    reasons: list[str] = []

    breakdown.freshness_score = _freshness_score(paper.get("published_at"), settings["timezone"], now)
    relevance, penalty, positive_hits, relevance_reasons = _relevance_and_penalty(paper, keywords_cfg, settings)
    breakdown.relevance_score = relevance
    breakdown.penalty_score = penalty
    reasons.extend(relevance_reasons)

    author_score, author_reasons = _author_score(paper, authors_cfg)
    breakdown.author_score = author_score
    reasons.extend(author_reasons)

    heat_score, heat_reasons = _heat_score(paper)
    if positive_hits == 0 and author_score == 0:
        heat_score = min(heat_score, 2.0)
        if heat_reasons:
            reasons.append("热度存在，但主题相关性不足")
    breakdown.heat_score = heat_score
    reasons.extend(heat_reasons)

    paper["score"] = round(breakdown.total, 2)
    paper["positive_keyword_hits"] = positive_hits
    paper["is_report_eligible"] = bool(
        positive_hits > 0 or author_score > 0 or not settings.get("require_topic_or_priority_for_report", True)
    )
    paper["score_breakdown"] = {
        "freshness_score": breakdown.freshness_score,
        "relevance_score": breakdown.relevance_score,
        "author_score": breakdown.author_score,
        "heat_score": breakdown.heat_score,
        "penalty_score": breakdown.penalty_score,
    }
    paper["tags"] = infer_tags(paper.get("title", ""), paper.get("summary", ""), keywords_cfg)
    paper["recommendation_reasons"] = list(dict.fromkeys(reasons))
    paper["one_line_summary"] = _build_bilingual_summary(paper)
    return paper


def _split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[.!?])\s+", compact)
    return [part.strip() for part in parts if part.strip()]


def _trim_sentence(text: str, max_length: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    clipped = text[: max_length - 1].rstrip(" ,;:")
    return clipped + "…"


def _classify_contribution(title: str, summary: str) -> tuple[str, str]:
    haystack = f"{title} {summary}".lower()
    patterns = [
        (["we propose", "we present", "introduce", "propose"], ("提出", "proposes")),
        (["we study", "study", "investigate", "analyze", "analysis"], ("分析", "analyzes")),
        (["benchmark", "evaluate", "evaluation", "compare"], ("评估", "evaluates")),
        (["framework", "system", "approach", "method"], ("方法", "presents")),
        (["training", "optimization", "scaling"], ("训练", "studies")),
    ]
    for needles, labels in patterns:
        if any(needle in haystack for needle in needles):
            return labels
    return ("研究", "studies")


def _extract_focus_phrase(title: str, tags: list[str]) -> str:
    if tags:
        return ", ".join(tags[:3])
    normalized = re.sub(r"[:\-].*$", "", title).strip()
    return normalized[:80] if normalized else "该工作"


def _build_zh_summary(title: str, summary: str, tags: list[str]) -> str:
    first_sentence = _split_sentences(summary)[:1]
    action_zh, _action_en = _classify_contribution(title, summary)
    focus = _extract_focus_phrase(title, tags)
    if first_sentence:
        sentence = first_sentence[0]
        sentence = re.sub(
            r"^(This paper|This work|We|In this paper)\s+(propose|present|introduce|study|analyze|investigate)?\s*",
            "",
            sentence,
            flags=re.IGNORECASE,
        )
        sentence = sentence.rstrip(".")
        return _trim_sentence(f"该文{action_zh}{focus}，核心内容是 {sentence}。")
    return _trim_sentence(f"该文{action_zh}{focus}，建议优先查看摘要与方法设定。")


def _build_en_summary(title: str, summary: str, tags: list[str]) -> str:
    first_sentence = _split_sentences(summary)[:1]
    _action_zh, action_en = _classify_contribution(title, summary)
    focus = _extract_focus_phrase(title, tags)
    if first_sentence:
        sentence = first_sentence[0].rstrip(".")
        sentence = re.sub(
            r"^(This paper|This work|We|In this paper)\s+(propose|present|introduce|study|analyze|investigate)?\s*",
            "",
            sentence,
            flags=re.IGNORECASE,
        )
        return _trim_sentence(f"The paper {action_en} {focus} and centers on {sentence}.")
    return _trim_sentence(f"The paper {action_en} {focus}; start with the abstract and method section.")


def _build_bilingual_summary(paper: dict[str, Any]) -> dict[str, str]:
    title = paper.get("title", "")
    summary = paper.get("summary", "")
    tags = paper.get("tags", [])
    if summary:
        return {
            "zh-CN": _build_zh_summary(title, summary, tags),
            "en-US": _build_en_summary(title, summary, tags),
        }
    if tags:
        tag_text = ", ".join(tags[:3])
        return {
            "zh-CN": f"该文围绕 {tag_text} 展开，建议先查看摘要与方法部分。",
            "en-US": f"The paper focuses on {tag_text}; start with the abstract and method section.",
        }
    return {
        "zh-CN": "该文与当前监控方向存在一定相关性，建议先快速扫摘要。",
        "en-US": "The paper shows some overlap with the tracked themes; start with a quick abstract scan.",
    }
