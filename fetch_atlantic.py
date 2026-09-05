#!/usr/bin/env python3
"""Collect public The Atlantic RSS metadata for a personal learning library."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

FEEDS = {
    "全部": "https://www.theatlantic.com/feed/all/",
    "精选": "https://www.theatlantic.com/feed/best-of/",
    "商业": "https://www.theatlantic.com/feed/channel/business/",
    "科技": "https://www.theatlantic.com/feed/channel/technology/",
    "教育": "https://www.theatlantic.com/feed/channel/education/",
    "国际": "https://www.theatlantic.com/feed/channel/international/",
}
OUTPUT = Path("docs/data/articles.json")
LIMIT = 250
USER_AGENT = "AtlanticLearning/1.0 (+https://github.com/rayraywong6-dev/Atlantic-learning)"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str | None) -> str:
    parser = TextExtractor()
    parser.feed(unescape(value or ""))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names and child.text:
            return child.text.strip()
    return ""


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return value


def fetch_feed(category: str, url: str) -> list[dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"})
    with urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    entries: list[dict[str, str]] = []
    nodes = root.findall(".//item")
    if not nodes:
        nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "entry"]

    for item in nodes:
        link = child_text(item, ("link",))
        if not link:
            for child in item:
                if child.tag.rsplit("}", 1)[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        link = canonical_url(link)
        title = plain_text(child_text(item, ("title",)))
        if not title or not link:
            continue
        author = plain_text(child_text(item, ("creator", "author", "name")))
        summary = plain_text(child_text(item, ("description", "summary", "content", "encoded")))
        published = iso_date(child_text(item, ("pubdate", "published", "updated", "date")))
        entries.append(
            {
                "title": title,
                "link": link,
                "author": author,
                "published": published,
                "category": category,
                "summary": summary,
            }
        )
    return entries


def load_existing() -> list[dict[str, str]]:
    try:
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
        return data.get("articles", [])
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


def main() -> int:
    fetched: list[dict[str, str]] = []
    errors: list[str] = []
    for category, url in FEEDS.items():
        try:
            items = fetch_feed(category, url)
            fetched.extend(items)
            print(f"{category}: {len(items)}")
        except Exception as exc:
            errors.append(f"{category}: {exc}")
            print(f"warning: {category}: {exc}", file=sys.stderr)

    if not fetched:
        print("No feeds could be fetched; keeping the existing library.", file=sys.stderr)
        return 1

    # Prefer the more specific category when the same article appears in several feeds.
    combined = load_existing() + fetched
    by_url: dict[str, dict[str, str]] = {}
    for article in combined:
        key = canonical_url(article.get("link", ""))
        if key:
            by_url[key] = {**article, "link": key}

    articles = sorted(
        by_url.values(),
        key=lambda item: item.get("published", ""),
        reverse=True,
    )[:LIMIT]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "feeds": FEEDS,
        "errors": errors,
        "articles": articles,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(articles)} articles to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
