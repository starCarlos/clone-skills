
# 思维克隆私人顾问构建

## Shared Standard

Follow `SKILL-OPERATING-STANDARD.md` for hierarchy, trust boundaries, and escalation behavior.

## 何时使用

- 用户希望基于某人公开内容构建"思维克隆/数字分身/人物克隆/私人顾问/思维画像/知识库顾问"
- 需要设计多维度思维提取、画像合成、System Prompt、RAG 与评测迭代

## 角色分工

本 skill 采用"脚本 + Claude"协作模式：

- **脚本（scripts/）**：负责机械性和统计性工作——词频统计、TF-IDF、共现聚类、文件 I/O、格式转换、校验。脚本不做语义判断。
- **Claude（会话中）**：负责语义性工作——审阅脚本输出、补充人工判断、调整 domain_config、撰写 system_prompt 和 thinking_profile 的语义内容、进行质量评估与迭代。

关键原则：脚本产出的是"粗稿 / 统计结果"，Claude 在会话中对其进行"语义审阅与精修"。

## 合规与授权（先确认）

- 古代人物或已故公众人物：可基于公开文献
- 在世公众人物：必须获得明确授权
- 非公众人物：必须获得当事人明确同意
- 无法确认授权时，先询问并暂停；不要用 `--skip-compliance-gate` 当常规路径

## 输出合同（固定）

- 事实层：语料范围、来源、时间窗、授权状态
- 推导层：画像提取依据与方法
- 交付层：skill目录、prompt、配置文件清单
- 风险层：授权缺口、样本偏差、更新计划

## 快速开始

1. 合规确认与使用边界
2. 明确目标与范围（人物、语料范围、语言、用途、交付物）
3. 规范语料与元数据结构
4. 7 维思维提取与画像合成
5. 生成 System Prompt
6. 视需求设计 RAG 与对话流程
7. 测试与迭代优化
8. 生成对应人物的 skill 目录

## 统一入口（推荐）

使用 `scripts/person.py` 统一管理人物注册与创建/更新流程。你只需要让 Codex 使用本 skill，不需要手工改人物 skill。

常用命令：

- 注册人物 + 一键构建：
  `python3 scripts/person.py new --name "张三" --slug zhang-san --ingestor wechat_ingestor.py --source-config registry/sources/zhang-san.json --run full`
- 仅注册（稍后再构建）：
  `python3 scripts/person.py new --name "张三" --slug zhang-san --ingestor wechat_ingestor.py --source-config registry/sources/zhang-san.json`
- 仅更新：
  `python3 scripts/person.py run --person zhang-san --mode update`
- 查看列表：
  `python3 scripts/person.py list`
- 只看待人工确认的人物：
  `python3 scripts/person.py list --needs-review-only`
- 查看单条合规阻断原因：
  `python3 scripts/person.py show --person zhang-san --explain-compliance`
- 在不重填 source 配置的情况下更新合规字段：
  `python3 scripts/person.py patch --person zhang-san --authorization-status verified --source-legitimacy public_materials_verified --authorization-checked-at 2026-03-17`

如果你只有本地语料：

- 注册 + 构建：
  `python3 scripts/person.py new --name "张三" --slug zhang-san --input-corpus /path/to/plain_text --run full`

## 合规 review 队列

先用 audit 看全局，再用 `person.py patch` 完成单条确认：

```bash
python3 scripts/audit_person_skills.py --report /tmp/person-skills-audit-report.md
python3 scripts/person.py list --needs-review-only
python3 scripts/person.py show --person zhang-san --explain-compliance
```

`audit_person_skills.py` 现在会直接输出：

- 当前 `subject_type / authorization_status / source_legitimacy`
- 语料入口（`ingestor` / `source_config` / `input_corpus`）
- 一条可复制的 `person.py patch` review command

只有当 audit 显示该人物 `Ready For Strict Gate: yes` 时，才应进入默认 build / rebuild / dispatch 流程。

如果要批量 review，不要 16 条命令手工敲一遍，直接走 CSV：

