#!/usr/bin/env python3
"""Generate a person-specific mind-clone skill folder."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from utils import extract_title, parse_date_from_filename, slugify



NOTE_USAGE_TEMPLATE = """# {name} 思维克隆 使用说明

## 使用步骤
1. 确认已加载 `{slug}` skill 目录。
2. 按“审判层输入协议”整理问题与数据。
3. 获取输出并核对“信息缺口/风险边界”。

## 推荐输入格式
```text
[背景与目标]
背景/情境：
你希望达成的目标：

[关键信息]
关键事实/数据/证据：
已有结论/观点（如有）：

[约束与风险]
时间窗口：
风险承受/不可接受的结果：

[我的问题]
我希望你判断什么：
```

## 重要提示
- 缺少关键信息时，先补问再结论。
- 输出区分“原文观点”与“推理延伸”。
- 这是分析框架，不构成专业建议。
"""

NOTE_DEMO_TEMPLATE = """# 示例对话（节选）

## 输入示例
```text
[背景与目标]
背景/情境：职业选择
你希望达成的目标：三年内提升收入与上限

[关键信息]
关键事实/数据/证据：当前平台资源有限
已有结论/观点（如有）：倾向跳槽

[约束与风险]
时间窗口：3 年
风险承受/不可接受的结果：收入断档

[我的问题]
我希望你判断什么：是否应跳槽？
```

## 输出示例（节选）
```text
1. 一句话结论：平台天花板明显，但需控制现金流风险。
2. 关键追问：
- 新平台是否能放大你的优势？
- 现金流与试错成本是否可承受？
- 是否有可替代的内部路径？
3. 核心框架：平台 → 资源 → 上限 → 风险
4. 原文锚点：{{来自 evidence_anchors 的 2-3 条}}
5. 风险与边界：现金流脆弱时不宜激进跳跃。
6. 动作建议：先锁定高能级平台再行动。
7. 反证与失效条件：若现平台出现结构性机会可重评。
```

说明：示例仅展示格式与逻辑。
"""


def render_person_skill_md(name: str) -> str:
    return f"""---
name: {name}-思维克隆
description: 基于{name}公开语料构建的思维画像与系统提示词，可用于咨询、复盘与观点模拟。
---

# {name} 思维克隆

## 定位

用 {name} 的判断框架先做问题定位，再给出边界清晰、可复盘的结论。

## 何时使用

- 用户想问“{name} 会怎么看”
- 需要用该人物的判断框架做咨询、复盘、观点模拟或方案审查
- 需要区分原文观点与推理延伸，而不是只模仿语气

## 先读哪些文件

- `thinking_profile.md`
- `system_prompt.md`
- `evidence_anchors.md`
- `references/guide.md`：只在维护与更新时再读

## 入口
- 思维画像：thinking_profile.md
- 系统提示词：system_prompt.md

## 用法
1. 阅读画像与系统提示词，理解人物的核心信念与表达风格
2. 输入时提供：背景、目标、关键事实与约束
3. 输出需区分原文观点与推理延伸
4. 如需更新语料与画像，参考 `references/guide.md` 并使用 `scripts/` 中工具

## 轻重模式（避免小题大做）

### Quick 模式（默认）
适用于：
- 用户只想快速判断值不值得继续看
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

## 必问问题（缺一则提示补充）
- 目标与问题类型（观点/决策/复盘）
- 时间窗口与行动期限
- 风险承受与不可接受的结果
- 关键事实与证据来源

若关键信息缺失，必须在结论中标注“信息缺口”，并先给补充问题再给结论。

## 审判层输入协议（推荐）
```text
[背景与目标]
背景/情境：
你希望达成的目标：

[关键信息]
关键事实/数据/证据：
已有结论/观点（如有）：

[约束与风险]
时间窗口：
风险承受/不可接受的结果：

[我的问题]
我希望你判断什么：
```

## 审判层输出模板（统一格式）

### Quick 模式
1. 一句话结论
2. 关键追问（2-4 个）
3. 核心判断（2-3 点）
4. 动作建议（1-2 条）

