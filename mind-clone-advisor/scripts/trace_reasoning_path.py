#!/usr/bin/env python3
"""Trace a reasoning path from query to beliefs/models/topics using keyword matching.

Uses domain_config.json for belief buckets and keyword vocabulary.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from domain_config import load_config
from utils import load_jsonl, setup_logging

logger = setup_logging(__name__)


DEFAULT_BELIEF_BUCKETS = {
    "认知与信息质量": {"信息差", "认知差", "认知", "information", "signal", "noise"},
    "正期望与概率下注": {"概率", "期望", "expected value", "probability", "odds"},
    "趋势与周期": {"趋势", "周期", "cycle", "trend", "liquidity"},
    "平台与结构价值": {"平台", "势能", "结构价值", "资源价值", "工具价值", "platform", "network effects", "infrastructure"},
    "非线性跃迁": {"非线性", "阶级跃迁", "上限", "天花板", "nonlinear", "phase change"},
    "客户导向与商业模式": {"商业模式", "客户", "获客", "流量", "定价", "business model", "pricing", "distribution"},
    "宏观与主权": {"美元", "流动性", "利率", "通胀", "财政", "geopolitics", "sovereign", "dollar", "rates", "inflation"},
    "加密与安全": {"比特币", "以太坊", "区块链", "安全", "去中心化", "bitcoin", "ethereum", "blockchain", "security", "decentralization"},
    "技术架构与权衡": {"扩容", "性能", "权衡", "架构", "protocol", "scaling", "tradeoff", "rollup", "l1", "l2"},
    "公共物品与治理": {"公共物品", "治理", "投票", "public goods", "governance", "quadratic"},
    "价值存储与数字财产": {"价值存储", "数字财产", "稀缺", "sound money", "store of value", "digital property"},
}

DEFAULT_KEYWORD_VOCAB = {
    "房产", "房地产", "房价", "杠杆", "现金流", "投资", "资产", "风险", "趋势", "周期",
    "机会", "平台", "势能", "认知", "信息差", "认知差", "上限", "天花板", "职业", "选择",
    "管理", "组织", "客户", "商业模式", "获客", "流量", "决策",
    "liquidity", "dollar", "rates", "inflation", "credit", "cycle", "trend", "bitcoin",
    "ethereum", "crypto", "blockchain", "security", "decentralization", "scaling", "rollup",
    "layer", "governance", "public goods", "privacy", "sovereign", "geopolitics",
    "sound money", "store of value", "digital property", "energy", "thermodynamics",
    "protocol", "mechanism", "infrastructure",
}

GENERIC = {
    "商业", "认知", "财富", "阶级", "机会", "逻辑", "公司", "行业",
    "market", "crypto", "blockchain", "token", "project", "system", "value",
}


def tokenize(text: str, keyword_vocab: set[str], belief_buckets: dict) -> set[str]:
    tokens = set()
    lower = text.lower()
    for k in keyword_vocab:
        if k in text or k in lower:
            tokens.add(k)
    for w in re.findall(r"[A-Za-z][A-Za-z']{2,}", lower):
        if w not in GENERIC:
            tokens.add(w)
    # map to belief keywords
    for belief, kws in belief_buckets.items():
        for k in kws:
            if k in text or k in lower:
                tokens.add(k)
    return tokens


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--query", required=True, help="user query")
    parser.add_argument("--out", required=True, help="output path")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    cfg = load_config(args.config)
    belief_buckets = cfg.get("belief_buckets", {}) or DEFAULT_BELIEF_BUCKETS
    keyword_vocab = set(cfg.get("top_terms", [])) or set(DEFAULT_KEYWORD_VOCAB)

    items = load_jsonl(Path(args.input))
    if not items:
        raise SystemExit("no items")

    q = args.query.strip()
    q_tokens = tokenize(q, keyword_vocab, belief_buckets)

    # score topics by keyword overlap
    topic_counter = Counter()
    model_counter = Counter()
    for it in items:
        kws = set([str(k).lower() for k in (it.get("keywords", []) or [])])
        ms = set([str(m).lower() for m in (it.get("models", []) or [])])
        overlap = kws & set([t.lower() for t in q_tokens])
        if overlap:
            for k in overlap:
                topic_counter[k] += 1
            for m in ms:
                model_counter[m] += 1

    # map to beliefs
    belief_scores = Counter()
    for belief, kws in belief_buckets.items():
        if q_tokens & set([str(k).lower() for k in kws]):
            belief_scores[belief] += 1

    # fallback: if no token hit, pick top themes by keyword frequency in corpus
    if not belief_scores:
        for belief in belief_buckets.keys():
            belief_scores[belief] = 1

    path = {
        "query": q,
        "beliefs": [b for b, _ in belief_scores.most_common(args.top)],
        "models": [m for m, _ in model_counter.most_common(args.top)],
        "topics": [t for t, _ in topic_counter.most_common(args.top)],
    }

    Path(args.out).write_text(
        json.dumps(path, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[done] out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
