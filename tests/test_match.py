from scripts.match_sources import match_papers


def test_match_papers_by_normalized_title():
    arxiv = [
        {
            "arxiv_id": "2603.12345",
            "title": "Attention Residuals: A Transformer Study",
            "summary": "",
        }
    ]
    hf = [
        {
            "title": "Attention Residuals A Transformer Study",
            "hf_url": "https://huggingface.co/papers/2603.12345",
            "paper_url": "",
            "section": "trending",
        }
    ]

    result = match_papers(arxiv, hf, fuzzy_threshold=0.9)

    assert result[0]["in_hf_trending"] is True
    assert result[0]["hf_match_confidence"] == 1.0
