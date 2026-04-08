#!/usr/bin/env python3
"""Compute node weights for beliefs/models/topics based on extractions.

Uses domain_config.json for belief buckets and generic terms.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from domain_config import load_config
from utils import load_jsonl, setup_logging

logger = setup_logging(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out", required=True, help="output json path")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    belief_buckets = cfg.get("belief_buckets", {})
    generic_terms = set(cfg.get("generic_terms", []))

    items = load_jsonl(Path(args.input))
    if not items:
        raise SystemExit("no items")

    topic_counter = Counter()
    model_counter = Counter()

    for it in items:
        for k in it.get("keywords", []) or []:
            if k not in generic_terms:
                topic_counter[k] += 1
        for m in it.get("models", []) or []:
            model_counter[m] += 1

    belief_counter = Counter()
    for belief, kws in belief_buckets.items():
        for it in items:
            if set(it.get("keywords", []) or []) & set(kws):
                belief_counter[belief] += 1

    # Normalize weights
    def normalize(counter: Counter):
        if not counter:
            return {}
        max_v = max(counter.values())
        return {k: round(v / max_v, 3) for k, v in counter.items()}

    weights = {
        "beliefs": normalize(belief_counter),
        "models": normalize(model_counter),
        "topics": normalize(topic_counter),
        "raw_counts": {
            "beliefs": dict(belief_counter),
            "models": dict(model_counter),
            "topics": dict(topic_counter),
        },
    }

    Path(args.out).write_text(
        json.dumps(weights, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[done] out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
