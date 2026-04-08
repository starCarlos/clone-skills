#!/usr/bin/env python3
"""Recommend the closest profession adapter from a profession label or work description."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def normalize_profession_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.strip().lower())


def tokenize_text(value: str) -> list[str]:
    lowered = value.lower()
    ascii_tokens = re.findall(r"[a-z0-9]+", lowered)
    cjk_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    return ascii_tokens + cjk_tokens


def compact_nonempty(items: list[Any]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def load_adapters(workspace: Path) -> list[dict[str, Any]]:
    adapters_dir = workspace / "references" / "profession-adapters"
    loaded = []
    if not adapters_dir.exists():
        return loaded
    for path in sorted(adapters_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        loaded.append({"file": str(path), "data": data})
    return loaded


def build_adapter_keywords(data: dict[str, Any]) -> list[str]:
    stage_overrides = data.get("stage_overrides", {})
    execution_overrides = data.get("execution_overrides", {})
    keywords: list[str] = []
    keywords.extend(data.get("profession_aliases", []))
    keywords.extend(data.get("notes", []))
    keywords.extend(data.get("preferred_repo_types", []))
    if isinstance(stage_overrides, dict):
        for stage_name, stage_config in stage_overrides.items():
            keywords.append(stage_name)
            if isinstance(stage_config, dict):
                keywords.extend(stage_config.get("preferred_tools", []))
                keywords.extend(stage_config.get("extra_read", []))
                keywords.extend(stage_config.get("extra_produce", []))
                keywords.extend(stage_config.get("notes", []))
    if isinstance(execution_overrides, dict):
        tool_preferences = execution_overrides.get("tool_preferences", {})
        artifact_templates = execution_overrides.get("artifact_templates", {})
        if isinstance(tool_preferences, dict):
            keywords.extend(tool_preferences.keys())
        if isinstance(artifact_templates, dict):
            keywords.extend(artifact_templates.keys())
    return compact_nonempty(keywords)


def score_adapter(query: str, adapter: dict[str, Any]) -> dict[str, Any]:
    data = adapter["data"]
    aliases = data.get("profession_aliases", []) if isinstance(data.get("profession_aliases", []), list) else []
    normalized_query = normalize_profession_key(query)
    normalized_aliases = [normalize_profession_key(str(alias)) for alias in aliases]
    reasons: list[str] = []
    score = 0

    if normalized_query and normalized_query in normalized_aliases:
        score += 100
        reasons.append("normalized alias exact match")

    query_lower = query.lower()
    for alias in aliases:
        alias_text = str(alias).strip()
        if alias_text and alias_text.lower() in query_lower:
            score += 40
            reasons.append(f"alias substring match: {alias_text}")

    query_tokens = set(tokenize_text(query))
    keyword_hits = []
    for keyword in build_adapter_keywords(data):
        keyword_text = str(keyword).strip()
        if keyword_text and keyword_text.lower() in query_lower:
            score += 15
            keyword_hits.append({"keyword": keyword_text, "overlap": ["substring"]})
        keyword_tokens = set(tokenize_text(str(keyword)))
        if keyword_tokens and query_tokens.intersection(keyword_tokens):
            overlap = sorted(query_tokens.intersection(keyword_tokens))
            score += len(overlap) * 5
            keyword_hits.append({"keyword": keyword_text, "overlap": overlap})
    if keyword_hits:
        reasons.append(f"keyword overlap hits: {len(keyword_hits)}")

    summary = {
        "primary_name": str(aliases[0]).strip() if aliases else "",
        "profession_aliases": aliases,
        "notes": data.get("notes", []),
        "stage_override_stages": list(data.get("stage_overrides", {}).keys()) if isinstance(data.get("stage_overrides", {}), dict) else [],
        "preferred_repo_types": data.get("preferred_repo_types", []),
        "execution_override_keys": list(data.get("execution_overrides", {}).keys()) if isinstance(data.get("execution_overrides", {}), dict) else [],
    }
    return {
        "file": adapter["file"],
        "score": score,
        "reasons": compact_nonempty(reasons),
        "keyword_hits": keyword_hits[:10],
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend a profession adapter from text.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--query", required=True, help="Profession label or short work description.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    adapters = load_adapters(workspace)
    scored = [score_adapter(args.query, adapter) for adapter in adapters]
    scored.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("file", ""))))
    recommendation = {
        "query": args.query,
        "adapter_count": len(scored),
        "best_match": scored[0] if scored else None,
        "top_matches": scored[: max(args.top_k, 1)],
    }
    Path(args.output).write_text(json.dumps(recommendation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