```bash
python3 scripts/person.py review-export \
  --out /tmp/person-review-queue.csv \
  --needs-review-only \
  --prefill-suggested

# 在表格里编辑 review_* 列，并把 apply 改成 1

python3 scripts/person.py review-apply \
  --in /tmp/person-review-queue.csv \
  --dry-run

python3 scripts/person.py review-apply \
  --in /tmp/person-review-queue.csv
```

规则：

- 只会处理 `apply=1/true/yes` 的行
- 实际回写的是 `review_*` 列，不是 `current_*` 列
- 建议先跑一次 `--dry-run`，确认输出里目标人物已变成 `compliance=ready`
- `triage_bucket / triage_priority / can_review_now / triage_note` 是系统给出的处理顺序建议
- 一般先处理 `source_review_only`，再决定是否继续追 `authorization_blocked`
- runtime gate 与 audit 默认以 `registry/persons.json` 为合规 source of truth；`review-apply` 会把结果同步回 `meta/build_summary.json`
- `authorization_checked_at` 现在是 readiness 硬条件；即使授权状态和来源合法性都对，没填日期也不会过 gate
- `--prefill-suggested` 只会预填 `can_review_now=1` 的行，避免把授权阻塞人物自动改成 `verified`

## 先确认这些问题

- 目标人物与授权/合规边界
- 语料来源与数量（文章/演讲/播客/评论等）
- 语言与时间跨度
- 交付物类型：画像报告 / System Prompt / 完整 RAG 方案 / 平台配置
- 是否需要“持续更新机制”
- 技术栈偏好（向量库、Embedding、框架）

## 交付形态：人物 skill（必须产出）

当用户要求“做某人的思维克隆”，必须创建一个对应人物的 skill 目录。最小结构：

```
person-skill/
├── SKILL.md
├── thinking_profile.md
└── system_prompt.md
```

增强结构参见 `references/case_template.md`。

约束（重要）

- 人物 skill 必须独立可用
- 人物相关的语料、抽取、图谱、论证链、更新脚本都放在该人物 skill 中
- 总思维克隆只提供方法论与工具，不保存人物数据

## 工作流

### 1) 数据采集与整理

- 收集公开语料，保留标题、正文、时间、来源
- 去重、去广告、统一格式
- 按时间排序并打基础标签
- 数据采集优先使用 `content-harvester` skill
- 元数据格式、清洗规则与标签模板见 `references/guide.md`

### 1.2) plain_text 格式规范

`kb/plain_text/` 中的文件应满足以下标准：

- 格式：`.md` 纯文本（无 YAML front matter、无 HTML 标签）
- 文件名：`YYYY-MM-DD__标题slug.md`（日期前缀用于时间排序）
- 内容：仅保留正文文本，已去除登录框/广告/分享按钮等网页噪音
- 最小长度：有效正文 >= 100 字符（过短文件在分析中被跳过）
- 可使用 `scripts/extract_plain_text.py` 从 `full_archive` 自动转换：

```bash
python3 scripts/extract_plain_text.py \
  --input-dir /path/to/kb/full_archive \
  --output-dir /path/to/kb/plain_text \
  --config /path/to/analysis/domain_config.json
```

### 1.5) 质量门控（推荐）

- 清理明显无效文本（404/订阅墙/登录页/空白页/无关访谈）
- 清理后再进入抽取与图谱流程，避免污染分析
- 推荐用低质扫描脚本做初筛：

```bash
python3 scripts/scan_low_quality.py \
  --plain-text-dir /path/to/kb/plain_text \
  --min-chars 400
```

若使用 `rebuild_from_kb.py`，可加 `--scan-quality` 仅提示低质语料并继续：

```bash
python3 scripts/rebuild_from_kb.py \
  --skill-dir /path/to/skill \
  --scan-quality \
  --scan-min-chars 400
```

### 1.6) 领域配置（domain_config.json）

