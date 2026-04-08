#!/usr/bin/env python3
"""RSS/Atom feed ingestor with filtering and full-content fetching.

source-config.json schema:
{
  "feeds": [
    {
      "url": "https://medium.com/feed/@CryptoHayes",
      "type": "auto",
      "author_filter": "",
      "title_filter": "",
      "author": "Arthur Hayes",
      "default_tags": ["crypto"]
    }
  ],
  "fetch_full_content": true,
  "fallback_feeds": []
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None


def load_config(path: Path) -> dict:
    """Load source config from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("source-config must be a dict with 'feeds' field")
    if "feeds" not in data:
        raise SystemExit("source-config must have 'feeds' field")
    return data


def parse_date(value: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    if not value:
        return ""

    # Try common formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RSS: Wed, 02 Oct 2024 10:00:00 +0000
        "%a, %d %b %Y %H:%M:%S %Z",  # RSS: Wed, 02 Oct 2024 10:00:00 GMT
        "%Y-%m-%dT%H:%M:%S%z",       # ISO with timezone
        "%Y-%m-%dT%H:%M:%SZ",        # ISO UTC
        "%Y-%m-%dT%H:%M:%S",         # ISO without timezone
        "%Y-%m-%d",                  # Simple date
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except Exception:
            continue

    # Fallback: extract YYYY-MM-DD pattern
    m = re.search(r"(\d{4}-\d{2}-\d{2})", value)
    return m.group(1) if m else ""


def parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS 2.0 feed."""
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"[warn] XML parse failed: {exc}", file=sys.stderr)
        return []

    items = []
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        creator = (item.findtext("dc:creator", default="", namespaces=ns) or "").strip()

        # Try content:encoded first, then description
        content = (item.findtext("content:encoded", default="", namespaces=ns) or "").strip()
        if not content:
            content = (item.findtext("description") or "").strip()

        items.append({
            "title": title,
            "link": link,
            "published": published,
            "creator": creator,
            "content": content,
        })

    return items


def parse_atom(xml_text: str) -> list[dict]:
    """Parse Atom feed."""
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"[warn] XML parse failed: {exc}", file=sys.stderr)
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = []

    for entry in root.findall("atom:entry", ns) + root.findall("entry"):
        title = (
            entry.findtext("atom:title", default="", namespaces=ns)
            or entry.findtext("title")
            or ""
        ).strip()

        # Extract link
        link = ""
        link_el = entry.find("atom:link", ns) or entry.find("link")
        if link_el is not None:
            link = link_el.get("href") or (link_el.text or "")

        # Extract published/updated date
        published = (
            entry.findtext("atom:published", default="", namespaces=ns)
            or entry.findtext("published")
            or ""
        ).strip()
        if not published:
            published = (
                entry.findtext("atom:updated", default="", namespaces=ns)
                or entry.findtext("updated")
                or ""
            ).strip()

        # Extract author
        creator = ""
        author_el = entry.find("atom:author", ns) or entry.find("author")
        if author_el is not None:
            creator = (
                author_el.findtext("atom:name", default="", namespaces=ns)
                or author_el.findtext("name")
                or ""
            ).strip()

        # Extract content
        content = (
            entry.findtext("atom:content", default="", namespaces=ns)
            or entry.findtext("content")
            or ""
        ).strip()
        if not content:
            content = (
                entry.findtext("atom:summary", default="", namespaces=ns)
                or entry.findtext("summary")
                or ""
            ).strip()

        entries.append({
            "title": title,
            "link": link.strip(),
            "published": published,
            "creator": creator,
            "content": content,
        })

    return entries


def detect_feed_type(xml_text: str) -> str:
    """Auto-detect feed type (rss or atom)."""
    if "<rss" in xml_text[:500] or "<channel>" in xml_text[:500]:
        return "rss"
    if "<feed" in xml_text[:500] or 'xmlns="http://www.w3.org/2005/Atom"' in xml_text[:1000]:
        return "atom"
    return "rss"  # default


def fetch_feed(url: str) -> str:
    """Fetch feed XML from URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml, text/xml, application/rss+xml"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def html_to_text(html: str) -> str:
    """Convert HTML to plain text."""
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        text = soup.get_text("\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # fallback: strip tags with regex
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_full_content(url: str) -> str:
    """Fetch full HTML content from URL and convert to text."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        return html_to_text(html)
    except Exception as exc:
        print(f"[warn] Failed to fetch full content from {url}: {exc}", file=sys.stderr)
        return ""


def generate_id(url: str, title: str) -> str:
    """Generate a unique ID from URL or title."""
    # Try to extract meaningful slug from URL
    m = re.search(r"/([a-z0-9-]+)/?$", url)
    if m and len(m.group(1)) > 5:
        return m.group(1)

    # Fallback: sanitize title
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:80].strip("-") or "untitled"


def manifest_line(item: dict, file_name: str) -> str:
    """Generate manifest JSONL entry."""
    obj = {
        "id": item.get("id") or Path(file_name).stem,
        "title": item.get("title") or "",
        "source": item.get("url") or "",
        "author": item.get("author") or "",
        "date": item.get("date") or "",
        "type": "article",
        "reliability": "原文直接引语",
        "tags": item.get("tags") or [],
        "file": file_name,
    }
    return json.dumps(obj, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--full-archive-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-config", required=True)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--since", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.source_config))
    feeds = config.get("feeds", [])
    fetch_full = config.get("fetch_full_content", False)
    fallback_feeds = config.get("fallback_feeds", [])

    plain_dir = Path(args.plain_text_dir)
    full_dir = Path(args.full_archive_dir)
    manifest_path = Path(args.manifest)

    plain_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing IDs for incremental mode
    existing = set()
    if args.incremental and manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(line)
                existing.add(obj.get("id"))
            except Exception:
                continue

    # Process each feed
    all_items = []
    for feed_config in feeds:
        feed_url = feed_config.get("url", "")
        if not feed_url:
            continue

        feed_type = feed_config.get("type", "auto")
        author_filter = feed_config.get("author_filter", "")
        title_filter = feed_config.get("title_filter", "")
        default_author = feed_config.get("author", "")
        default_tags = feed_config.get("default_tags", [])

        print(f"[info] Fetching feed: {feed_url}")

        # Try main feed, then fallbacks
        xml_text = None
        for url in [feed_url] + fallback_feeds:
            try:
                xml_text = fetch_feed(url)
                if xml_text:
                    print(f"[info] Successfully fetched from {url}")
                    break
            except Exception as exc:
                print(f"[warn] Failed to fetch {url}: {exc}", file=sys.stderr)
                continue

        if not xml_text:
            print(f"[warn] All feed URLs failed for {feed_url}", file=sys.stderr)
            continue

        # Auto-detect feed type
        if feed_type == "auto":
            feed_type = detect_feed_type(xml_text)

        # Parse feed
        if feed_type == "atom":
            items = parse_atom(xml_text)
        else:
            items = parse_rss(xml_text)

        print(f"[info] Parsed {len(items)} items from feed")

        # Filter items
        for item in items:
            # Author filter
            if author_filter and author_filter.lower() not in item.get("creator", "").lower():
                continue

            # Title filter
            if title_filter and title_filter.lower() not in item.get("title", "").lower():
                continue

            # Add metadata
            item["feed_url"] = feed_url
            item["default_author"] = default_author
            item["default_tags"] = default_tags
            all_items.append(item)

    print(f"[info] Total items after filtering: {len(all_items)}")

    # Process items
    new_lines = []
    errors = []

    for item in all_items:
        url = item.get("link", "")
        if not url:
            continue

        title = item.get("title", "")
        published = item.get("published", "")
        date = parse_date(published)

        # Filter by --since
        if args.since and date and date < args.since:
            continue

        # Generate ID
        item_id = generate_id(url, title)

        # Skip if already ingested
        if args.incremental and item_id in existing:
            continue

        if args.dry_run:
            print(f"[dry-run] {url} -> {item_id}")
            continue

        try:
            # Get content
            if fetch_full:
                # Fetch full content from URL
                body_text = fetch_full_content(url)
                if not body_text:
                    # Fallback to feed content
                    body_text = html_to_text(item.get("content", ""))
            else:
                # Use inline feed content
                body_text = html_to_text(item.get("content", ""))

            if not body_text:
                print(f"[warn] No content for {url}", file=sys.stderr)
                errors.append(item_id)
                continue

            # Save raw HTML/content
            raw_path = full_dir / f"{item_id}.html"
            raw_path.write_text(item.get("content", ""), encoding="utf-8")

            # Save plain text
            fname = f"{date}__{item_id}.md" if date else f"{item_id}.md"
            plain_path = plain_dir / fname

            content_lines = []
            if title:
                content_lines.append(title)
                content_lines.append("")
            content_lines.append(body_text)

            plain_path.write_text("\n".join(content_lines).strip() + "\n", encoding="utf-8")

            # Add to manifest
            author = item.get("creator") or item.get("default_author", "")
            item_data = {
                "id": item_id,
                "title": title,
                "url": url,
                "author": author,
                "date": date,
                "tags": item.get("default_tags", []),
            }
            new_lines.append(manifest_line(item_data, plain_path.name))

        except Exception as exc:
            print(f"[warn] Failed to process {url}: {exc}", file=sys.stderr)
            errors.append(item_id)
            continue

    # Write manifest
    if new_lines:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    if errors:
        print(f"[warn] {len(errors)} item(s) failed: {errors[:10]}")
    print(f"[done] ingested={len(new_lines)} failed={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
