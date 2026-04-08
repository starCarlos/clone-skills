# Step 06: 输出分身交付物

> 用户可见步骤：Step 5｜交付

## 输入

- `skill_config`（Step 01）
- `interview_data`（Step 02）
- `mind_profile.md`（Step 03）
- `system_prompt.md`（Step 04）
- `eval_report.md`（Step 05）
- `workflow_interview.md`（若启用 `persona-plus-workflow`，即使目标工作尚未最终确认也应存在）
- `workflow_blueprint.md`（Step 07，可选；当工作流目标已经明确并完成建模时生成）

## 处理逻辑

1. 将所有内容组装进 `templates/clone_config_v1.yaml` 模板。
2. 如果当前只有访谈、画像、System Prompt 等 Markdown 文件，优先使用 `scripts/extract_clone_draft.py` 生成结构化 JSON 草稿。
3. 如果已有结构化 JSON 草稿，优先使用 `scripts/build_clone_config.py` 生成 `clone_config.yaml` 初稿，再人工复核关键字段。
4. 生成 `clone_config.yaml` 后，优先使用 `scripts/validate_clone_config.py` 检查是否满足 `final` 放行条件。
5. 基于内置的 personal clone skill 模板 `assets/personal-clone-skill-base/` 复制并填充，生成个人分身 skill 目录。
6. 将 `clone_config.yaml`、`mind_profile.md`、`system_prompt.md`、`eval_report.md` 等文件放入该目录。
7. 如果用户选择了 `persona-plus-workflow`，但 `target_work_unit` 还未明确，保留 `workflow_interview.md`、bundle validation 和下一步命令，不要强行编译 workflow pipeline。
8. 如果用户进入了 Step 07 且 `workflow_blueprint.md` 已准备好，将其放入个人分身 skill，并继续编译 workflow clone skill / runtime bundle。
9. 使用 `scripts/render_delivery_summary.py` 生成用户可读的交付说明，尤其是 `draft` 时的差距说明。
10. 生成最终交付物。
11. 向用户说明如何使用。

优先使用 `scripts/build_personal_clone_skill.py` 自动完成第 5-6 步，而不是手工拷贝。
优先使用 `scripts/render_delivery_summary.py` 生成 `draft` 的用户说明，而不是手工总结缺口。
如果用户要的是人格 + workflow 顶层交付，优先使用 `scripts/bootstrap_working_clone_bundle.py`，而不是手工拼接个人分身目录与 workflow 目录。

## 调度原则

- 即使在前序步骤中调用过其他 skill，最终组装、放行判断和 `draft/final` 决策仍由 `mind-clone-creator` 负责。
- 若前序步骤为了补足用户工作流程而引入了外部 skill，应在最终说明中标明：用了哪个 skill、补足了哪段能力、是否已获得用户确认。
- 若缺失 skill 是在本流程中经用户确认后安装的，也应在最终说明中标明安装动作和用途。

## 使用说明（向用户展示）

“你的个人分身 skill 已生成。

你可以：
1. 直接把这个个人分身 skill 交给 OpenClaw 使用
2. 需要手动使用时，也可以把 `system_prompt.md` 的内容粘贴到支持自定义 System Prompt 的 AI 工具中

注意：
- 分身还原度约为 70%，复杂问题建议本人介入
- 建议每 3 个月根据新的经验更新一次分身 skill
- 使用过程中发现偏差，可以重新补充访谈内容”

## 输出物列表

- 个人分身 skill 目录
- working clone bundle 目录（如果启用 `persona-plus-workflow`）
- `clone_config.yaml`
- `mind_profile.md`
- `system_prompt.md`
- `eval_report.md`
- `research_digest.md`（如果执行了职业深度研究）
- `workflow_interview.md`（如果已开启 workflow 轨道）
- `workflow_blueprint.md`（如果执行了工作流建模）
- workflow clone skill 目录（如果继续编译工作型替身）
- workflow runtime bundle（如果继续编译工作型替身运行包）

## 推荐目录结构

```text
my-clone-skill/
├── SKILL.md
├── clone_config.yaml
├── mind_profile.md
├── system_prompt.md
├── eval_report.md
├── workflow_blueprint.md
└── research_digest.md
```

如果启用了人格 + workflow 双轨，推荐再保留一个总入口：

```text
working-clone-bundle/
├── personal-clone-skill/
├── workflow_interview.md
├── WORKING_CLONE_BUNDLE_README.md
├── working_clone_bundle_validation.json
└── workflow-blueprint-pipeline/   # target_work_unit 明确后再生成
```

## 个人分身 Skill 的最小要求

- `SKILL.md` 说明这是哪个人的分身 skill
- 其他文件作为该 personal clone skill 的运行上下文和人工校验材料保留在同一目录

生成个人分身 skill 时，优先复制 `assets/personal-clone-skill-base/` 作为基础骨架。
生成 `SKILL.md` 时，优先参考 `assets/personal-clone-skill-base/SKILL.md` 与 `templates/personal_clone_skill_template.md`。
如果存在工作流蓝图，优先通过 `scripts/build_personal_clone_skill.py --workflow-blueprint ...` 将其一并打包，而不是手工复制。