- 运行 `discover_domain.py` 生成领域配置，作为后续抽取与图谱的词表与主题种子
- 可人工微调：`top_terms / belief_buckets / theme_seeds / cleanup_patterns / generic_terms`

```bash
python3 scripts/discover_domain.py \
  --input /path/to/kb/plain_text \
  --person "人物名" \
  --out /path/to/analysis/domain_config.json
```

### 2) 分类打标

- 至少包含：主题领域、内容类型、可靠度、时间阶段
- 可靠度要区分原文/同代记录/后人转述/演义虚构
- `build_labels.py` 是**人工审阅辅助工具**：它基于规则自动生成初始标签，但产出仅为"建议标签"，需 Claude 或人工在会话中审阅确认

```bash
python3 scripts/build_labels.py \
  --plain-text-dir /path/to/kb/plain_text \
  --config /path/to/analysis/domain_config.json \
  --out /path/to/analysis/labels.jsonl
```

### 3) 多维思维提取（强制 7 维）

- 核心观点与立场
- 思维模式与推理方式
- 心智模型与分析框架
- 价值观与信念体系
- 决策模式
- 语言风格与表达习惯
- 认知盲区与局限

强制要求

- 所有维度必须提取，不允许缺项
- 原文缺失信息必须在“抽取结果”中标注
- 人物 skill 交付物中不得出现“未覆盖/无法判断/待补充”等提示

当前实现（规则提取）

- 通过 `llm_extract.py` 使用基于规则的关键词匹配从语料中提取 7 维信号
- 使用 `domain_config.json` 中的词表和模式进行匹配
- 不依赖外部 LLM API

### 4) 思维画像合成与交叉验证

- 汇总所有提取结果，生成结构化“思维画像”
- 标注高频/中频/偶发特征与置信度
- 记录矛盾点与思维演变

### 5) 生成 System Prompt

- 覆盖身份设定、核心信念、思维方式、决策风格、价值排序、表达风格、约束规则
- 古代人物需加“时空桥接规则”
- System Prompt 长度建议 2000-4000 字

### 6) 构建 RAG（可选）

- 语义分块 300-500 字/块
- 注入元数据并检索 Top 5-10
- 统一“原文优先、推理需标注”

### 7) 图谱与论证链（推荐）

- 生成思维图谱、关系图谱、概念层级图谱
- 抽取论证链用于“结论-证据”引用

### 8) 测试与迭代

- A 类：有据可查题
- B 类：推理延伸题
- C 类：边界测试题
- 评估维度与权重见 `references/guide.md`
- 建议输出 `evaluation_plan.md` 与 `evaluation_report.md` 作为可复用测试集与结果记录
- `evaluation_report.md` 的定位是 artifact coverage / supporting-artifact 评分，不是 live response quality

```bash
# Automated validation
python3 scripts/validate_person_skill.py --skill-dir /path/to/skill

# Automated evaluation (requires evaluation_plan.md)
python3 scripts/evaluate_person_skill.py --skill-dir /path/to/skill
```

## 输出物清单（按需）

- `thinking_profile.md`（思维画像）
- `system_prompt.md`
- `rag_plan.md`（分块、索引、检索策略）
- `evaluation_plan.md`
- `evaluation_report.md`（artifact coverage 报告）
- `meta/build_summary.json`（构建摘要、语料规模、合规状态）
- `analysis/extractions.jsonl`（逐篇抽取结果）
- `analysis/labels.jsonl`（分类打标结果）
- `analysis/domain_config.json`（领域配置）
- `graph/thought_graph.json`（思维图谱数据）
- `graph/thought_graph.mmd`（Mermaid 图谱）
- `graph/graph_report.md`（图谱摘要）
- `graph/relation_graph.json`（关系类型图谱）
- `graph/relation_graph.mmd`（关系图谱 Mermaid）
- `graph/relation_report.md`（关系图谱摘要）
- `graph/thought_hierarchy.json`（概念层级图谱）
- `graph/thought_hierarchy.md`（概念层级说明）
- `graph/argument_chains.jsonl`（论证链：因→结/证据→结论）
- `graph/argument_chains.md`（论证链摘要）
- `graph/node_weights.json`（节点权重：信念/模型/话题）
- `graph/sample_path_*.json`（示例路径：问题→信念→模型→话题）
- `analysis/corpus_summary.json`（语料摘要 JSON）
- `analysis/corpus_summary.md`（语料摘要 Markdown）
- `kb/manifest.jsonl`（语料清单）
- `theme_clusters.md`
- `notes/`（手工备注/校验记录）

