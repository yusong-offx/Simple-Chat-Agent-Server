from __future__ import annotations

import asyncio
import email.utils
import html
import logging
import httpx
import xml.etree.ElementTree as ET

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Iterable, Optional, Sequence


# Public types
@dataclass(slots=True)
class FeedSource:
    url: str
    name: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class NewsItem:
    id: str
    title: str
    link: str
    summary: Optional[str]
    published_at: Optional[datetime]
    source_url: str
    source_name: Optional[str]
    authors: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)


class RssFeedCollector:
    """Simple RSS/Atom news collector.

    - Fetches multiple feeds concurrently using httpx.AsyncClient
    - Parses both RSS 2.0 and Atom 1.0 into a normalized NewsItem
    - De-duplicates across polling runs using an in-memory id/link set
    - Provides `fetch_all()` for one-shot and `poll()` for continuous collection
    """

    def __init__(
        self,
        feeds: Sequence[str | FeedSource],
        *,
        timeout: float = 10.0,
        concurrency: int = 8,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._sources: list[FeedSource] = [
            f if isinstance(f, FeedSource) else FeedSource(url=f) for f in feeds
        ]
        self._timeout = timeout
        self._sem = asyncio.Semaphore(max(1, int(concurrency)))
        self._seen: set[str] = set()
        self._log = logger or logging.getLogger(__name__)

    async def fetch_all(
        self, client: Optional[httpx.AsyncClient] = None
    ) -> list[NewsItem]:
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=True)
            close_client = True
        try:
            tasks = [self._fetch_one(client, src) for src in self._sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            items: list[NewsItem] = []
            for res in results:
                if isinstance(res, Exception):
                    self._log.warning("feed fetch failed: %s", res)
                    continue
                items.extend(res)
            return items
        finally:
            if close_client:
                await client.aclose()

    async def poll(
        self,
        *,
        interval: float = 300.0,
        on_items: Optional[Callable[[list[NewsItem]], Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> AsyncIterator[list[NewsItem]]:
        """Continuously fetch feeds and yield only new items.

        - interval: seconds between polls
        - on_items: optional callback invoked with each non-empty batch
        """
        while True:
            all_items = await self.fetch_all(client=client)
            new_items = self._dedupe(all_items)
            if new_items:
                if on_items:
                    try:
                        on_items(new_items)
                    except Exception as e:
                        self._log.warning("on_items callback error: %s", e)
                yield new_items
            await asyncio.sleep(max(1.0, float(interval)))

    # -------------- Internal --------------
    async def _fetch_one(
        self, client: httpx.AsyncClient, source: FeedSource
    ) -> list[NewsItem]:
        async with self._sem:
            resp = await client.get(source.url, headers={"User-Agent": _UA})
        resp.raise_for_status()
        text = resp.text

        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            self._log.warning("XML parse error for %s: %s", source.url, e)
            return []

        tag = _strip_ns(root.tag)
        if tag == "rss" or tag == "rdf":
            return self._parse_rss(root, source)
        if tag == "feed":
            return self._parse_atom(root, source)

        # Fallback: try detecting by presence
        if root.find("channel") is not None:
            return self._parse_rss(root, source)
        return self._parse_atom(root, source)

    def _parse_rss(self, root: ET.Element, source: FeedSource) -> list[NewsItem]:
        # RSS 2.0: <rss><channel><item>...</item></channel></rss>
        channel = root.find("channel") if _strip_ns(root.tag) == "rss" else root
        items_el = channel.findall("item") if channel is not None else []

        ns_content = "{http://purl.org/rss/1.0/modules/content/}encoded"
        out: list[NewsItem] = []
        for it in items_el:
            title = _text(it.find("title"))
            link = _text(it.find("link"))
            guid = _text(it.find("guid")) or link or title
            desc = _text(it.find("description")) or _text(it.find(ns_content))
            pub = _text(it.find("pubDate"))

            published = _parse_dt(pub)
            authors = tuple(filter(None, [_text(it.find("author"))]))
            tags = tuple(t.text.strip() for t in it.findall("category") if t.text)

            out.append(
                NewsItem(
                    id=guid or link or title,
                    title=html.unescape(title or ""),
                    link=link or "",
                    summary=html.unescape(desc or None) if desc else None,
                    published_at=published,
                    source_url=source.url,
                    source_name=source.name,
                    authors=authors,
                    tags=source.tags + tags,
                )
            )
        return out

    def _parse_atom(self, root: ET.Element, source: FeedSource) -> list[NewsItem]:
        # Atom 1.0: <feed><entry>...</entry></feed>
        out: list[NewsItem] = []
        for e in root.findall(_with_ns("entry", root)):
            title = _text(e.find(_with_ns("title", root)))
            link = _first_link(e, root)
            id_ = _text(e.find(_with_ns("id", root))) or link or title
            summary = _text(e.find(_with_ns("summary", root))) or _text(
                e.find(_with_ns("content", root))
            )
            published = _text(e.find(_with_ns("published", root))) or _text(
                e.find(_with_ns("updated", root))
            )

            authors = tuple(
                filter(
                    None,
                    [
                        _text(a.find(_with_ns("name", root)))
                        for a in e.findall(_with_ns("author", root))
                    ],
                )
            )
            tags = tuple(
                t.attrib.get("term") or _text(t.find(_with_ns("term", root))) or ""
                for t in e.findall(_with_ns("category", root))
            )

            out.append(
                NewsItem(
                    id=id_,
                    title=html.unescape(title or ""),
                    link=link or "",
                    summary=html.unescape(summary or None) if summary else None,
                    published_at=_parse_dt(published),
                    source_url=source.url,
                    source_name=source.name,
                    authors=authors,
                    tags=source.tags + tags,
                )
            )
        return out

    def _dedupe(self, items: Iterable[NewsItem]) -> list[NewsItem]:
        new_items: list[NewsItem] = []
        for it in items:
            key = it.id or it.link
            if not key:
                continue
            if key in self._seen:
                continue
            self._seen.add(key)
            new_items.append(it)
        return new_items

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _strip_ns(tag: str) -> str:
    if not tag:
        return tag
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _with_ns(tag: str, root: ET.Element) -> str:
    # Support both namespaced and non-namespaced atom elements
    # Try default namespace of root first
    if root.tag.startswith("{"):
        ns = root.tag.split("}", 1)[0][1:]
        return f"{{{ns}}}{tag}"
    return tag


def _text(el: Optional[ET.Element]) -> str:
    if el is None:
        return ""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    if el.tail:
        parts.append(el.tail)
    return "".join(parts).strip()


def _first_link(entry: ET.Element, root: ET.Element) -> Optional[str]:
    # Prefer rel=alternate HTML link
    links = entry.findall(_with_ns("link", root))
    href: Optional[str] = None
    for l in links:
        rel = l.attrib.get("rel", "alternate")
        type_ = l.attrib.get("type", "text/html")
        if rel == "alternate" and ("html" in type_ or type_ == "text/html"):
            href = l.attrib.get("href")
            if href:
                return href
    # Fallback to first link@href or text content
    if links:
        return links[0].attrib.get("href") or _text(links[0]) or None
    return None


def _parse_dt(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    v = value.strip()
    # RFC-822 / 1123 (typical RSS pubDate)
    try:
        dt = email.utils.parsedate_to_datetime(v)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception:
        pass
    # ISO-8601 (Atom published/updated)
    try:
        v2 = v.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None
