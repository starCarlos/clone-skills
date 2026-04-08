#!/usr/bin/env python3
"""Substack blog ingestor with automatic pagination.

source-config.json schema:
{
  "blog": "cryptohayes",
  "author": "Arthur Hayes",
  "limit": 50
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
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
        raise SystemExit("source-config must be a dict with 'blog' field")
    if "blog" not in data:
        raise SystemExit("source-config must have 'blog' field")
    return data


def parse_date(value: str) -> str:
    """Parse ISO date string to YYYY-MM-DD."""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        # fallback: extract YYYY-MM-DD pattern
        m = re.search(r"(\d{4}-\d{2}-\d{2})", value)
        return m.group(1) if m else value[:10]


def fetch_substack_posts(blog: str, limit: int = 50) -> list[dict]:
    """Fetch all posts from Substack blog via API pagination."""
    posts = []
    offset = 0

    while True:
        api_url = f"https://{blog}.substack.com/api/v1/posts?limit={limit}&offset={offset}"
        try:
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"[warn] API request failed at offset={offset}: {exc}", file=sys.stderr)
            break

        if not data or not isinstance(data, list):
            break

        posts.extend(data)
        offset += limit

        if len(data) < limit:
            break

    return posts


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


def generate_id(url: str, title: str) -> str:
    """Generate a unique ID from URL or title."""
    # Try to extract slug from URL
    m = re.search(r"/p/([a-z0-9-]+)", url)
    if m:
        return m.group(1)

    # Fallback: sanitize title
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:80].strip("-")


def manifest_line(post: dict, file_name: str, author: str) -> str:
    """Generate manifest JSONL entry."""
    obj = {
        "id": post.get("id") or Path(file_name).stem,
        "title": post.get("title") or "",
        "source": post.get("url") or "",
        "author": author,
        "date": post.get("date") or "",
        "type": "article",
        "reliability": "原文直接引语",
        "tags": post.get("tags") or [],
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
    blog = config["blog"]
    author = config.get("author", "")
    limit = config.get("limit", 50)

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

    # Fetch all posts
    print(f"[info] Fetching posts from {blog}.substack.com...")
    raw_posts = fetch_substack_posts(blog, limit)
    print(f"[info] Found {len(raw_posts)} posts")

    # Process posts
    new_lines = []
    errors = []

    for post in raw_posts:
        url = post.get("canonical_url") or post.get("url") or ""
        if not url:
            continue

        title = post.get("title") or ""
        published = post.get("post_date") or post.get("updated_at") or ""
        date = parse_date(published)

        # Filter by --since
        if args.since and date and date < args.since:
            continue

        # Generate ID
        post_id = generate_id(url, title)

        # Skip if already ingested
        if args.incremental and post_id in existing:
            continue

        if args.dry_run:
            print(f"[dry-run] {url} -> {post_id}")
            continue

        # Extract content from body_html (Substack API provides full HTML)
        body_html = post.get("body_html") or ""
        if not body_html:
            print(f"[warn] No body_html for {url}", file=sys.stderr)
            errors.append(post_id)
            continue

        try:
            # Save raw HTML
            raw_path = full_dir / f"{post_id}.html"
            raw_path.write_text(body_html, encoding="utf-8")

            # Convert to plain text
            body_text = html_to_text(body_html)

            # Save plain text
            fname = f"{date}__{post_id}.md" if date else f"{post_id}.md"
            plain_path = plain_dir / fname

            content_lines = []
            if title:
                content_lines.append(title)
                content_lines.append("")
            content_lines.append(body_text)

            plain_path.write_text("\n".join(content_lines).strip() + "\n", encoding="utf-8")

            # Add to manifest
            post_data = {
                "id": post_id,
                "title": title,
                "url": url,
                "date": date,
                "tags": config.get("default_tags", []),
            }
            new_lines.append(manifest_line(post_data, plain_path.name, author))

        except Exception as exc:
            print(f"[warn] Failed to process {url}: {exc}", file=sys.stderr)
            errors.append(post_id)
            continue

    # Write manifest
    if new_lines:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    if errors:
        print(f"[warn] {len(errors)} post(s) failed: {errors[:10]}")
    print(f"[done] ingested={len(new_lines)} failed={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