## 交付规则

结果分两种：

- `final`：评分 >= 60，且满足定稿条件，交付最终版文件并说明如何使用、何时更新
- `draft`：评分 < 60 或核心信息不足，仍交付草稿文件，同时明确差距、补充动作和可先使用的边界

无论 `final` 还是 `draft`，都要交付 personal clone skill 文件，不要因为分数不够而卡住用户。

同时要向用户明确说明当前交付物的定位：

- 这是“人格层分身”的可运行交付物
- 它默认负责复现用户的判断方式、表达方式、边界和协作风格
- 它默认不等于已经完成“工作流层 + 决策层”的全自动工作替身

如果用户的目标是“替我做事”，交付说明里必须补一句：

- 人格层仍是当前已交付的基础成品
- 如果 workflow 轨道已开启但 `target_work_unit` 未明确，必须同时交付 `workflow_interview.md` 和下一步动作
- 如果 `target_work_unit` 已明确，应继续交付 `workflow_blueprint.md`、workflow clone skill、workflow runtime bundle，或明确指出还卡在哪个 workflow blocker
- 不要把当前人格层产物描述成已经能端到端替代用户生产工作的 Agent

对于 `draft`，应明确给出：

- 差在哪里
- 具体该补什么
- 用户可以“现在补充”还是“先拿草稿用，之后再改”
- 当前草稿适合什么场景，不适合什么场景

对于任何交付状态，都应明确适用场景与不适用场景：

- 适合：咨询、评审、思路拆解、风格对齐、边界判断
- 不适合：未经额外工作流设计就直接承担完整执行闭环

建议直接读取 `clone_config.yaml` 中的 `release_readiness.failed_checks`，并通过 `scripts/render_delivery_summary.py` 转成用户可读说明。

## 配置增强要求

最终 `clone_config.yaml` 除了核心画像信息，还应尽量包含：

- `source_materials`：访谈、示例问答、外部研究等来源列表
- `confidence_by_dimension`：各维度置信度
- `evidence_map`：关键判断对应的证据片段或来源编号
- `last_updated_at`：最近更新时间
- `update_log`：后续迭代记录
- `source_mode`：明确标识该分身主要来自本人访谈还是“本人访谈 + 本人补充材料”
- `draft_status`：若核心本人材料不足，必须是 `draft`

## 脚本建议用法

先提取 JSON 草稿：

```bash
python3 scripts/extract_clone_draft.py \
  --interview examples/ai_engineer/interview_filled.md \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --research-digest examples/ai_engineer/research_digest.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --name "AI 工程师分身" \
  --creator "匿名" \
  --profession "AI Engineer" \
  --output /tmp/clone_config_input.json
```

再生成 YAML：

```bash
python3 scripts/build_clone_config.py \
  --input /tmp/clone_config_input.json \
  --output /tmp/clone_config.yaml
```

最后打包个人分身 skill：

```bash
python3 scripts/build_personal_clone_skill.py \
  --clone-config /tmp/clone_config.yaml \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --research-digest examples/ai_engineer/research_digest.md \
  --output-dir /tmp/ai-engineer-clone
```

如果已经完成工作流建模，可追加：

```bash
python3 scripts/build_personal_clone_skill.py \
  --clone-config /tmp/clone_config.yaml \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --output-dir /tmp/ai-engineer-clone
```

如果要一键从现有产物直接生成个人分身 skill：

```bash
python3 scripts/build_clone_from_artifacts.py \
  --interview examples/ai_engineer/interview_filled.md \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --research-digest examples/ai_engineer/research_digest.md \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --name "AI 工程师分身" \
  --creator "匿名" \
  --profession "AI Engineer" \
  --output-dir /tmp/ai-engineer-clone
```

如果用户从一开始就要人格 + workflow 双轨，可直接启动 working bundle：

```bash
python3 scripts/bootstrap_working_clone_bundle.py \
  --interview examples/ai_engineer/interview_filled.md \
  --name "AI工程师分身" \
  --profession "AI Engineer" \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --research-digest examples/ai_engineer/research_digest.md \
  --target-mode persona-plus-workflow \
  --output-dir /tmp/working-clone-bundle \
  --execute-safe
```

这条命令即使还没有 `work_unit`，也会先保留 `workflow_interview.md` 和 bundle blocker，等目标工作确认后再继续编译 workflow 管线。

## 最终放行条件

只有同时满足以下条件，才允许输出 `draft_status: final` 的配置：

- 已完成本人核心回答区块（无论是预先材料还是对话追问产生）
- 已补齐技能与知识层的最小信息，不只是思维和风格
- 关键维度存在本人来源证据映射
- 质量评分达到及格线

建议再用 `scripts/validate_clone_config.py` 做一次字段级校验，确认当前配置确实满足 `final` 标准。

否则只能输出草稿版。