## 思考流程（强制）

任何“思维克隆”回答必须按以下思考顺序执行，并在输出中体现结构：

1. 问题定位：判断问题类型（观点咨询/决策建议/知识解释/案例复盘）
2. 路径检索：用图谱或人工方式映射到“信念→模型→话题”
3. 证据锚定：从 `extractions.jsonl` / 代表文章中选 3-5 个锚点
4. 论证链引用：选 1-2 条“证据→结论”作为说服力核心
5. 框架生成：用“宏观趋势→结构变量→行动路径”的顺序搭框架
6. 答案生成：分点输出建议与排序
7. 边界声明：明确能力圈、信息缺口与风险
8. 推理标注：区分原文观点 vs 推理延伸
9. 一致性检查：检查是否违背核心信念/语言风格

输出结构建议

1. 问题复述
2. 框架（3-5 点）
3. 建议与排序
4. 风险与边界
5. 祝福/行动提醒（保持人物风格）

## 原文锚点引用方式（统一标准）

- 在 `analysis/extractions.jsonl` 的 `evidence_anchors` 中选择 2-3 条原文片段
- 引用格式：原文锚点：{text}
- 原文锚点用于支撑结论，结论需回到人物核心框架

## 图谱抽取（可选）

当需要“更深入的结构化视图”时，生成思维图谱：

```bash
python3 scripts/build_thought_graph.py \
  --input /path/to/analysis/extractions.jsonl \
  --out-dir /path/to/graph \
  --min-edge 4
```

## 关系图谱与层级图谱（可选）

关系图谱（带“因果/对比/类比/建议”等类型）：

```bash
python3 scripts/build_relation_graph.py \
  --extractions /path/to/analysis/extractions.jsonl \
  --plain-text-dir /path/to/plain_text \
  --out-dir /path/to/graph \
  --min-edge 3
```

概念层级图谱（信念 → 模型 → 话题）：

```bash
python3 scripts/build_thought_hierarchy.py \
  --input /path/to/analysis/extractions.jsonl \
  --out-dir /path/to/graph
```

## 论证链抽取（可选）

抽取“观点→结论 / 证据→结论”的论证链：

```bash
python3 scripts/build_argument_chains.py \
  --plain-text-dir /path/to/plain_text \
  --out-dir /path/to/graph
```

## 节点权重与路径检索（可选）

节点权重：

```bash
python3 scripts/compute_node_weights.py \
  --input /path/to/analysis/extractions.jsonl \
  --out /path/to/graph/node_weights.json
```

路径检索（给定问题返回“信念→模型→话题”）：

```bash
python3 scripts/trace_reasoning_path.py \
  --input /path/to/analysis/extractions.jsonl \
  --query "你的问题文本" \
  --out /path/to/graph/sample_path.json
```

## 一键完整生成（推荐）

从语料到可用 skill 全流程一键产出（含画像、系统提示词、抽取结果、图谱、论证链、主题聚类）：

```bash
python3 scripts/build_full_person_skill.py \
  --name "人物名" \
  --slug person-slug \
  --input-corpus /path/to/plain_text \
  --out-root /path/to/skills
```

说明：

- 会将语料复制到 `kb/plain_text`，保证人物 skill 自包含
- 自动生成 `analysis/domain_config.json` 与 `analysis/extractions.jsonl`
- 自动生成 `thinking_profile.md` 与 `system_prompt.md`
- 自动生成 `graph/` 与 `theme_clusters.md`
- 自动生成 `analysis/corpus_summary.json` / `analysis/corpus_summary.md`
- 自动生成 `kb/manifest.jsonl`

