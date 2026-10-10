"""Fetch and parse the Google News RSS feed (task H2). Standard library only.

The network call lives behind an injectable `opener` so tests pass a saved RSS file and never touch the network.
Each item in a Google News feed has a title in the form "Headline - Source", a link (a Google redirect to the real
article), a pubDate (RFC 822) and a <source> element with the publisher name.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from email.utils import parsedate_to_datetime

from backend.app.news import config


def _default_opener(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=config.FETCH_TIMEOUT_S) as resp:  # noqa: S310 (fixed https host)
        return resp.read()


def _clean_title(raw: str, source: str | None) -> str:
    """Google News appends " - Source" to the title; drop it when it matches the <source> element."""
    title = (raw or "").strip()
    if source and title.endswith(f" - {source}"):
        return title[: -(len(source) + 3)].strip()
    return title


def _published(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        return None


def fetch_rss(query: str, opener: Callable[[str], bytes] | None = None) -> list[dict]:
    """Raw items for one query: [{title, url, source, published}], newest first. Never returns filler fields.

    `opener` is resolved at call time (not bound as a default), so monkeypatching `_default_opener` works in tests.
    """
    raw = (opener or _default_opener)(config.RSS_URL.format(query=urllib.request.quote(query)))
    root = ET.fromstring(raw)  # noqa: S314 (Google News feed, not user-supplied XML)
    items = []
    for item in root.findall(".//item"):
        src_el = item.find("source")
        source = src_el.text.strip() if src_el is not None and src_el.text else None
        title = _clean_title(item.findtext("title") or "", source)
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append({"title": title, "url": link, "source": source, "published": _published(item.findtext("pubDate"))})
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    return items
