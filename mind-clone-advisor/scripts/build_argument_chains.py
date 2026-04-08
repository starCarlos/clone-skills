#!/usr/bin/env python3
"""Extract argument chains (cause -> conclusion, evidence -> conclusion) from plain_text.

Uses domain_config.json for cleanup patterns. Causal patterns and evidence markers
are generic language features, not domain-specific.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from domain_config import CAUSE_PATTERNS_RAW, EVIDENCE_MARKERS, load_config
from utils import count_cjk, count_latin, extract_title, parse_date_from_filename, split_paragraphs, split_sentences, setup_logging

logger = setup_logging(__name__)


def compile_cause_patterns():
    """Compile regex patterns from raw tuples."""
    return [(re.compile(pat), rel) for pat, rel in CAUSE_PATTERNS_RAW]


CAUSE_PATTERNS = compile_cause_patterns()

CLAIM_MARKERS = [
    "我认为",
    "我觉得",
    "我的观点",
    "关键是",
    "核心是",
    "本质是",
    "结论是",
    "we believe",
    "we think",
    "our view",
    "the point is",
    "the key is",
    "the core is",
]

CONCLUSION_MARKERS = [
    "因此",
    "所以",
    "于是",
    "这意味着",
    "这说明",
    "所以说",
    "therefore",
    "thus",
    "hence",
    "as a result",
    "so",
    "which means",
    "this means",
]



def clean_sentence(s: str, cleanup_patterns: list[str]) -> str:
    """Clean sentence using domain-specific cleanup patterns from config."""
    s = s.replace("\u200d", "")
    # Apply domain-specific cleanup patterns
    for pat in cleanup_patterns:
        s = s.replace(pat, "")
    # Generic cleanup (not domain-specific)
    s = re.sub(r"^[-*•·]+\s*", "", s)
    s = re.sub(r"^\d+[.)、\s]+", "", s)
    s = re.sub(r"^Q[:：]\s*", "", s, flags=re.I)
    s = re.sub(r"^A[:：]\s*", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_fragment(text: str, cleanup_patterns: list[str]) -> str:
    text = clean_sentence(text, cleanup_patterns)
    text = re.sub(r"^[,;:，；：]+", "", text).strip()
    text = re.sub(r"[,;:，；：]+$", "", text).strip()
    text = re.sub(r"^(and|but|so|therefore|thus|because|since)\b\s*", "", text, flags=re.I)
    text = re.sub(r"^(所以|因此|因为|但是|但|而|于是)\s*", "", text)
    return text.strip()


def is_valid_fragment(text: str) -> bool:
    if not text:
        return False
    if len(text) < 8:
        return False
    if count_cjk(text) + count_latin(text) < 8:
        return False
    if len(text) > 360:
        return False
    return True


def is_valid_sentence(text: str) -> bool:
    text = text.strip()
    if not is_valid_fragment(text):
        return False
    if re.fullmatch(r"[0-9\s,.-]+", text):
        return False
    return True


def match_cause(sentence: str, cleanup_patterns: list[str]):
    for pat, rel in CAUSE_PATTERNS:
        m = pat.match(sentence)
        if m:
            a = normalize_fragment(m.group(1), cleanup_patterns)
            b = normalize_fragment(m.group(2), cleanup_patterns)
            if is_valid_fragment(a) and is_valid_fragment(b):
                return rel, a, b
    return None


def is_claim(sentence: str) -> bool:
    s = sentence.lower()
    return any(m.lower() in s for m in CLAIM_MARKERS)


def is_conclusion_sentence(sentence: str) -> bool:
    s = sentence.lower()
    return any(m.lower() in s for m in CONCLUSION_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    cleanup_patterns = cfg.get("cleanup_patterns", [])

    plain_dir = Path(args.plain_text_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(plain_dir.glob("*.md"))
    if args.limit:
        paths = paths[: args.limit]

    chains = []
    seen = set()

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(text)
        date = parse_date_from_filename(path.name) or ""

        paras = split_paragraphs(text)
        for para in paras:
            sentences = [clean_sentence(s, cleanup_patterns) for s in split_sentences(para)]
            sentences = [s for s in sentences if is_valid_sentence(s)]
            last_claim = None
            prev_sentence = None
            for s in sentences:
                match = match_cause(s, cleanup_patterns)
                if match:
                    rel, cause, effect = match
                    last_claim = effect
                    key = (rel, cause, effect, "", path.name)
                    if key not in seen:
                        seen.add(key)
                        chains.append(
                            {
                                "type": rel,
                                "cause": cause,
                                "conclusion": effect,
                                "evidence": "",
                                "source_file": path.name,
                                "title": title,
                                "date": date,
                            }
                        )
                    prev_sentence = s
                    continue

                if is_conclusion_sentence(s) and prev_sentence:
                    cause = normalize_fragment(prev_sentence, cleanup_patterns)
                    conclusion = normalize_fragment(s, cleanup_patterns)
                    if is_valid_fragment(cause) and is_valid_fragment(conclusion):
                        key = ("inferred", cause, conclusion, "", path.name)
                        if key not in seen:
                            seen.add(key)
                            chains.append(
                                {
                                    "type": "inferred",
                                    "cause": cause,
                                    "conclusion": conclusion,
                                    "evidence": "",
                                    "source_file": path.name,
                                    "title": title,
                                    "date": date,
                                }
                            )
                        last_claim = conclusion
                    prev_sentence = s
                    continue

                if is_claim(s):
                    last_claim = s
                    prev_sentence = s
                    continue

                if any(m in s for m in EVIDENCE_MARKERS) and last_claim:
                    evidence = s
                    key = ("evidence", "", last_claim, evidence, path.name)
                    if key not in seen:
                        seen.add(key)
                        chains.append(
                            {
                                "type": "evidence",
                                "cause": "",
                                "conclusion": last_claim,
                                "evidence": evidence,
                                "source_file": path.name,
                                "title": title,
                                "date": date,
                            }
                        )
                prev_sentence = s

    jsonl_path = out_dir / "argument_chains.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for c in chains:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    md_lines = ["# 论证链摘要", "", f"- 链条数：{len(chains)}", ""]
    for c in chains[:40]:
        if c["type"] == "evidence":
            md_lines.append(f"- [证据] {c['evidence']} → 支持：{c['conclusion']}")
        else:
            md_lines.append(f"- [{c['type']}] 因：{c['cause']} → 结：{c['conclusion']}")
    (out_dir / "argument_chains.md").write_text("\n".join(md_lines), encoding="utf-8")

    logger.info(f"[done] chains={len(chains)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