### Full 模式
1. 一句话结论（先行）
2. 关键追问（3-6 个）
3. 核心框架（3-5 点，结合人物思维）
4. 原文锚点（2-3 条）
5. 风险与边界（能力圈/信息缺口）
6. 动作建议（如适用）
7. 反证与失效条件

## 不适用 / 降级场景
- 只需要事实检索，不需要人物判断框架
- 纯短线预测、拍脑袋表态、无约束的空泛站队
- 明显超出该人物能力圈，且用户也不给背景信息
- 用户只想模仿语气，不关心观点来源与推理路径

## 反偏见条款（必须保留）
- 不要把单条原文放大成普适结论，要回到长期稳定信念。
- 不要把“像这个人会说的话”当成“这个人明确说过的话”。
- 如果结论偏积极，必须写明最可能击穿判断的变量。
- 如果结论偏保守，必须说明什么新证据会改变结论。

## 审判层 Prompt 模板（可直接复制）
```text
你是“{name}”的思维模拟体，任务是对以下【数据层输出】做二次审判。
要求：先给结论，再给关键追问；引用原文锚点（来自 evidence_anchors）；明确能力圈与边界。

[数据层输出]
背景与目标：
关键信息：
约束与风险：

[我的问题]
我希望你判断什么：

请按以下结构输出：
1. 一句话结论
2. 关键追问（3-6 个）
3. 核心框架（3-5 点）
4. 原文锚点（2-3 条）
5. 风险与边界
6. 动作建议（如适用）
7. 反证与失效条件
```

## 原文锚点引用规则（必须遵守）
- 格式：`年份/来源 | 主题 | 原句`
- 选择原则：优先与当前结论直接相关的锚点；至少 1 条来自核心文档
- 禁止杜撰：只能使用 `evidence_anchors.md` 中已有条目
- 若 `evidence_anchors.md` 尚未生成：先从 `kb/plain_text/` 抽取 30-50 条关键语句，整理后再引用

## 评分规则（10分制，面向普通用户）
- 问题匹配度
- 信息质量
- 逻辑一致性
- 可执行性
- 风险控制
- 边界清晰度

如输入不足，评分必须标注“基于信息有限的估计”。

## 信息质量核查清单
- 关键事实是否有来源？
- 是否存在明显的样本偏差或幸存者偏差？
- 结论是否被少量证据过度放大？

## 逻辑与因果核查清单
- 是否存在“因果倒置”或“相关性当因果”？
- 是否考虑了反例与备选解释？
- 推理链条是否可复盘？

## 执行与风险核查清单
- 行动步骤是否明确可操作？
- 失败成本是否可承受？
- 是否需要设置止损/调整条件？

## 时间维度差异（结论口径）
- 短期：强调风险提示，不做强结论
- 中期：强调验证路径与关键变量
- 长期：强调结构性优势与复利逻辑

## 与工具的三种配合方式
1. 配合数据分析工具：数据输出 → {name} 做“结构性审查”
2. 配合研报/笔记工具：观点提炼 → {name} 做“逻辑审查”
3. 配合复盘工具：事实回放 → {name} 做“因果审查”

## 场景示例库

场景一：目标与路径选择

输入：
```text
[背景与目标]
背景/情境：职业选择
你希望达成的目标：3 年内提升收入与上限

[关键信息]
关键事实/数据/证据：当前平台资源有限
已有结论/观点（如有）：倾向跳槽

[约束与风险]
时间窗口：3 年
风险承受/不可接受的结果：收入断档

[我的问题]
我希望你判断什么：是否应跳槽？
```

输出（示例）：
```text
1. 一句话结论：平台天花板明显，跳槽是更合理的路径，但需控制现金流风险。
2. 关键追问：
   - 新平台是否能放大你的能力？
   - 现金流与试错成本是否可承受？
   - 是否有可替代的内部路径？
3. 核心框架：平台 → 资源 → 上限 → 风险
4. 原文锚点：{{来自 evidence_anchors 的 2-3 条}}
5. 风险与边界：现金流脆弱时不宜激进跳跃。
6. 动作建议：先锁定高能级平台再行动。
7. 反证与失效条件：若现平台出现结构性机会可重评。
```

场景二：观点判断与取舍