## 抓取与更新（可插拔模板）

通用约定：

- 任何抓取脚本遵循统一 CLI：`--plain-text-dir`、`--full-archive-dir`、`--manifest`、`--source-config`、`--incremental`、`--since`
- 抓取脚本只负责“获取 + 规范化 + 写入语料”，更新画像与图谱由统一流水线处理

内置示例抓取器：

| 抓取器 | 适用场景 | 关键字段 | 可选依赖 |
|--------|---------|---------|---------|
| `wechat_mp.py` | 微信公号文章（URL 列表） | `sources: [{id, url, date, title, tags}]` | requests, bs4 |
| `url_list.py` | 通用 URL 列表（html/pdf/wp_json/sina） | `sources: [{id, url, date, title, format, tags}]` | bs4, pypdf |
| `berkshire_letters.py` | 伯克希尔股东信 + Owner's Manual | 无需配置（内置 URL） | requests, bs4, pypdf |
| `substack.py` | Substack 博客自动分页 | `blog, author, limit, default_tags` | bs4（可选） |
| `rss_feed.py` | RSS/Atom 订阅源（支持过滤） | `feeds: [{url, type, author_filter, title_filter, author, default_tags}], fetch_full_content, fallback_feeds` | bs4（可选） |
| `platform.py` | 多平台（微博/B站/知乎/掘金/CSDN/头条/小红书/Twitter/Facebook/通用HTML） | `sources: [{id, url, tags}], browser_mode, sleep` | requests, bs4, cloudscraper（可选）, playwright（可选） |

**使用示例：**

Substack 博客抓取：
```bash
# 配置文件示例：registry/sources/examples/substack-example.json
python3 scripts/ingestors/substack.py \
  --plain-text-dir /path/to/kb/plain_text \
  --full-archive-dir /path/to/kb/full_archive \
  --manifest /path/to/kb/manifest.jsonl \
  --source-config registry/sources/examples/substack-example.json \
  --incremental --dry-run
```

RSS/Atom 订阅源抓取：
```bash
# 配置文件示例：registry/sources/examples/rss-feed-example.json
python3 scripts/ingestors/rss_feed.py \
  --plain-text-dir /path/to/kb/plain_text \
  --full-archive-dir /path/to/kb/full_archive \
  --manifest /path/to/kb/manifest.jsonl \
  --source-config registry/sources/examples/rss-feed-example.json \
  --since 2024-01-01
```

多平台内容抓取：
```bash
# 配置文件示例：registry/sources/examples/platform-example.json
python3 scripts/ingestors/platform.py \
  --plain-text-dir /path/to/kb/plain_text \
  --full-archive-dir /path/to/kb/full_archive \
  --manifest /path/to/kb/manifest.jsonl \
  --source-config registry/sources/examples/platform-example.json \
  --incremental
```

模板脚本（复制后实现）：

```bash
python3 scripts/ingest_template.py --dry-run \
  --plain-text-dir /path/to/kb/plain_text \
  --full-archive-dir /path/to/kb/full_archive \
  --manifest /path/to/kb/manifest.jsonl \
  --source-config /path/to/source_config.json
```

运行任意抓取器：

```bash
python3 scripts/run_ingest.py \
  --ingestor /path/to/ingest_xxx.py \
  --skill-dir /path/to/skill \
  --source-config /path/to/source_config.json \
  --incremental --since 2026-01-01
```

也可在“一键完整生成”中直接调用抓取器：

```bash
python3 scripts/build_full_person_skill.py \
  --name "人物名" \
  --slug person-slug \
  --ingestor scripts/ingestors/wechat_mp.py \
  --source-config /path/to/source_config.json \
  --out-root /path/to/skills
```

抓取后更新画像与图谱：

```bash
python3 scripts/rebuild_from_kb.py \
  --skill-dir /path/to/skill \
  --overwrite-outputs
```

注意：

