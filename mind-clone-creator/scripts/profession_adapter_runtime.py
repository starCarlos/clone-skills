#!/usr/bin/env python3
"""Shared runtime helpers for profession adapter loading and recommendation."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def normalize_profession_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.strip().lower())


def load_adapter(skill_root: Path, profession: str) -> dict[str, Any]:
    if not profession.strip():
        return {}
    profession_key = normalize_profession_key(profession)
    if not profession_key:
        return {}
    adapters_dir = skill_root / "references" / "profession-adapters"
    if not adapters_dir.exists():
        return {}
    for path in adapters_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        aliases = data.get("profession_aliases", [])
        if any(profession_key == normalize_profession_key(str(alias)) for alias in aliases):
            return data if isinstance(data, dict) else {}
    return {}


def recommend_adapter(skill_root: Path, query: str) -> dict[str, Any]:
    if not query.strip():
        return {}
    recommender = skill_root / "scripts" / "recommend_profession_adapter.py"
    if not recommender.exists():
        return {}
    with tempfile.TemporaryDirectory(prefix="profession-adapter-recommendation-") as tmpdir:
        output = Path(tmpdir) / "recommendation.json"
        proc = subprocess.run(
            ["python3", str(recommender), "--workspace", str(skill_root), "--query", query, "--output", str(output)],
            cwd=skill_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not output.exists():
            return {}
        data = json.loads(output.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}


def resolve_profession_adapter(
    skill_root: Path,
    profession_input: str,
    fallback_query: str = "",
    allow_recommendation: bool = True,
    auto_apply_recommendation: bool = True,
) -> dict[str, Any]:
    profession = profession_input.strip()
    explicit_input = bool(profession)
    adapter = load_adapter(skill_root, profession)
    matched_directly = bool(adapter)
    recommendation_query = ""
    recommendation: dict[str, Any] = {}
    fallback_recommendation_applied = False

    if allow_recommendation and not adapter:
        recommendation_query = profession or fallback_query.strip()
        recommendation = recommend_adapter(skill_root, recommendation_query)
        best_match = recommendation.get("best_match", {}) if isinstance(recommendation, dict) else {}
        recommended_primary_name = (
            str(best_match.get("summary", {}).get("primary_name", "")).strip()
            if isinstance(best_match, dict)
            else ""
        )
        recommended_score = int(best_match.get("score", 0)) if isinstance(best_match, dict) else 0
        if auto_apply_recommendation and recommended_primary_name and recommended_score > 0 and not explicit_input:
            profession = recommended_primary_name
            adapter = load_adapter(skill_root, profession)
            fallback_recommendation_applied = bool(adapter)

    return {
        "profession": profession,
        "adapter": adapter,
        "recommendation": recommendation,
        "resolution": {
            "explicit_input": explicit_input,
            "matched_directly": matched_directly,
            "fallback_recommendation_applied": fallback_recommendation_applied,
            "recommendation_query": recommendation_query,
        },
    }
