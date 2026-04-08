#!/usr/bin/env python3
"""WeChat MP ingestor (URL list).

source-config.json schema:
[
  {"id": "...", "url": "https://mp.weixin.qq.com/...", "date": "YYYY-MM-DD", "title": "...", "tags": []}
]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import requests  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"[error] missing deps: {exc}", file=sys.stderr)
    sys.exit(1)


def load_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "sources" in data:
        return data["sources"]
    raise SystemExit("source-config must be a list or dict with 'sources'")


def fetch_html(url: str, timeout: int = 20) -> tuple[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/markdown, text/html",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    ctype = (resp.headers.get("content-type") or "").lower()
    if "text/markdown" in ctype and resp.headers.get("x-markdown-tokens"):
        print(f"[markdown] x-markdown-tokens={resp.headers.get('x-markdown-tokens')} url={url}")
    content = resp.content
    encoding = resp.encoding
    if not encoding or encoding.lower() == "iso-8859-1":
        m = re.search(br"charset=([a-zA-Z0-9_-]+)", content[:10000], re.IGNORECASE)
        encoding = m.group(1).decode("ascii", errors="ignore") if m else "utf-8"
    try:
        html = content.decode(encoding, errors="replace")
    except LookupError:
        html = content.decode("utf-8", errors="replace")
    return html, resp.url


def html_to_md(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    title_tag = soup.find(id="activity-name")
    if title_tag:
        title = title_tag.get_text(strip=True)
    content = soup.find(id="js_content")
    if not content:
        return title, soup.get_text("\n")
    # remove scripts/styles
    for tag in content(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    text = content.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text.strip()


def manifest_line(src: dict, file_name: str) -> str:
    obj = {
        "id": src.get("id") or Path(file_name).stem,
        "title": src.get("title") or "",
        "source": src.get("url") or "",
        "author": src.get("author") or "",
        "date": src.get("date") or "",
        "type": src.get("type") or "公众号",
        "reliability": src.get("reliability") or "原文直接引语",
        "tags": src.get("tags") or [],
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

    plain_dir = Path(args.plain_text_dir)
    full_dir = Path(args.full_archive_dir)
    manifest_path = Path(args.manifest)
    sources = load_sources(Path(args.source_config))

    plain_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if args.incremental and manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(line)
                existing.add(obj.get("id"))
            except Exception:
                continue

    new_lines = []
    for src in sources:
        if args.since and src.get("date") and src["date"] < args.since:
            continue
        src_id = src.get("id")
        if args.incremental and src_id in existing:
            continue
        url = src.get("url")
        if not url:
            continue
        if args.dry_run:
            print(f"[dry-run] {url}")
            continue

        html, final_url = fetch_html(url)
        raw_path = full_dir / f"{src_id or Path(final_url).stem}.html"
        raw_path.write_text(html, encoding="utf-8")

        title, body = html_to_md(html)
        title = src.get("title") or title
        date = src.get("date") or ""
        fname = f"{date}__{src_id}.md" if date and src_id else f"{src_id}.md"
        plain_path = plain_dir / fname
        plain_path.write_text(f"{title}\n\n{body}\n", encoding="utf-8")

        new_lines.append(manifest_line(src, plain_path.name))

    if new_lines:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    print(f"[done] ingested={len(new_lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