- `build_full_person_skill.py`、`rebuild_from_kb.py`、`dispatch_persons.py` 默认都会执行 strict compliance gate
- 仅在迁移、排障或明确受控场景下才使用 `--skip-compliance-gate`

## 总思维克隆“下发”到各人物（总控分发）

配置人物注册表：

- `registry/persons.json`
- 示例：`registry/persons.example.json`

批量分发（创建/更新）：

```bash
python3 scripts/dispatch_persons.py --mode full
```

仅更新某一个人物：

```bash
python3 scripts/dispatch_persons.py --mode update --person uncle-wan
```

如果 registry 中仍有 `needs_review` 条目，批量分发会跳过这些人物并返回非零退出码；先修 registry，再重跑。

## 自动生成脚本（可选）

用于快速生成“对应人物 skill 目录”的入口脚本：

```bash
python3 scripts/generate_person_skill.py \
  --name "人物名" \
  --slug person-slug \
  --out-root /path/to/skills \
  --input-corpus /path/to/plain_text \
  --auto-draft
```

说明：

- `--auto-draft` 只生成“粗稿”，不替代 LLM 抽取与合成
- 如需安装到技能目录，按环境默认方式处理

## 更新人物 skill（新增文章）

当有新文章/语料进入后，按以下流程更新指定人物的 skill：

1. 用 `content-harvester` 更新语料（保持 `kb/plain_text` 为最新）
2. 对新增语料做 7 维抽取，合并到 `analysis/extractions.jsonl`
3. 重新合成 `thinking_profile.md` 与 `system_prompt.md`
4. 生成/更新 `evidence_anchors`（原文锚点）
5. 视需求重新生成图谱与论证链

如需脚本化更新，可使用：

```bash
python3 scripts/generate_person_skill.py \
  --name "人物名" \
  --slug person-slug \
  --out-root /path/to/skills \
  --input-corpus /path/to/plain_text \
  --auto-draft \
  --merge \
  --overwrite-outputs

# 原文锚点（可选，推荐）
python3 scripts/add_evidence_anchors.py \
  --plain-text-dir /path/to/plain_text \
  --input /path/to/analysis/extractions.jsonl \
  --output /path/to/analysis/extractions.jsonl \
  --config /path/to/analysis/domain_config.json

# 语料摘要（可选）
python3 scripts/build_corpus_summary.py \
  --input /path/to/analysis/extractions.jsonl \
  --out-json /path/to/analysis/corpus_summary.json \
  --out-md /path/to/analysis/corpus_summary.md

# 语料清单（可选）
python3 scripts/build_kb_manifest.py \
  --plain-text-dir /path/to/plain_text \
  --out /path/to/kb/manifest.jsonl
```

## 技能生成规则（强制）

- 任何“思维克隆”项目必须落地为一个人物 skill 目录
- 该目录必须包含 `thinking_profile.md` 与 `system_prompt.md`
- 若存在语料/分析步骤，保留 `references/guide.md` 与分析脚本/报告
- 若用户要求“可用的分析 skill”，需补齐可执行入口（脚本或明确步骤）

## Roadmap（未来能力规划）

以下功能尚未实现，列为未来迭代方向：

- **RAG 向量检索**：基于向量数据库的语义检索，替代当前关键词匹配，提升召回与相关性
- **LLM 深度提取**：通过外部 LLM API 实现真正的语义级抽取，替代当前基于规则的 `llm_extract.py`
- **9 步思考流程编排**：将"思考流程（强制）"中的 9 步自动化为可执行的推理管线，支持图谱检索与论证链自动引用

## 安全与边界

- 不编造原作者未表达过的观点
- 推理与原文观点需区分标注
- 原文缺失领域应明确说明能力边界
- 不用于冒充/欺骗
- 在高风险领域的建议需明确风险与不确定性

## 参考

- `references/guide.md`：完整操作指南与 Prompt 模板
- `references/acceptance.md`：人物 skill 验收清单
- `references/case_template.md`：人物 skill 结构模板
