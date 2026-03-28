from unittest.mock import patch

from scripts.fetch_arxiv import fetch_arxiv


class DummyResponse:
    def __init__(self, content: bytes):
        self.content = content


def test_fetch_arxiv_falls_back_to_api_when_rss_is_empty():
    rss_xml = b"""<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel><title>empty</title></channel></rss>"""
    api_xml = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry>
    <id>http://arxiv.org/abs/2603.12345v1</id>
    <updated>2026-03-27T12:00:00Z</updated>
    <published>2026-03-27T12:00:00Z</published>
    <title>Residual Connections for Deep Transformers</title>
    <summary>We propose a revised residual design.</summary>
    <author><name>Jane Doe</name></author>
    <link href='http://arxiv.org/abs/2603.12345v1' rel='alternate' type='text/html'/>
    <link title='pdf' href='http://arxiv.org/pdf/2603.12345v1' rel='related' type='application/pdf'/>
    <category term='cs.LG'/>
  </entry>
</feed>
"""
    responses = [DummyResponse(rss_xml), DummyResponse(api_xml)]

    with patch("scripts.fetch_arxiv.request_with_retry", side_effect=responses):
        papers = fetch_arxiv(
            ["https://rss.arxiv.org/rss/cs.LG"],
            lookback_days=7,
            timezone="UTC",
            api_max_results=5,
        )

    assert len(papers) == 1
    assert papers[0]["source_method"] == "api"
    assert papers[0]["arxiv_id"] == "2603.12345v1"
