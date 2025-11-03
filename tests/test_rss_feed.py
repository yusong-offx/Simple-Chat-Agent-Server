from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from ai.news.tools.rss_feed import RssFeedCollector, FeedSource, _strip_ns, _parse_dt  # noqa: F401


def test_strip_ns():
    assert _strip_ns("{ns}tag") == "tag"
    assert _strip_ns("tag") == "tag"
    assert _strip_ns("") == ""


def test_parse_dt_rfc_and_iso():
    # RFC-822
    rfc = "Wed, 02 Oct 2002 08:00:00 EST"
    dt = _parse_dt(rfc)
    assert isinstance(dt, datetime)
    # ISO-8601
    iso = "2024-10-31T12:34:56Z"
    dt2 = _parse_dt(iso)
    assert isinstance(dt2, datetime)
    assert dt2.tzinfo is not None
    assert dt2.tzinfo.utcoffset(dt2) == timezone.utc.utcoffset(dt2)


def test_parse_minimal_rss():
    rss_xml = """
    <rss version="2.0">
      <channel>
        <title>Feed</title>
        <item>
          <title>Item 1</title>
          <link>https://example.com/1</link>
          <description>Desc1</description>
          <pubDate>Wed, 02 Oct 2002 08:00:00 GMT</pubDate>
          <guid>id-1</guid>
        </item>
      </channel>
    </rss>
    """
    root = ET.fromstring(rss_xml)
    collector = RssFeedCollector([FeedSource(url="https://example.com/feed.xml", name="ex")])
    # Accessing internal parser for unit test is acceptable here
    items = collector._parse_rss(  # noqa: SLF001
        root, FeedSource(url="https://example.com/feed.xml", name="ex")
    )
    assert len(items) == 1
    it = items[0]
    assert it.id == "id-1"
    assert it.title == "Item 1"
    assert it.link == "https://example.com/1"
    assert it.summary == "Desc1"
