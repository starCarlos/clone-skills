#!/usr/bin/env python3
"""Berkshire Hathaway letters + owner manual ingestor.

This mirrors Buffett skill's update_corpus style but conforms to the pluggable
ingestor contract.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None

BASE_URL = "https://www.berkshirehathaway.com/letters/"
OWNER_MANUAL_URL = "https://www.berkshirehathaway.com/ownman.pdf"


class _BodyText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return "\n".join(self._chunks)


def fetch_url(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def decode_html(data: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc, errors="ignore")
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def html_to_text(html: str) -> str:
    parser = _BodyText()
    parser.feed(html)
    text = parser.text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
    lines = [title, "", body.strip()]
    path.write_text("\n".join([l for l in lines if l is not None]).strip() + "\n", encoding="utf-8")


def manifest_line(obj: dict, file_name: str) -> str:
    entry = {
        "id": obj.get("id") or Path(file_name).stem,
        "title": obj.get("title") or "",
        "source": obj.get("url") or "",
        "author": "Warren Buffett",
        "date": obj.get("date") or "",
        "type": obj.get("type") or "股东信",
        "reliability": obj.get("reliability") or "原文直接引语",
        "tags": obj.get("tags") or ["投资", "价值投资"],
        "file": file_name,
    }
    return json.dumps(entry, ensure_ascii=False)


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise SystemExit("source-config for berkshire_letters must be a dict")


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

    cfg = load_config(Path(args.source_config))
    start_year = int(cfg.get("start_year", 1977))
    end_year = int(cfg.get("end_year", 2024))
    use_pdf = bool(cfg.get("pdf_years", []))
    include_owner_manual = cfg.get("include_owner_manual", True)

    plain_dir = Path(args.plain_text_dir)
    full_dir = Path(args.full_archive_dir)
    manifest_path = Path(args.manifest)
    plain_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if args.incremental and manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                existing.add(json.loads(line).get("id"))
            except Exception:
                continue

    new_lines = []
    for year in range(start_year, end_year + 1):
        if args.since and str(year) < args.since:
            continue
        doc_id = f"{year}_shareholder_letter"
        if args.incremental and doc_id in existing:
            continue
        url_html = f"{BASE_URL}{year}.html"
        url_pdf = f"{BASE_URL}{year}ltr.pdf"
        url = url_pdf if (use_pdf and year in set(cfg.get("pdf_years", []))) else url_html
        if args.dry_run:
            print(f"[dry-run] {url}")
            continue

        data = fetch_url(url)
        if url.endswith(".pdf"):
            raw_path = full_dir / f"{year}ltr.pdf"
            raw_path.write_bytes(data)
            body = pdf_to_text(data)
        else:
            raw_path = full_dir / f"{year}.html"
            raw_path.write_text(decode_html(data), encoding="utf-8")
            body = html_to_text(decode_html(data))

        title = f"Berkshire Hathaway Shareholder Letter {year}"
        fname = f"{year}__shareholder_letter.md"
        write_plain(plain_dir / fname, title, body)
        new_lines.append(
            manifest_line({"id": doc_id, "title": title, "url": url, "date": str(year)}, fname)
        )

    if include_owner_manual:
        doc_id = "owners_manual"
        if not (args.incremental and doc_id in existing):
            if not args.dry_run:
                data = fetch_url(OWNER_MANUAL_URL)
                raw_path = full_dir / "owners_manual.pdf"
                raw_path.write_bytes(data)
                body = pdf_to_text(data) if PdfReader else ""
                title = "Berkshire Hathaway Owner's Manual"
                fname = "1996__owners_manual.md"
                write_plain(plain_dir / fname, title, body)
                new_lines.append(
                    manifest_line(
                        {
                            "id": doc_id,
                            "title": title,
                            "url": OWNER_MANUAL_URL,
                            "date": "1996",
                            "type": "手册",
                        },
                        fname,
                    )
                )

    if new_lines:
        with manifest_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    print(f"[done] ingested={len(new_lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
