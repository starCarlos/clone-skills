#!/usr/bin/env python3
"""Backfill required SKILL.md scaffold sections for older persona skills."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MODE_BLOCK = """
## 轻重模式（避免小题大做）

### Quick 模式（默认）
适用于：
- 用户只要初步判断
- 信息还不完整
- 当前目标是初筛，不是正式决策

输出压缩为：
1. 一句话结论
2. 关键追问（2-4 个）
3. 核心判断（2-3 点）
4. 动作建议（1-2 条）

### Full 模式
适用于：
- 用户要求完整展开
- 需要原文锚点、反证、风险边界
- 问题本身是正式决策、复盘或观点冲突题
""".strip()

DEGRADE_BLOCK = """
## 不适用 / 降级场景
- 只需要事实检索，不需要人物判断框架
- 纯短线预测、拍脑袋表态、无约束的空泛站队
- 明显超出该人物能力圈，且用户也不给背景信息
- 用户只想模仿语气，不关心观点来源与推理路径
""".strip()

ANTI_BIAS_BLOCK = """
## 反偏见条款（必须保留）
- 不要把单条原文放大成普适结论，要回到长期稳定信念。
- 不要把“像这个人会说的话”当成“这个人明确说过的话”。
- 如果结论偏积极，必须写明最可能击穿判断的变量。
- 如果结论偏保守，必须说明什么新证据会改变结论。
""".strip()


def insert_before_heading(text: str, block: str, heading_candidates: tuple[str, ...]) -> str:
    for heading in heading_candidates:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
        if match:
            return text[: match.start()].rstrip() + "\n\n" + block + "\n\n" + text[match.start() :].lstrip()
    return text.rstrip() + "\n\n" + block + "\n"


def insert_after_section(text: str, block: str, section_candidates: tuple[str, ...]) -> str:
    for section in section_candidates:
        match = re.search(rf"(?m)^##\s+{re.escape(section)}\s*$", text)
        if not match:
            continue
        next_heading = re.search(r"(?m)^##\s+", text[match.end() :])
        if next_heading:
            insert_at = match.end() + next_heading.start()
            return text[:insert_at].rstrip() + "\n\n" + block + "\n\n" + text[insert_at:].lstrip()
        return text.rstrip() + "\n\n" + block + "\n"
    return text.rstrip() + "\n\n" + block + "\n"


def sync_skill_md(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="ignore")
    updated = original

    if "### Quick 模式" not in updated or "### Full 模式" not in updated:
        updated = insert_after_section(updated, MODE_BLOCK, ("默认设置", "用法"))
    if "## 不适用 / 降级场景" not in updated:
        updated = insert_before_heading(updated, DEGRADE_BLOCK, ("必问问题", "审判层输入协议（推荐）", "审判层输入协议"))
    if "## 反偏见条款" not in updated:
        updated = insert_before_heading(updated, ANTI_BIAS_BLOCK, ("必问问题", "审判层输入协议（推荐）", "审判层输入协议"))

    if updated == original:
        return False

    path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return True


def iter_skill_paths(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if (target / "SKILL.md").exists():
        return [target / "SKILL.md"]
    return sorted(path / "SKILL.md" for path in target.iterdir() if (path / "SKILL.md").exists())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="skill dir, SKILL.md, or parent dir containing persona skills")
    args = parser.parse_args()

    target = Path(args.target)
    paths = iter_skill_paths(target)
    changed = 0
    for path in paths:
        if sync_skill_md(path):
            changed += 1
            print(f"[updated] {path}")
    print(f"[done] changed={changed} total={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
