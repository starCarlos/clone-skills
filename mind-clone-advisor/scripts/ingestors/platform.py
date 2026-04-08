#!/usr/bin/env python3
"""Multi-platform content ingestor.

Supports: Weibo, Bilibili, Zhihu, Juejin, CSDN, Toutiao, Xiaohongshu, Twitter/X, Facebook, generic HTML.

source-config.json schema:
{
  "sources": [
    {"id": "weibo_001", "url": "https://weibo.com/...", "tags": []}
  ],
  "browser_mode": "auto",
  "sleep": 0.5
}
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

WECHAT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.40(0x1800282f) NetType/WIFI Language/zh_CN"
)

BLOCK_PATTERNS = [
    "请输入验证码",
    "验证",
    "访问过于频繁",
    "请求过于频繁",
    "请在微信客户端打开",
    "Access denied",
    "登录",
    "Sign in",
    "机器人",
    "captcha",
]


def load_config(path: Path) -> dict:
    """Load source config from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"sources": data, "browser_mode": "auto", "sleep": 0.5}
    if isinstance(data, dict) and "sources" in data:
        return data
    raise SystemExit("source-config must be a list or dict with 'sources'")


def sleep_jitter(base_seconds: float) -> None:
    """Sleep with random jitter to avoid rate limiting."""
    time.sleep(base_seconds + random.random() * base_seconds)


def safe_filename(text: str, max_len: int = 80) -> str:
    """Generate safe filename from text."""
    text = text.strip()
    text = re.sub(r"[\s\u00A0]+", " ", text)
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"_{2,}", "_", text)
    if len(text) > max_len:
        text = text[:max_len].rstrip("_ ").strip()
    return text or "untitled"


def is_blocked(html: str, status_code: int) -> bool:
    """Check if response indicates blocking/captcha."""
    if status_code in (401, 403, 429, 503):
        return True
    low = (html or "").lower()
    return any(p.lower() in low for p in BLOCK_PATTERNS)


def extract_json_script(html: str, key: str) -> dict | None:
    """Extract JSON from script tag or window variable."""
    # window.KEY = {...};
    m = re.search(rf"window\.{re.escape(key)}\s*=\s*({{.*?}})\s*;", html, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    # <script id="key">...</script>
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        el = soup.find("script", {"id": key})
        if el and el.string:
            try:
                return json.loads(el.string)
            except Exception:
                return None
    return None


def strip_html_text(html: str) -> str:
    """Convert HTML to plain text."""
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    # fallback: strip tags with regex
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_html_requests(url: str, headers: dict) -> str:
    """Fetch HTML using requests library."""
    if not requests:
        raise RuntimeError("requests library not available")

    session = requests.Session()
    resp = session.get(url, headers=headers, timeout=45)
    resp.raise_for_status()

    if is_blocked(resp.text, resp.status_code):
        raise RuntimeError("blocked by target site")

    return resp.text


def fetch_html_cloudscraper(url: str, headers: dict) -> str:
    """Fetch HTML using cloudscraper (bypasses Cloudflare)."""
    try:
        import cloudscraper  # type: ignore
    except Exception as e:
        raise RuntimeError(f"cloudscraper not available: {e}") from e

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "darwin", "mobile": False}
    )
    resp = scraper.get(url, headers=headers, timeout=45)
    resp.raise_for_status()

    if is_blocked(resp.text, resp.status_code):
        raise RuntimeError("blocked by target site")

    return resp.text


def fetch_html_playwright(url: str, user_agent: str) -> str:
    """Fetch HTML using Playwright (headless browser)."""
    try:
        import asyncio
        from playwright.async_api import async_playwright
    except Exception as e:
        raise RuntimeError(f"playwright not available: {e}") from e

    async def _run() -> str:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(user_agent=user_agent)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            await browser.close()
            return html

    return asyncio.run(_run())


def fetch_html(url: str, headers: dict, browser_mode: str) -> str:
    """Fetch HTML with 3-level degradation: requests -> cloudscraper -> playwright."""
    if browser_mode == "none":
        return fetch_html_requests(url, headers)

    if browser_mode == "playwright":
        return fetch_html_playwright(url, headers.get("User-Agent", DEFAULT_UA))

    # auto: try requests first, then cloudscraper, then playwright
    try:
        return fetch_html_requests(url, headers)
    except Exception:
        try:
            return fetch_html_cloudscraper(url, headers)
        except Exception:
            return fetch_html_playwright(url, headers.get("User-Agent", DEFAULT_UA))


