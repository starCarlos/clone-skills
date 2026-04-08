#!/usr/bin/env python3
"""Lightweight topic modeling utilities (TF-IDF + LSA) with stopword filtering.

Supports both English tokens and CJK bi-grams for Chinese corpora.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

import numpy as np

from domain_config import STOPWORDS_CJK, STOPWORDS_EN


DEFAULT_PHRASES = {
    # General value investing
    "intrinsic value": "intrinsic_value",
    "margin of safety": "margin_of_safety",
    "circle of competence": "circle_of_competence",
    "owner earnings": "owner_earnings",
    "mr. market": "mr_market",
    "mr market": "mr_market",
    "free cash flow": "free_cash_flow",
    "competitive advantage": "competitive_advantage",
    "pricing power": "pricing_power",
    "capital allocation": "capital_allocation",
    "share repurchase": "share_repurchase",
    "share repurchases": "share_repurchase",
    "stock repurchase": "share_repurchase",
    "stock repurchases": "share_repurchase",
    "net tangible assets": "net_tangible_assets",
    "return on equity": "roe",
    "return on capital": "roc",
    "return on invested capital": "roic",
    "economic goodwill": "economic_goodwill",
    "long term": "long_term",
    "short term": "short_term",
    "permanent loss": "permanent_loss",
    "business value": "business_value",
    "book value": "book_value",
    # Damodaran - valuation methodology
    "discounted cash flow": "dcf",
    "cash flow": "cash_flow",
    "risk free rate": "risk_free_rate",
    "risk-free rate": "risk_free_rate",
    "equity risk premium": "equity_risk_premium",
    "cost of capital": "cost_of_capital",
    "cost of equity": "cost_of_equity",
    "relative valuation": "relative_valuation",
    "terminal value": "terminal_value",
    "narrative and numbers": "narrative_and_numbers",
    "price to earnings": "pe_ratio",
    "price to book": "pb_ratio",
    "price earnings": "pe_ratio",
    "enterprise value": "enterprise_value",
    "market capitalization": "market_cap",
    "expected growth": "expected_growth",
    "reinvestment rate": "reinvestment_rate",
    "excess returns": "excess_returns",
    "mature company": "mature_company",
    "young company": "young_company",
    "corporate governance": "corporate_governance",
    "real options": "real_options",
    # Peter Lynch - growth investing
    "price earnings ratio": "pe_ratio",
    "earnings growth": "earnings_growth",
    "earnings per share": "eps",
    "ten bagger": "ten_bagger",
    "ten-bagger": "ten_bagger",
    "fast grower": "fast_grower",
    "slow grower": "slow_grower",
    "asset play": "asset_play",
    "growth rate": "growth_rate",
    "invest in what you know": "invest_what_you_know",
    "wall street": "wall_street",
    "mutual fund": "mutual_fund",
    "small company": "small_company",
    "local knowledge": "local_knowledge",
    # Soros - reflexivity and macro
    "boom bust": "boom_bust",
    "boom-bust": "boom_bust",
    "far from equilibrium": "far_from_equilibrium",
    "open society": "open_society",
    "central bank": "central_bank",
    "exchange rate": "exchange_rate",
    "financial markets": "financial_markets",
    "market fundamentalism": "market_fundamentalism",
    "radical fallibility": "radical_fallibility",
    "human uncertainty": "human_uncertainty",
    "cognitive function": "cognitive_function",
    "manipulative function": "manipulative_function",
    "fertile fallacy": "fertile_fallacy",
    "super bubble": "super_bubble",
    "credit default": "credit_default",
    # Greenblatt - magic formula and special situations
    "magic formula": "magic_formula",
    "earnings yield": "earnings_yield",
    "special situation": "special_situation",
    "special situations": "special_situation",
    "risk reward": "risk_reward",
    "risk-reward": "risk_reward",
    "stock market": "stock_market",
    "value investing": "value_investing",
    "market inefficiency": "market_inefficiency",
    # Marks - cycle and risk
    "second level thinking": "second_level_thinking",
    "second-level thinking": "second_level_thinking",
    "market cycle": "market_cycle",
    "credit cycle": "credit_cycle",
    "risk premium": "risk_premium",
    "risk management": "risk_management",
}

STOPWORDS_EN_EXT = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "to", "up", "with", "without", "over", "under", "between", "about", "after", "before", "during",
    "this", "that", "these", "those", "it", "its", "it's", "they", "them", "their", "we", "us", "our", "you", "your",
    "he", "him", "his", "she", "her", "i", "me", "my", "mine", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done", "have", "has", "had", "having", "will", "would", "can", "could", "may", "might",
    "should", "shall", "must", "not", "no", "yes", "all", "any", "each", "every", "some", "many", "much", "more",
    "most", "few", "less", "very", "just", "only", "also", "too", "now", "then", "there", "here", "when", "where",
    "why", "how", "what", "who", "whom", "which", "because", "so", "such",
    # Transcript noise / filler
    "yeah", "uh", "um", "er", "ah", "oh", "huh", "okay", "ok", "thanks", "thank", "please", "applause",
    "laughter", "laughs", "laugh", "smiles", "audience", "question", "answer", "q", "a",
    # Generic boilerplate
    "report", "reports", "letter", "meeting", "annual", "chapter", "page",
    "percent", "million", "billion",
    "http", "https", "www", "com", "org", "net", "pdf", "doc",
}


def _replace_phrases(text: str, phrases: dict[str, str] | None = None) -> str:
    merged = dict(DEFAULT_PHRASES)
    if phrases:
        merged.update(phrases)
    out = text
    for phrase, token in merged.items():
        out = re.sub(rf"\b{re.escape(phrase)}\b", token, out, flags=re.IGNORECASE)
    return out


def _english_tokens(text: str, phrases: dict[str, str] | None = None) -> list[str]:
    text = text.lower()
    text = _replace_phrases(text, phrases)
    text = re.sub(r"[^a-z_\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    tokens = text.split()
    stop = STOPWORDS_EN.union(STOPWORDS_EN_EXT)
    return [t for t in tokens if t not in stop and len(t) >= 3]


def _cjk_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for seg in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(seg) == 2:
            tokens.append(seg)
            continue
        for i in range(len(seg) - 1):
            tok = seg[i : i + 2]
            if tok in STOPWORDS_CJK:
                continue
            tokens.append(tok)
    return tokens


def tokenize(text: str, phrases: dict[str, str] | None = None) -> list[str]:
    if not text:
        return []
    return _english_tokens(text, phrases) + _cjk_tokens(text)


def build_tfidf(
    docs: Iterable[str],
    *,
    min_df: int = 2,
    max_df_ratio: float = 0.6,
    max_features: int | None = None,
    phrases: dict[str, str] | None = None,
) -> tuple[np.ndarray, list[str], list[list[str]]]:
    docs = list(docs)
    tokenized = [tokenize(d, phrases) for d in docs]

    df = Counter()
    for toks in tokenized:
        for t in set(toks):
            df[t] += 1

    n_docs = max(1, len(docs))
    max_df = max(1, math.floor(n_docs * max_df_ratio))
    vocab = [t for t, c in df.items() if c >= min_df and c <= max_df]
    vocab.sort()
    if max_features is not None and max_features > 0 and len(vocab) > max_features:
        vocab = sorted(vocab, key=lambda t: df[t], reverse=True)[:max_features]

    index = {t: i for i, t in enumerate(vocab)}
    tf = np.zeros((n_docs, len(vocab)), dtype=np.float64)

    for i, toks in enumerate(tokenized):
        counts = Counter(t for t in toks if t in index)
        for t, c in counts.items():
            tf[i, index[t]] = float(c)

    if tf.shape[1] == 0:
        return tf, vocab, tokenized

    idf = np.zeros((len(vocab),), dtype=np.float64)
    for t, i in index.items():
        idf[i] = math.log((1 + n_docs) / (1 + df.get(t, 0))) + 1.0

    tfidf = tf * idf
    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    tfidf = tfidf / norms
    return tfidf, vocab, tokenized


def lsa_topics(
    tfidf: np.ndarray,
    vocab: list[str],
    *,
    num_topics: int = 6,
    top_n: int = 8,
) -> tuple[list[list[str]], np.ndarray]:
    if tfidf.size == 0 or tfidf.shape[1] == 0:
        return [], np.zeros((tfidf.shape[0], 0), dtype=np.float64)

    u, s, vt = np.linalg.svd(tfidf, full_matrices=False)
    k = min(num_topics, vt.shape[0])
    vt = vt[:k]
    s = s[:k]

    topics: list[list[str]] = []
    for i in range(k):
        comp = vt[i]
        idx = np.argsort(np.abs(comp))[::-1][:top_n]
        topics.append([vocab[j] for j in idx])

    doc_topics = u[:, :k] * s
    return topics, doc_topics


def display_term(term: str) -> str:
    return term.replace("_", " ")
