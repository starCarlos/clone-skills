#!/usr/bin/env python3
"""Generic URL list ingestor.

source-config.json schema (list or {"sources": [...]}):
{
  "sources": [
    {
      "id": "unique_id",
      "title": "Title",
      "url": "https://...",
      "date": "YYYY" | "YYYY-MM" | "YYYY-MM-DD",
      "type": "article|report|letter|transcript",
      "reliability": "原文直接引语|后人转述",
      "format": "html|pdf|md|text|wp_json|sina",
      "tags": ["tag1", "tag2"]
    }
  ]
}
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None


def load_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "sources" in data:
        return data["sources"]
    raise SystemExit("source-config must be a list or dict with 'sources'")


AGENT_ACCEPT = "text/markdown, text/html"


def fetch_url(url: str, timeout: int = 30) -> tuple[bytes, str]:
    """Fetch a URL and return (data, content_type)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            # Cloudflare Markdown for Agents (if enabled) will return Markdown here.
            "Accept": AGENT_ACCEPT,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ct = resp.headers.get("Content-Type", "")
        # Optional token budgeting hint for Markdown for Agents
        tok = resp.headers.get("x-markdown-tokens")
        if tok and "text/markdown" in (ct or "").lower():
            print(f"[markdown] x-markdown-tokens={tok} url={url}")
        return resp.read(), ct


def detect_format(data: bytes, content_type: str, declared: str) -> str:
    """Auto-detect format from response data, overriding declared format if needed."""
    ct = (content_type or "").lower()
    if data[:5] == b"%PDF-":
        return "pdf"
    if "application/pdf" in ct:
        return "pdf"
    if "application/json" in ct:
        return "wp_json"
    if "text/markdown" in ct:
        return "md"
    return declared


def decode_html(data: bytes) -> str:
    for enc in ("utf-8", "gb18030", "gbk", "big5", "latin-1"):
        try:
            return data.decode(enc, errors="ignore")
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


class _BodyText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._chunks)


def html_to_text(html: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        body = soup.body or soup
        text = body.get_text("\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    parser = _BodyText()
    parser.feed(html)
    return parser.text()


def wp_json_to_text(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8", errors="ignore"))
    content = data.get("content", {}).get("rendered", "")
    if not content and isinstance(data, dict) and "content" in data:
        content = data["content"]
    return html_to_text(content)


def sina_to_text(html: str) -> str:
    # Sina finance articles often use <div id="artibody"> or class "article"
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        body = soup.find(id="artibody") or soup.find("div", class_="article") or soup.body
        text = body.get_text("\n") if body else soup.get_text("\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    return html_to_text(html)


def pdf_to_text(data: bytes) -> str:
    if not PdfReader:
        raise RuntimeError("pypdf not installed")
    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()


def write_plain(path: Path, title: str, body: str) -> None:
    lines = []
    if title:
        lines.append(title)
        lines.append("")
    lines.append(body.strip())
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def manifest_line(src: dict, file_name: str) -> str:
    obj = {
        "id": src.get("id") or Path(file_name).stem,
        "title": src.get("title") or "",
        "source": src.get("url") or "",
        "author": src.get("author") or "",
        "date": src.get("date") or "",
        "type": src.get("type") or "",
        "reliability": src.get("reliability") or "",
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
    errors = []
    for src in sources:
        if args.since and src.get("date") and src["date"] < args.since:
            continue
        src_id = src.get("id")
        if args.incremental and src_id in existing:
            continue
        url = src.get("url")
        if not url:
            continue
        fmt = (src.get("format") or "html").lower()
        title = src.get("title") or ""
        date = src.get("date") or ""
        fname = f"{date}__{src_id}.md" if date and src_id else f"{src_id}.md"

        if args.dry_run:
            print(f"[dry-run] {url} -> {fname}")
            continue

        try:
            data, content_type = fetch_url(url)
        except Exception as exc:
            print(f"[warn] fetch failed: {url} -> {exc}")
            errors.append(src_id or url)
            continue

        try:
            fmt = detect_format(data, content_type, fmt)
            if fmt == "pdf":
                raw_path = full_dir / f"{src_id or Path(url).stem}.pdf"
                raw_path.write_bytes(data)
                body = pdf_to_text(data)
            elif fmt == "wp_json":
                raw_path = full_dir / f"{src_id or Path(url).stem}.json"
                raw_path.write_bytes(data)
                body = wp_json_to_text(data)
            elif fmt == "md":
                md = data.decode("utf-8", errors="ignore")
                raw_path = full_dir / f"{src_id or Path(url).stem}.md"
                raw_path.write_text(md, encoding="utf-8")
                body = md
            else:
                html = decode_html(data)
                raw_path = full_dir / f"{src_id or Path(url).stem}.html"
                raw_path.write_text(html, encoding="utf-8")
                if fmt == "sina":
                    body = sina_to_text(html)
                else:
                    body = html_to_text(html)
        except Exception as exc:
            print(f"[warn] parse failed: {url} -> {exc}")
            errors.append(src_id or url)
            continue

        plain_path = plain_dir / fname
        write_plain(plain_path, title, body)
        new_lines.append(manifest_line(src, plain_path.name))

    if new_lines:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    if errors:
        print(f"[warn] {len(errors)} source(s) failed: {errors[:10]}")
    print(f"[done] ingested={len(new_lines)} failed={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