def fetch_weibo(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Weibo post via mobile API."""
    if not requests:
        raise RuntimeError("requests library required for Weibo")

    # Extract status ID
    m = re.search(r"/status/([A-Za-z0-9]+)", url) or re.search(r"/detail/([A-Za-z0-9]+)", url)
    if not m:
        m = re.search(r"/([A-Za-z0-9]+)$", url)
    if not m:
        raise RuntimeError("weibo status id not found")

    sid = m.group(1)
    api = f"https://m.weibo.cn/statuses/show?id={sid}"

    session = requests.Session()
    resp = session.get(api, headers={"User-Agent": DEFAULT_UA, "Referer": "https://m.weibo.cn/"}, timeout=30)
    resp.raise_for_status()

    data = resp.json().get("data") or {}
    title = data.get("page_info", {}).get("title") or data.get("text") or ""
    text_html = data.get("text") or ""
    text = strip_html_text(text_html)

    meta = {
        "author": (data.get("user") or {}).get("screen_name") or "",
        "created_at": data.get("created_at") or "",
        "weibo_id": sid,
    }

    return title, text, meta


def fetch_bilibili(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Bilibili video or article."""
    if not requests:
        raise RuntimeError("requests library required for Bilibili")

    session = requests.Session()

    # Video
    m = re.search(r"/video/(BV[0-9A-Za-z]+)", url)
    if m:
        bvid = m.group(1)
        api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        resp = session.get(api, headers={"User-Agent": DEFAULT_UA, "Referer": url}, timeout=30)
        resp.raise_for_status()

        payload = resp.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"bilibili api code={payload.get('code')}")

        data = payload.get("data") or {}
        title = data.get("title") or ""
        text = data.get("desc") or ""
        meta = {
            "author": (data.get("owner") or {}).get("name") or "",
            "pubdate": data.get("pubdate") or "",
            "bvid": data.get("bvid") or bvid,
            "aid": data.get("aid") or "",
        }
        return title, text, meta

    # Article (read/cv)
    m = re.search(r"/read/cv(\d+)", url)
    if m:
        html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)
        init = extract_json_script(html, "__INITIAL_STATE__") or extract_json_script(html, "__NEXT_DATA__")

        if init:
            data = init.get("readInfo") or init.get("props", {}).get("pageProps", {}).get("readInfo") or {}
            title = data.get("title") or ""
            text = strip_html_text(data.get("content") or "")
            meta = {"author": (data.get("author") or {}).get("name") or "", "cv": m.group(1)}
            return title, text, meta

        # Fallback: html text
        return "", strip_html_text(html), {}

    raise RuntimeError("bilibili url not recognized")