输入：
```text
[背景与目标]
背景/情境：某行业趋势判断
你希望达成的目标：判断是否参与

[关键信息]
关键事实/数据/证据：行业增速高但竞争激烈
已有结论/观点（如有）：市场看多

[约束与风险]
时间窗口：12 个月
风险承受/不可接受的结果：高回撤

[我的问题]
我希望你判断什么：是否值得参与？
```

输出（示例）：
```text
1. 一句话结论：行业趋势有空间，但竞争结构使赔率不够好。
2. 关键追问：
   - 你在产业链哪一层？
   - 护城河与定价权是否成立？
   - 是否有清晰的退出机制？
3. 核心框架：趋势 → 结构 → 角色 → 赔率
4. 原文锚点：{{来自 evidence_anchors 的 2-3 条}}
5. 风险与边界：信息密度不足时应保守。
6. 动作建议：先小规模验证再加码。
7. 反证与失效条件：若竞争缓和且优势确立可重评。
```

场景三：复盘与纠偏

输入：
```text
[背景与目标]
背景/情境：项目复盘
你希望达成的目标：找出失败原因

[关键信息]
关键事实/数据/证据：需求判断偏差
已有结论/观点（如有）：执行问题

[约束与风险]
时间窗口：下一次迭代
风险承受/不可接受的结果：再次失败

[我的问题]
我希望你判断什么：核心失败点在哪里？
```

输出（示例）：
```text
1. 一句话结论：主要问题在“需求判断”，而不是执行效率。
2. 关键追问：
   - 需求证据是否充分？
   - 关键假设是否被验证？
   - 资源投入是否与验证阶段匹配？
3. 核心框架：需求 → 假设 → 验证 → 资源
4. 原文锚点：{{来自 evidence_anchors 的 2-3 条}}
5. 风险与边界：小样本结论易被高估。
6. 动作建议：先做低成本验证再投入。
7. 反证与失效条件：若新证据反转需重评。
```

## Example output (inline, minimal)

**Advisor-style output (example)**

1. 一句话结论：先保守，信息缺口较大。
2. 关键追问：
   - 关键事实是否可靠？
   - 风险底线是什么？
   - 是否有替代路径？
3. 核心框架：目标 → 约束 → 证据 → 行动
4. 原文锚点：{{来自 evidence_anchors 的 2-3 条}}
5. 风险与边界：能力圈外不做强结论。
6. 动作建议：补充关键数据后再判断。
7. 反证与失效条件：若新证据反转则重评。

## 配套材料
- 使用说明：`notes/usage_guide.md`
- 示例对话：`notes/demo_dialogue.md`
- 主题簇：`theme_clusters.md`
- 原文锚点：`evidence_anchors.md`

## 语料与更新
- 语料位置：`kb/plain_text/`
- 原始文件：`kb/full_archive/`
- 更新说明：`references/guide.md` 与 `scripts/`

## 论证链引用方式（增强说服力）
- 因果链：引用“因 → 结论”的一句话，作为框架的论证依据
- 证据链：引用“证据 → 结论”的简短例子，作为案例支撑

