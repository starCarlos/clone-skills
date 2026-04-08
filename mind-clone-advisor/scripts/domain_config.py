"""Shared domain configuration loader for mind-clone scripts.

All scripts import load_config() to get domain-specific keywords, beliefs,
themes, etc. instead of using hardcoded constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _empty_config() -> dict[str, Any]:
    """Return a minimal empty config (no domain-specific content)."""
    return {
        "person": "",
        "top_terms": [],
        "model_terms": [],
        "value_terms": [],
        "style_terms": [],
        "belief_buckets": {},
        "theme_seeds": {},
        "language_markers": [],
        "cleanup_patterns": [],
        "line_noise_patterns": [],
        "generic_terms": [],
        "phrases": {},
    }


# ---------------------------------------------------------------------------
# Universal web noise patterns (login dialogs, ads, share buttons, etc.)
# Automatically merged into cleanup_patterns by load_config().
#
# Split into two safety tiers:
#   _LINE_NOISE:  short/ambiguous patterns — only removed when they appear
#                 as standalone lines (not inside article sentences).
#   _SUBSTRING_NOISE: longer, unambiguous patterns — safe for substring removal.
# ---------------------------------------------------------------------------

_LINE_NOISE: list[str] = [
    # These are short words that legitimately appear in article text about
    # auth systems, advertising industry, etc. Only strip when the whole
    # trimmed line matches (handled by clean_line_noise()).
    "登录", "注册", "登入", "转发", "点赞", "收藏", "订阅",
    "广告", "推广", "赞助", "评论", "试用", "阅读量",
    "Sign in", "Sign up", "Log in", "Register", "Subscribe",
    "Previous", "Next", "Premium",
    "Cookie", "cookie",
]

_SUBSTRING_NOISE: list[str] = [
    # Longer / unambiguous patterns safe for substring replacement.
    # Login / auth
    "忘记密码", "Forgot password", "Remember me", "记住我",
    # Captcha / verification
    "验证码", "滑动验证", "captcha", "CAPTCHA", "人机验证",
    # Sharing / social
    "分享到", "Share to", "关注作者",
    "喜欢就点", "阅读原文", "Read more", "展开全文",
    # Subscription / paywall
    "付费阅读", "会员专享", "开通VIP", "Free trial",
    # Ads / promotion
    "立即购买", "Buy now", "限时优惠", "Special offer",
    "Sponsored", "Advertisement",
    # Navigation / boilerplate
    "返回顶部", "Back to top", "上一篇", "下一篇",
    "相关推荐", "猜你喜欢", "热门文章", "最新文章",
    # Cookie / privacy
    "隐私政策", "Privacy Policy", "用户协议", "Terms of Service",
    # WeChat specific
    "微信扫一扫", "长按识别", "二维码", "QR code",
    "公众号", "小程序",
]

# Combined for backward compat (only the safe substring patterns go here)
UNIVERSAL_WEB_NOISE: list[str] = _SUBSTRING_NOISE

# Expose line-level noise for scripts that do line-level cleaning
UNIVERSAL_LINE_NOISE: list[str] = _LINE_NOISE


def load_config(path: str | Path | None) -> dict[str, Any]:
    """Load domain_config.json. Returns empty defaults if path is None or missing.

    Automatically merges UNIVERSAL_WEB_NOISE into cleanup_patterns.
    """
    if path is None:
        cfg = _empty_config()
    else:
        p = Path(path)
        if not p.exists():
            cfg = _empty_config()
        else:
            data = json.loads(p.read_text(encoding="utf-8"))
            # Merge with defaults so callers can safely access any key
            cfg = _empty_config()
            cfg.update(data)
    # Auto-merge universal web noise into cleanup_patterns (safe substrings only)
    existing = set(cfg["cleanup_patterns"])
    for pat in UNIVERSAL_WEB_NOISE:
        if pat not in existing:
            cfg["cleanup_patterns"].append(pat)
    # Auto-merge line-level noise patterns
    existing_line = set(cfg["line_noise_patterns"])
    for pat in UNIVERSAL_LINE_NOISE:
        if pat not in existing_line:
            cfg["line_noise_patterns"].append(pat)
    return cfg


# ---------------------------------------------------------------------------
# Generic Chinese language patterns (not domain-specific, shared by scripts)
# ---------------------------------------------------------------------------

REASONING_PATTERNS: dict[str, list[str]] = {
    "因果": ["因为", "所以", "因此", "本质", "根本",
             "because", "therefore", "thus", "hence", "as a result", "leads to", "results in"],
    "对比": ["对比", "相比", "反过来", "不是", "而是",
             "in contrast", "on the other hand", "unlike", "whereas", "however", "but rather"],
    "类比": ["比如", "例如", "像", "类似", "比喻",
             "for example", "for instance", "similar to", "analogous", "just as"],
    "归纳": ["总结", "归纳", "核心", "关键", "一脉相承",
             "in summary", "overall", "the key", "fundamentally", "essentially"],
    "演绎": ["推导", "演绎", "由此可见",
             "it follows", "which means", "this implies", "consequently"],
    "反证": ["反证", "反过来", "否则",
             "otherwise", "if not", "conversely"],
}

STANCE_PATTERNS: list[str] = [
    "支持", "反对", "应该", "不应该", "建议", "不建议",
    "必须", "不要", "尽量", "优先", "最好",
    # English
    "I believe", "I think", "we should", "we must", "I recommend",
    "you should", "never", "always", "avoid", "prefer",
    "the best", "the worst", "critical", "essential",
]

REL_PATTERNS: dict[str, list[str]] = {
    "causal": ["因为", "所以", "因此", "导致", "结果", "本质",
               "because", "therefore", "thus", "hence", "leads to", "results in", "causes"],
    "contrast": ["不是", "而是", "相反", "对比", "相比", "不同", "反过来", "但是", "但", "不过",
                 "however", "in contrast", "on the other hand", "unlike", "whereas", "nevertheless"],
    "analogy": ["像", "比如", "例如", "类似", "好比",
                "for example", "for instance", "similar to", "analogous", "just as"],
    "advice": ["建议", "应该", "不要", "尽量", "优先", "最好", "必须", "需要", "可以", "别",
               "should", "must", "recommend", "avoid", "prefer", "better to", "ought to"],
}

CAUSE_PATTERNS_RAW: list[tuple[str, str]] = [
    (r"因为(.+?)，所以(.+?)$", "because"),
    (r"因为(.+?)所以(.+?)$", "because"),
    (r"(.+?)导致(.+?)$", "causes"),
    (r"(.+?)因此(.+?)$", "therefore"),
    (r"(.+?)所以(.+?)$", "therefore"),
    (r"如果(.+?)，?就(.+?)$", "if_then"),
    # English
    (r"^because (.+?), (.+?)$", "because"),
    (r"^(.+?) because (.+?)$", "because"),
    (r"^if (.+?),? then (.+?)$", "if_then"),
    (r"^(.+?) leads to (.+?)$", "causes"),
    (r"^(.+?) results in (.+?)$", "causes"),
    (r"^(.+?) causes (.+?)$", "causes"),
    (r"^(.+?) therefore (.+?)$", "therefore"),
    (r"^(.+?) thus (.+?)$", "therefore"),
    (r"^(.+?) so (.+?)$", "therefore"),
]

EVIDENCE_MARKERS: list[str] = [
    "比如", "例如", "案例", "数据", "研究", "统计",
    "报告", "历史", "电影", "故事", "书里",
    "for example",
    "for instance",
    "evidence",
    "data",
    "study",
    "studies",
    "research",
    "statistics",
    "report",
    "according to",
    "historically",
    "case",
    "in practice",
    "in reality",
]

DECISION_PATTERNS: dict[str, list[str]] = {
    "风险意识": ["风险", "不确定", "波动",
                  "risk", "uncertainty", "volatility", "downside"],
    "风险偏好-激进": ["激进", "冒险",
                       "aggressive", "bold", "speculative"],
    "风险偏好-稳健": ["稳健", "保守",
                       "conservative", "prudent", "defensive", "margin of safety"],
    "时间偏好-长期": ["长期", "拉长时间",
                       "long term", "long-term", "patient", "compounding"],
    "时间偏好-短期": ["短期", "及时",
                       "short term", "short-term", "tactical", "timing"],
    "信息偏好-数据": ["数据", "量化", "统计",
                       "data", "quantitative", "statistical", "empirical", "numbers"],
    "信息偏好-一线": ["一线", "线下", "场域", "圈子", "信息质量",
                       "firsthand", "on the ground", "primary research"],
}

STOPWORDS_CJK: set[str] = {
    "我们", "你们", "他们", "这个", "那个", "这些", "那些", "这样", "那样",
    "因为", "所以", "因此", "然后", "但是", "不过", "其实", "可能", "觉得",
    "认为", "知道", "可以", "应该", "不要", "必须", "开始", "后来", "今天",
    "如果", "就是", "还是", "一点", "一些", "很多", "非常", "比较", "时候",
    "事情", "问题", "什么", "如何", "怎么", "怎样", "一个", "两个", "三个",
    "已经", "一直", "关于", "不是", "不能", "不会", "一定", "永远", "自己",
}

STOPWORDS_EN: set[str] = {
    # Determiners & articles
    "the", "a", "an",
    # Conjunctions & prepositions
    "and", "or", "but", "if", "then", "than", "as", "at", "by", "for", "from",
    "in", "into", "of", "on", "to", "up", "with", "without", "over", "under",
    "between", "about", "after", "before", "during",
    # Pronouns
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "we", "us", "our", "you", "your", "he", "him", "his", "she", "her",
    "i", "me", "my", "mine",
    # Be / auxiliary verbs
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done",
    "have", "has", "had", "having",
    "will", "would", "can", "could", "may", "might", "should", "shall", "must",
    # Negation
    "not", "no",
    # Quantifiers & degree
    "all", "one", "any", "each", "every", "some", "many", "much", "more", "most",
    "few", "less", "very", "just", "even", "still", "also", "too", "only",
    # Adverbs / connectors
    "now", "then", "there", "here", "when", "where", "why", "how",
    "what", "who", "whom", "which", "because", "so", "such",
    "well", "back", "out", "yet",
    # Common verbs (too generic for keyword use)
    "make", "made", "take", "took", "get", "got", "come", "came",
    "give", "gave", "go", "went", "see", "saw", "know", "knew",
    "think", "thought", "want", "need", "like", "use", "used",
    # Other high-frequency words
    "other", "first", "last", "next", "new", "old", "good", "great",
    "long", "little", "own", "way", "time", "part",
    # Generic business / finance terms (too common to be distinctive)
    "work", "business", "company", "companies", "market", "markets",
    "percent", "million", "billion", "dollar", "dollars",
    "number", "people", "world", "year", "years",
}

# Suffix heuristics for classifying discovered keywords
MODEL_SUFFIXES: tuple[str, ...] = (
    # Chinese
    "模型", "曲线", "效应", "法则", "思维", "框架", "路径", "周期", "趋势",
    "定律", "理论", "原理", "范式", "策略", "机制",
    # English
    "model", "curve", "effect", "framework", "cycle", "trend",
    "theory", "principle", "paradigm", "strategy", "mechanism",
    "approach", "method", "formula", "ratio", "premium",
)

VALUE_SUFFIXES: tuple[str, ...] = (
    # Chinese
    "价值", "主义", "原则", "精神", "观念", "信念", "底线", "伦理",
    # English
    "value", "integrity", "principle", "belief", "discipline",
    "ethics", "conviction", "philosophy",
)

STYLE_WORDS: set[str] = {
    # Chinese
    "谨慎", "激进", "保守", "稳健", "快速", "长期", "聚焦", "简化",
    "高杠杆", "高频", "果断", "审慎", "灵活", "务实",
    # English
    "cautious", "aggressive", "conservative", "prudent", "patient",
    "contrarian", "systematic", "pragmatic", "disciplined", "flexible",
    "decisive", "focused", "long-term", "short-term",
}


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def validate_config(cfg: dict) -> list[str]:
    """Return a list of validation warnings for *cfg*."""
    warnings: list[str] = []
    if not cfg.get("top_terms"):
        warnings.append("top_terms is empty")
    if not cfg.get("model_terms"):
        warnings.append("model_terms is empty — no mental model keywords detected")
    if not cfg.get("value_terms"):
        warnings.append("value_terms is empty — no value/belief keywords detected")
    if not cfg.get("theme_seeds"):
        warnings.append("theme_seeds is empty — theme clustering will fall back to auto")
    if not cfg.get("belief_buckets"):
        warnings.append("belief_buckets is empty — hierarchy will use generic buckets")
    if cfg.get("person") == "":
        warnings.append("person name is empty")
    return warnings