def fetch_zhihu(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Zhihu article or answer."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)
    init = extract_json_script(html, "__INITIAL_STATE__") or extract_json_script(html, "js-initialData")

    if not init:
        return "", strip_html_text(html), {}

    entities = init.get("entities") or {}

    # Article
    m = re.search(r"/p/(\d+)", url)
    if m:
        aid = m.group(1)
        art = (entities.get("articles") or {}).get(aid) or {}
        title = art.get("title") or ""
        text = strip_html_text(art.get("content") or "")
        meta = {"author": (art.get("author") or {}).get("name") or "", "id": aid}
        return title, text, meta

    # Answer
    m = re.search(r"/answer/(\d+)", url)
    if m:
        ans_id = m.group(1)
        ans = (entities.get("answers") or {}).get(ans_id) or {}
        title = (ans.get("question") or {}).get("title") or ""
        text = strip_html_text(ans.get("content") or "")
        meta = {"author": (ans.get("author") or {}).get("name") or "", "id": ans_id}
        return title, text, meta

    return "", strip_html_text(html), {}


def fetch_juejin(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Juejin article."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)

    if not BeautifulSoup:
        return "", strip_html_text(html), {}

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    content = (
        soup.select_one("div.markdown-body")
        or soup.select_one("div.article-content")
        or soup.select_one("article")
    )

    if content:
        text = content.get_text("\n", strip=True)
    else:
        text = strip_html_text(html)

    return title, text, {}


def fetch_csdn(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch CSDN article."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)

    if not BeautifulSoup:
        return "", strip_html_text(html), {}

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    content = soup.select_one("#content_views") or soup.select_one("article")

    if content:
        text = content.get_text("\n", strip=True)
    else:
        text = strip_html_text(html)

    return title, text, {}


def fetch_toutiao(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Toutiao article."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)
    init = extract_json_script(html, "__NEXT_DATA__") or extract_json_script(html, "__INITIAL_STATE__")

    if init:
        title = ""
        text = ""
        data = init

        if "props" in init:
            data = init["props"].get("pageProps") or {}

        if isinstance(data, dict):
            title = data.get("title") or data.get("article", {}).get("title") or ""
            content = data.get("content") or data.get("article", {}).get("content") or ""
            text = strip_html_text(content) if content else ""

        if text:
            return title, text, {}

    return "", strip_html_text(html), {}


def fetch_xhs(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch Xiaohongshu note."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)
    init = extract_json_script(html, "__INITIAL_STATE__")

    if init:
        note = init.get("note") or init.get("noteDetail") or {}
        title = note.get("title") or ""
        text = note.get("desc") or ""
        return title, text, {}

    return "", strip_html_text(html), {}


def fetch_wechat(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch WeChat public account article."""
    html = fetch_html(url, {"User-Agent": WECHAT_UA, "Referer": "https://mp.weixin.qq.com/"}, browser_mode)

    if not BeautifulSoup:
        return "", strip_html_text(html), {}

    soup = BeautifulSoup(html, "html.parser")
    title = ""
    title_tag = soup.find(id="activity-name")
    if title_tag:
        title = title_tag.get_text(strip=True)

    content = soup.select_one("#js_content")
    if content:
        text = content.get_text("\n", strip=True)
    else:
        text = strip_html_text(html)

    return title, text, {}


def fetch_generic(url: str, browser_mode: str) -> tuple[str, str, dict]:
    """Fetch generic HTML page."""
    html = fetch_html(url, {"User-Agent": DEFAULT_UA, "Referer": url}, browser_mode)

    if not BeautifulSoup:
        return "", strip_html_text(html), {}

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = strip_html_text(html)

    return title, text, {}


def choose_handler(url: str) -> str:
    """Choose appropriate handler based on URL."""
    host = urlparse(url).netloc.lower()

    if host.endswith("mp.weixin.qq.com"):
        return "wechat"
    if "bilibili.com" in host:
        return "bilibili"
    if "zhihu.com" in host:
        return "zhihu"
    if "weibo.com" in host or "weibo.cn" in host:
        return "weibo"
    if "juejin.cn" in host:
        return "juejin"
    if "csdn.net" in host:
        return "csdn"
    if "toutiao.com" in host:
        return "toutiao"
    if "xiaohongshu.com" in host:
        return "xhs"

    return "generic"


def manifest_line(src: dict, file_name: str) -> str:
    """Generate manifest JSONL entry."""
    obj = {
        "id": src.get("id") or Path(file_name).stem,
        "title": src.get("title") or "",
        "source": src.get("url") or "",
        "author": src.get("author") or "",
        "date": src.get("date") or "",
        "type": src.get("type") or "article",
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

    config = load_config(Path(args.source_config))
    sources = config.get("sources", [])
    browser_mode = config.get("browser_mode", "auto")
    sleep_time = config.get("sleep", 0.5)

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

    # Process sources
    new_lines = []
    errors = []

    for src in sources:
        url = src.get("url", "")
        if not url:
            continue

        src_id = src.get("id", "")
        date = src.get("date", "")

        # Filter by --since
        if args.since and date and date < args.since:
            continue

        # Skip if already ingested
        if args.incremental and src_id in existing:
            continue

        if args.dry_run:
            print(f"[dry-run] {url} -> {src_id}")
            continue

        handler = choose_handler(url)

        try:
            # Fetch content
            if handler == "wechat":
                title, text, meta = fetch_wechat(url, browser_mode)
            elif handler == "bilibili":
                title, text, meta = fetch_bilibili(url, browser_mode)
            elif handler == "zhihu":
                title, text, meta = fetch_zhihu(url, browser_mode)
            elif handler == "weibo":
                title, text, meta = fetch_weibo(url, browser_mode)
            elif handler == "juejin":
                title, text, meta = fetch_juejin(url, browser_mode)
            elif handler == "csdn":
                title, text, meta = fetch_csdn(url, browser_mode)
            elif handler == "toutiao":
                title, text, meta = fetch_toutiao(url, browser_mode)
            elif handler == "xhs":
                title, text, meta = fetch_xhs(url, browser_mode)
            else:
                title, text, meta = fetch_generic(url, browser_mode)

            if not text:
                print(f"[warn] No content extracted from {url}", file=sys.stderr)
                errors.append(src_id or url)
                sleep_jitter(sleep_time)
                continue

            # Use provided title or extracted title
            final_title = src.get("title") or title

            # Generate ID if not provided
            if not src_id:
                src_id = safe_filename(final_title or urlparse(url).path.split("/")[-1])

            # Save raw HTML (we don't have it in this flow, so skip or save metadata)
            raw_path = full_dir / f"{src_id}.json"
            raw_path.write_text(json.dumps({"url": url, "meta": meta}, ensure_ascii=False), encoding="utf-8")

            # Save plain text
            fname = f"{date}__{src_id}.md" if date else f"{src_id}.md"
            plain_path = plain_dir / fname

            content_lines = []
            if final_title:
                content_lines.append(final_title)
                content_lines.append("")
            content_lines.append(text)

            plain_path.write_text("\n".join(content_lines).strip() + "\n", encoding="utf-8")

            # Add to manifest
            src_data = {
                "id": src_id,
                "title": final_title,
                "url": url,
                "author": src.get("author") or meta.get("author", ""),
                "date": date,
                "type": src.get("type", "article"),
                "reliability": src.get("reliability", "原文直接引语"),
                "tags": src.get("tags", []),
            }
            new_lines.append(manifest_line(src_data, plain_path.name))

        except Exception as exc:
            print(f"[warn] Failed to process {url}: {exc}", file=sys.stderr)
            errors.append(src_id or url)

        # Sleep to avoid rate limiting
        sleep_jitter(sleep_time)

    # Write manifest
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
