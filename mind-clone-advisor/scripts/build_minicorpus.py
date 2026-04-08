#!/usr/bin/env python3
"""build_minicorpus.py

Create a small local corpus (plain_text) from a few public URLs by extracting
paragraphs and splitting them into N short documents.

This is designed for mind-clone-advisor bootstrapping where you want >=10 docs
per person quickly without depending on many different websites.

Writes BOTH .txt and .md files. First line always includes Source URL.

Usage:
  python skills/mind-clone-advisor/scripts/build_minicorpus.py \
    --slug charlie-munger \
    --out skills/mind-clone-advisor/registry/corpus/charlie-munger/plain_text \
    --url https://en.wikipedia.org/wiki/Charlie_Munger \
    --url https://en.wikiquote.org/wiki/Charlie_Munger \
    --target 10

Proxy:
  Defaults to http://127.0.0.1:7897 (common local proxy). Override with --proxy.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


AGENT_ACCEPT = "text/markdown, text/html"


def fetch_paragraphs(url: str, proxies: dict | None, max_paras: int = 200) -> list[str]:
    r = requests.get(
        url,
        timeout=30,
        proxies=proxies,
        headers={
            "User-Agent": "Mozilla/5.0",
            # Cloudflare Markdown for Agents (if enabled) will return Markdown here.
            "Accept": AGENT_ACCEPT,
        },
    )
    r.raise_for_status()

    # If the origin returns Markdown directly, use it and skip HTML parsing.
    ctype = (r.headers.get("content-type") or "").lower()
    if "text/markdown" in ctype:
        if r.headers.get("x-markdown-tokens"):
            print(f"[markdown] x-markdown-tokens={r.headers.get('x-markdown-tokens')} url={url}")
        # Treat markdown blocks separated by blank lines as "paragraphs".
        paras = [p.strip() for p in re.split(r"\n\s*\n+", r.text) if p.strip()]
        return paras[:max_paras]

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    paras: list[str] = []

    def push(text: str):
        nonlocal paras
        t = re.sub(r"\s+", " ", text.strip())
        if len(t) < 60:
            return
        paras.append(t)

    # Prefer normal paragraphs
    for p in soup.find_all("p"):
        push(p.get_text(" ", strip=True))
        if len(paras) >= max_paras:
            return paras

    # Fallback: list items (often richer on some CN encyclopedia pages)
    for li in soup.find_all("li"):
        push(li.get_text(" ", strip=True))
        if len(paras) >= max_paras:
            return paras

    # Fallback: table cells (some pages store content in tables)
    for td in soup.find_all("td"):
        push(td.get_text(" ", strip=True))
        if len(paras) >= max_paras:
            return paras

    return paras


def chunk_paragraphs(paras: list[str], max_chars: int) -> list[str]:
    """Chunk paragraphs into ~max_chars docs.

    If a single paragraph is too long, split it by sentence-ish punctuation.
    """

    def split_long(p: str) -> list[str]:
        if len(p) <= max_chars:
            return [p]
        # First try split by sentence-ish punctuation (CN/EN)
        parts = [s.strip() for s in re.split(r"(?<=[。！？.!?])\s+", p) if s.strip()]
        if len(parts) <= 1:
            # Fallback: hard-split by length
            return [p[i : i + max_chars] for i in range(0, len(p), max_chars)]

        out: list[str] = []
        buf: list[str] = []
        blen = 0
        for s in parts:
            add = len(s) + (1 if buf else 0)
            if buf and blen + add > max_chars:
                out.append(" ".join(buf))
                buf = [s]
                blen = len(s)
            else:
                buf.append(s)
                blen += add
        if buf:
            out.append(" ".join(buf))
        # If still too few, also hard-split long outputs
        final: list[str] = []
        for chunk in out:
            if len(chunk) <= max_chars:
                final.append(chunk)
            else:
                final.extend([chunk[i : i + max_chars] for i in range(0, len(chunk), max_chars)])
        return final

    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in paras:
        for piece in split_long(p):
            add = len(piece) + (2 if cur else 0)
            if cur and cur_len + add > max_chars:
                chunks.append("\n\n".join(cur))
                cur = [piece]
                cur_len = len(piece)
            else:
                cur.append(piece)
                cur_len += add
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--out", required=True, help="output plain_text dir")
    ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--target", type=int, default=10)
    ap.add_argument("--max-chars", type=int, default=3500)
    ap.add_argument("--proxy", default="http://127.0.0.1:7897")
    ap.add_argument("--start-index", type=int, default=1)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None

    # collect paragraphs from all urls
    all_chunks: list[tuple[str, str]] = []
    for url in args.url:
        paras = fetch_paragraphs(url, proxies)
        chunks = chunk_paragraphs(paras, args.max_chars)
        for c in chunks:
            all_chunks.append((url, c))

    if not all_chunks:
        raise SystemExit("no chunks extracted")

    # pick first target chunks (stable)
    picked = all_chunks[: args.target]

    for i, (url, body) in enumerate(picked, args.start_index):
        base = f"{args.slug}-{i:02d}-auto"
        content = f"Source: {url}\n\n{body}\n"
        (out_dir / (base + ".txt")).write_text(content, encoding="utf-8")
        (out_dir / (base + ".md")).write_text(content, encoding="utf-8")

    print(f"[ok] wrote {len(picked)} docs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
