"""Match arXiv papers with Hugging Face paper hints."""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

try:
    from .utils import extract_arxiv_id, normalize_title
except ImportError:
    from utils import extract_arxiv_id, normalize_title


def match_papers(
    arxiv_papers: list[dict[str, Any]],
    hf_papers: list[dict[str, Any]],
    fuzzy_threshold: float = 0.9,
) -> list[dict[str, Any]]:
    """Attach HF daily/trending flags to arXiv papers."""
    hf_by_arxiv_id: dict[str, list[dict[str, Any]]] = {}
    hf_by_title: dict[str, list[dict[str, Any]]] = {}
    normalized_hf: list[tuple[str, dict[str, Any]]] = []

    for item in hf_papers:
        paper_url = item.get("paper_url") or item.get("hf_url", "")
        arxiv_id = extract_arxiv_id(paper_url)
        if arxiv_id:
            hf_by_arxiv_id.setdefault(arxiv_id, []).append(item)
        normalized = normalize_title(item.get("title", ""))
        if normalized:
            hf_by_title.setdefault(normalized, []).append(item)
            normalized_hf.append((normalized, item))

    for paper in arxiv_papers:
        paper["in_hf_daily"] = False
        paper["in_hf_trending"] = False
        paper["hf_match_confidence"] = 0.0
        paper["hf_score_hint"] = None
        matches: list[tuple[dict[str, Any], float]] = []

        arxiv_id = paper.get("arxiv_id", "")
        if arxiv_id and arxiv_id in hf_by_arxiv_id:
            matches.extend((item, 1.0) for item in hf_by_arxiv_id[arxiv_id])

        normalized_title = normalize_title(paper.get("title", ""))
        for item in hf_by_title.get(normalized_title, []):
            matches.append((item, 1.0))

        if not matches and normalized_title:
            for hf_title, item in normalized_hf:
                similarity = fuzz.ratio(normalized_title, hf_title) / 100
                if similarity >= fuzzy_threshold:
                    matches.append((item, similarity))

        if not matches:
            continue

        best_confidence = max(confidence for _, confidence in matches)
        paper["hf_match_confidence"] = round(best_confidence, 3)
        numeric_hints = [item.get("score_hint") for item, _ in matches if isinstance(item.get("score_hint"), (int, float))]
        if numeric_hints:
            paper["hf_score_hint"] = max(numeric_hints)
        for item, _confidence in matches:
            section = item.get("section")
            if section == "daily":
                paper["in_hf_daily"] = True
            elif section == "trending":
                paper["in_hf_trending"] = True
    return arxiv_papers