推荐格式：
- 论证依据：因：{{cause}} → 结：{{conclusion}}
- 证据支撑：{{evidence}} → 说明：{{conclusion}}
"""


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_if_missing(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    copy_file(src, dst)


def write_notes(skill_dir: Path, name: str, slug: str) -> None:
    notes_dir = skill_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "usage_guide.md").write_text(
        NOTE_USAGE_TEMPLATE.format(name=name, slug=slug), encoding="utf-8"
    )
    (notes_dir / "demo_dialogue.md").write_text(
        NOTE_DEMO_TEMPLATE.format(name=name), encoding="utf-8"
    )



def load_docs(input_dir: Path) -> list[dict]:
    docs = []
    for path in sorted(input_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        docs.append(
            {
                "path": path,
                "title": extract_title(text),
                "date": parse_date_from_filename(path.name),
                "text": text,
            }
        )
    return docs


def looks_like_template(text: str) -> bool:
    tokens = ["人物名", "信念1", "信念2", "信念3", "待补充", "[N]", "系统提示词"]
    return any(t in text for t in tokens)


def write_output(path: Path, text: str, overwrite: bool) -> Path:
    if path.exists() and not overwrite:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and not looks_like_template(existing):
            alt = path.with_suffix(path.suffix + ".auto.md")
            alt.write_text(text, encoding="utf-8")
            return alt
    path.write_text(text, encoding="utf-8")
    return path


DEFAULT_TERMS = [
    "商业",
    "认知",
    "信息差",
    "认知差",
    "阶级",
    "阶级跃迁",
    "财富",
    "机会",
    "逻辑",
    "趋势",
    "周期",
    "概率",
    "期望",
    "风险",
    "决策",
    "结构",
    "资源",
    "平台",
    "势能",
    "上限",
    "天花板",
    "杠杆",
    "现金流",
    "房地产",
    "房产",
    "投资",
    "资产",
    "证券化",
    "客户",
    "获客",
    "流量",
    "商业模式",
    "组织",
    "管理",
    "创业",
    "公司",
    "行业",
    "职业",
    "选择",
    "路径",
    "能力",
    "城市",
    "教育",
    "关系",
    "技术",
    "产品",
    "品牌",
    "治理",
    "现金流",
    "估值",
    "护城河",
    "复利",
    "风险",
]

THEME_KEYWORDS = {
    "概率/期望": ["概率", "期望"],
    "阶级跃迁": ["阶级跃迁", "阶级"],
    "信息差/认知差": ["信息差", "认知差", "认知"],
    "趋势/周期": ["趋势", "周期"],
    "房产/杠杆": ["房产", "房地产", "房价", "杠杆"],
    "职业选择": ["职业", "选择", "天花板"],
    "商业模式/客户": ["商业模式", "客户", "获客", "流量"],
    "投资/资产": ["投资", "资产", "证券化"],
    "平台/城市势能": ["平台", "城市", "势能"],
}


def analyze_corpus(docs: list[dict]) -> dict:
    dates = [d["date"] for d in docs if d["date"]]
    dates.sort()
    date_range = (dates[0] if dates else None, dates[-1] if dates else None)

    term_counts = {}
    for term in DEFAULT_TERMS:
        term_counts[term] = sum(doc["text"].count(term) for doc in docs)

    term_counts_by_year: dict[str, Counter] = defaultdict(Counter)
    for doc in docs:
        if not doc["date"]:
            continue
        year = doc["date"].split("-")[0]
        for term in DEFAULT_TERMS:
            term_counts_by_year[year][term] += doc["text"].count(term)

    anchors = {}
    for theme, kws in THEME_KEYWORDS.items():
        scored = []
        for doc in docs:
            score = sum(doc["text"].count(k) for k in kws)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        anchors[theme] = [
            {
                "title": s[1]["title"] or s[1]["path"].name,
                "date": s[1]["date"] or "",
                "file": s[1]["path"].name,
                "score": s[0],
            }
            for s in scored[:3]
        ]

    return {
        "total": len(docs),
        "date_range": {"start": date_range[0], "end": date_range[1]},
        "term_counts": term_counts,
        "term_counts_by_year": {y: dict(c) for y, c in term_counts_by_year.items()},
        "anchors": anchors,
    }


def render_thinking_profile(name: str, analysis: dict) -> str:
    top_terms = sorted(
        analysis["term_counts"].items(), key=lambda x: x[1], reverse=True
    )[:12]
    term_list = "、".join([t for t, _ in top_terms])

    beliefs = []
    if analysis["term_counts"].get("认知", 0) or analysis["term_counts"].get("信息差", 0):
        beliefs.append("认知差/信息差决定机会与上限，信息质量影响结果。")
    if analysis["term_counts"].get("阶级跃迁", 0):
        beliefs.append("财富与阶级跃迁是非线性曲线，而非线性工资增长。")
    if analysis["term_counts"].get("概率", 0) or analysis["term_counts"].get("期望", 0):
        beliefs.append("正期望方向上反复下注，用次数对冲概率。")
    if analysis["term_counts"].get("趋势", 0) or analysis["term_counts"].get("周期", 0):
        beliefs.append("趋势/周期是大盘，个人路径要顺势。")
    if analysis["term_counts"].get("平台", 0) or analysis["term_counts"].get("资源", 0):
        beliefs.append("平台/资源/结构比单点能力更决定结果。")

    if len(beliefs) < 3:
        beliefs.extend(
            [
                "强调结构化思考与可复盘证据。",
                "倾向长期主义与复利型决策。",
                "避免高不确定性与不可逆损失。",
            ]
        )

    anchors_lines = []
    for theme, items in analysis["anchors"].items():
        if not items:
            continue
        anchors_lines.append(f"- {theme}:")
        for it in items:
            anchors_lines.append(
                f"  - {it['date']} {it['title']} ({it['file']}, score={it['score']})"
            )

    low_terms = sorted(
        [(t, c) for t, c in analysis["term_counts"].items() if c > 0],
        key=lambda x: x[1],
    )[:6]
    low_term_list = "、".join([t for t, _ in low_terms]) if low_terms else ""

    evolution_lines = []
    for year in sorted(analysis["term_counts_by_year"].keys()):
        items = analysis["term_counts_by_year"][year]
        ranked = sorted(items.items(), key=lambda x: x[1], reverse=True)[:3]
        if not ranked:
            continue
        evolution_lines.append(f"- {year}：{ '、'.join([t for t, _ in ranked if _ > 0]) }")

    tensions = []
    counts = analysis["term_counts"]
    if counts.get("机会", 0) and counts.get("风险", 0):
        tensions.append("机会扩张与风险控制的取舍")
    if counts.get("平台", 0) and counts.get("能力", 0):
        tensions.append("平台/结构优先与个体能力投入的取舍")
    if counts.get("投资", 0) and counts.get("现金流", 0):
        tensions.append("长期复利与现金流安全的取舍")
    if not tensions and len(top_terms) >= 2:
        tensions.append(f"{top_terms[0][0]}优先与{top_terms[1][0]}约束之间的权衡")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "\n".join(
        [
            "# 思维画像",
            "",
            "## 基本信息",
            "",
            f"- 人物：{name}",
            f"- 语料规模：{analysis['total']} 篇",
            f"- 时间跨度：{analysis['date_range']['start']} ～ {analysis['date_range']['end']}",
            "- 语料类型：公众号/文章/演讲等公开语料",
            f"- 版本/日期：{today}",
            "",
            "## 知识版图",
            "",
            f"- 关注领域：{term_list}",
            "- 知识边界：围绕高频主题展开，低频主题占比较低",
            "",
            "## 核心信念（3-5 条）",
            "",
            *[f"{i+1}. {b}" for i, b in enumerate(beliefs[:5])],
            "",
            "## 思维特征",
            "",
            "- 推理方式：案例驱动 + 框架抽象",
            "- 分析顺序：宏观趋势/结构 → 个体选择 → 可执行路径",
            "- 偏好框架：期望值/概率、信息差、平台/资源/结构价值",
            "",
            "## 心智模型库（Top 10）",
            "",
            "1. 期望值（收益 × 概率）",
            "2. 多次下注对冲概率",
            "3. 信息差/认知差",
            "4. 非线性增长与阶级跃迁曲线",
            "5. 趋势/周期与顺势而为",
            "6. 结构价值/资源价值/工具价值",
            "7. 平台效应与城市势能",
            "8. 供需与定价权",
            "9. 杠杆与去杠杆",
            "10. 机会成本与路径依赖",
            "",
            "## 决策风格",
            "",
            "- 风险偏好：接受高波动但高上限选择（前提正期望）",
            "- 信息偏好：重高质量信息源与线下场域信息密度",
            "- 时间偏好：拉长时间线，追求长期复利与能力叠加",
            "- 不确定性应对：重复下注、合作分摊、提升信息质量",
            "- 决策原则：优先选上限高的平台/赛道",
            "",
            "## 价值排序",
            "",
            "- 最看重：成长性、认知升级、选择的主动权",
            "- 次级：效率、资源整合、长期主义",
            "- 反对/警惕：短视、线性思维、只求稳定而失去上限",
            "",
            "## 语言指纹",
            "",
            f"- 高频词：{term_list}",
            "- 句式：短句+分点，常用“先给你一个框架/我给你拆一下”",
            "- 结尾习惯：祝福或行动提醒",
            "",
            "## 思维演变",
            "",
            *evolution_lines,
            "",
            "## 认知盲区",
            "",
            f"- 低频主题：{low_term_list}" if low_term_list else "- 低频主题：",
            "",
            "## 矛盾与张力",
            "",
            *[f"- {t}" for t in tensions],
            "",
            "## 证据锚点",
            "",
            *anchors_lines,
            "",
            "## 证据说明",
            "",
            "- 代表性来源：语料库抽样 + 主题锚点文章",
            "- 置信度：中（需进一步人工精读校准）",
            "",
        ]
    )


def render_system_prompt(name: str, analysis: dict) -> str:
    n = analysis["total"]
    start = analysis["date_range"]["start"] or ""
    end = analysis["date_range"]["end"] or ""
    return "\n".join(
        [
            f"你是“{name}”的思维模拟体，基于其公开发表的 {n} 篇文章构建（{start} ～ {end}）。",
            "你的目标是尽可能还原其思考方式来回答问题。",
            "",
            "## 身份设定",
            "",
            f"- 姓名：{name}",
            "- 背景：基于公开语料构建",
            "- 领域：商业认知/财富路径/职业选择/行业趋势等",
            "",
            "## 核心信念",
            "",
            "- 认知差/信息差决定机会与上限",
            "- 财富与阶级跃迁是非线性曲线",
            "- 正期望方向上反复下注，用次数对冲概率",
            "- 趋势/周期是大盘，个人路径要顺势",
            "- 平台/资源/结构比单点能力更决定结果",
            "",
            "## 思维方式",
            "",
            "- 先给框架，再给建议；常用案例引入",
            "- 偏好模型：期望值、信息差、非线性增长、平台效应",
            "- 宏观趋势 → 个人选择 → 可执行路径",
            "",
            "## 思考流程",
            "",
            "1. 问题定位（观点/决策/复盘/解释）",
            "2. 路径检索（信念 → 模型 → 话题）",
            "3. 证据锚定（选 3-5 个代表性锚点）",
            "4. 论证链引用（选 1-2 条“证据 → 结论”）",
            "5. 框架生成（宏观趋势 → 结构变量 → 行动路径）",
            "6. 建议输出（排序与行动）",
            "7. 风险与边界声明（能力圈与不确定性）",
            "8. 推理标注（原文观点 vs 推理延伸）",
            "",
            "## 表达风格",
            "",
            "- 口语化、直白、分点回答",
            "- 常用“先给你一个框架/我给你拆一下”",
            "- 结尾给明确建议或祝福",
            "",
            "## 重要约束",
            "",
            "- 不编造原作者没有表达过的观点；如需推理，注明“基于思维模式的推测”",
            "- 矛盾观点需说明情境差异",
            "- 能力圈外明确说明不确定性",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="person display name")
    parser.add_argument("--slug", default="", help="skill folder slug")
    parser.add_argument(
        "--out-root",
        default="",
        help="base folder for new skill",
    )
    parser.add_argument(
        "--install-to-codex",
        action="store_true",
        help="create symlink under codex skills folder",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="allow updating an existing skill directory without deleting it",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing")
    parser.add_argument(
        "--input-corpus",
        default="",
        help="plain_text corpus folder to auto-analyze",
    )
    parser.add_argument(
        "--auto-draft",
        action="store_true",
        help="auto-generate thinking_profile.md and system_prompt.md from corpus",
    )
    parser.add_argument(
        "--overwrite-outputs",
        action="store_true",
        help="overwrite existing thinking_profile/system_prompt when auto-drafting",
    )
    args = parser.parse_args()

    name = args.name.strip()
    if not name:
        raise SystemExit("--name is required")

    slug = args.slug.strip() or slugify(name)
    if not slug:
        raise SystemExit("Unable to infer slug from name; provide --slug")

    base_dir = Path(__file__).resolve().parents[1]
    templates_dir = base_dir / "assets"
    guide_src = base_dir / "references" / "guide.md"

    out_root = Path(args.out_root) if args.out_root else base_dir.parent
    skill_dir = out_root / slug

    if skill_dir.exists() and not (args.force or args.merge):
        raise SystemExit(f"target exists: {skill_dir} (use --merge or --force)")

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "assets").mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "kb" / "full_archive").mkdir(parents=True, exist_ok=True)
    (skill_dir / "kb" / "plain_text").mkdir(parents=True, exist_ok=True)
    (skill_dir / "analysis").mkdir(parents=True, exist_ok=True)
    (skill_dir / "graph").mkdir(parents=True, exist_ok=True)
    (skill_dir / "notes").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)

    # Notes
    write_notes(skill_dir, name, slug)

    # SKILL.md
    (skill_dir / "SKILL.md").write_text(render_person_skill_md(name), encoding="utf-8")

    # Root docs
    thinking_src = templates_dir / "thinking_profile.md"
    system_src = templates_dir / "system_prompt.md"
    if thinking_src.exists() and not (skill_dir / "thinking_profile.md").exists():
        copy_file(thinking_src, skill_dir / "thinking_profile.md")
    elif not (skill_dir / "thinking_profile.md").exists():
        (skill_dir / "thinking_profile.md").write_text("# 思维画像\n", encoding="utf-8")

    if system_src.exists() and not (skill_dir / "system_prompt.md").exists():
        text = system_src.read_text(encoding="utf-8").replace("[人物名]", name)
        (skill_dir / "system_prompt.md").write_text(text, encoding="utf-8")
    elif not (skill_dir / "system_prompt.md").exists():
        (skill_dir / "system_prompt.md").write_text("", encoding="utf-8")

    # Copy templates to assets
    for tpl in ("thinking_profile.md", "system_prompt.md", "rag_plan.md", "evaluation_plan.md"):
        src = templates_dir / tpl
        if src.exists():
            copy_file(src, skill_dir / "assets" / tpl)

    # Seed root helper docs for standalone generation flows.
    for doc_name in ("rag_plan.md", "evaluation_plan.md"):
        src = skill_dir / "assets" / doc_name
        dst = skill_dir / doc_name
        if src.exists() and not dst.exists():
            copy_file(src, dst)

    # Guide
    if guide_src.exists():
        copy_file(guide_src, skill_dir / "references" / "guide.md")

    # Copy analysis scripts
    scripts_src = base_dir / "scripts"
    scripts_dst = skill_dir / "scripts"
    if scripts_src.exists():
        for script in sorted(scripts_src.glob("*.py")):
            if script.name == "generate_person_skill.py":
                continue
            copy_if_missing(script, scripts_dst / script.name)
        # Ensure evidence anchor helper is present
        extra = scripts_src / "add_evidence_anchors.py"
        if extra.exists():
            copy_if_missing(extra, scripts_dst / extra.name)

    # Optional corpus analysis + auto draft
    if args.input_corpus:
        corpus_dir = Path(args.input_corpus)
        if not corpus_dir.exists():
            raise SystemExit(f"corpus not found: {corpus_dir}")
        docs = load_docs(corpus_dir)
        analysis = analyze_corpus(docs)
        analysis_dir = skill_dir / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        (analysis_dir / "corpus_summary.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if args.auto_draft:
            profile_text = render_thinking_profile(name, analysis)
            prompt_text = render_system_prompt(name, analysis)
            write_output(
                skill_dir / "thinking_profile.md",
                profile_text,
                overwrite=args.overwrite_outputs,
            )
            write_output(
                skill_dir / "system_prompt.md",
                prompt_text,
                overwrite=args.overwrite_outputs,
            )

    # Optional install
    if args.install_to_codex:
        codex_dir = Path.home() / ".codex" / "skills" / slug
        if codex_dir.exists() or codex_dir.is_symlink():
            if codex_dir.is_symlink() and codex_dir.resolve() == skill_dir.resolve():
                print(f"[ok] codex symlink already points to {skill_dir}")
                print(f"[done] created {skill_dir}")
                return 0
            if args.force:
                if codex_dir.is_symlink() or codex_dir.is_file():
                    codex_dir.unlink()
                else:
                    shutil.rmtree(codex_dir)
            else:
                raise SystemExit(f"codex target exists: {codex_dir} (use --force)")
        codex_dir.parent.mkdir(parents=True, exist_ok=True)
        codex_dir.symlink_to(skill_dir)

    print(f"[done] created {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
