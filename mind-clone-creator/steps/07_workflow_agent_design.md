# Step 07: 工作型替身工作流设计

> 当用户要的不是“更像我回答”，而是“能替我推进工作”时，进入这个扩展步骤

## 目标

把“人格层分身”升级为“工作型替身”的通用方法。
顶层 bundle 可以从一开始就开启人格 + workflow 双轨，但真正编译 workflow 蓝图前，仍然要收敛到一类明确的工作单元。

这一阶段的核心不是继续补人格描述，而是把用户的真实工作拆成：

- 可识别的阶段
- 可执行的动作
- 可调用的工具
- 可自动推进的判断
- 必须人工介入的边界

## 顶层 Bundle 行为

- 人格层仍然是底座，不因为要 workflow 就跳过。
- 如果用户一开始就说“我要一个能替我工作的分身”，优先直接启动 `persona-plus-workflow` 的 working bundle。
- 如果 `target_work_unit` 还不明确，先初始化 `workflow_interview.md`，把 blocker 和下一步命令写清楚，不要把 workflow 意图静默丢弃。
- 只有在 `target_work_unit` 明确后，才继续编译 `workflow_blueprint.md`、workflow clone skill 和 workflow runtime bundle。

## 四层结构

工作型替身建议按四层建模：

### 1. 人格层

- 用户的判断标准
- 用户的边界意识
- 用户的表达风格
- 用户的协作偏好

这一层由 `mind-clone-creator` 当前主流程生成。

### 2. 工具层

- 当前环境可用的技能和工具
- 每个工具适合做什么
- 每个工具的输入输出约束

这一层需要在真实环境里检查，不靠想象补全。

### 3. 工作流层

- 任务如何分阶段推进
- 每个阶段需要什么输入
- 每个阶段产出什么输出
- 阶段间如何衔接

这是“能替你做事”的核心。

### 4. 决策层

- 当前任务处于哪个阶段
- 下一步该调用什么工具或子流程
- 什么情况下自动继续
- 什么情况下暂停并让用户介入

这是“能稳定跑”的核心。

## 通用创建流程

无论具体工作是什么，都按以下顺序设计：

### 1. 先定义工作单元

先明确“替身到底接什么类型的活”。

不要上来就说“替我工作”，要收缩成一个稳定工作单元，例如：

- 接到 AI 需求并完成第一版方案
- 接到代码仓库并输出审查结论
- 接到知识库资料并完成 RAG 接入方案
- 接到一个模糊需求并整理成可执行任务单

输出：

- `work_unit`
- `success_condition`
- `stop_condition`

### 2. 先做通用工作流访谈

这一轮不要先假设阶段名称。

不同职业的典型工作路径差异很大，不能预设成固定流水线。先用 7 个职业无关的问题，把工作从“模糊描述”变成“可建模样本”。

七个问题：

1. W1. 这类工作从什么触发？
   - 什么情况下你开始做这件事
2. W2. 完成的标准是什么？
   - 你怎么判断这件事做完了
3. W3. 中间大概经过几个阶段？
   - 不用精确，说关键节点
4. W4. 每个阶段你主要用什么工具？
   - 软件、平台、方法都算
5. W5. 哪些环节最容易卡住？
   - 你最需要反复来回的地方
6. W6. 哪些决策必须你本人来做？
   - 不能交给别人或自动化的
7. W7. 最终交给对方的是什么？
   - 文件、代码、建议、方案都算

访谈要求：

- 问题保持通用，不预设职业，不偷塞标准答案
- 用户回答只要能覆盖真实工作样本即可，不要求术语统一
- 如果用户给的是一整段描述，系统负责抽取结构，不强迫重答
- 如果用户只给碎片答案，系统可以追问一个最小补充，但不要无限展开

输出：

- `workflow_interview_answers`
- 推荐先用 `scripts/init_workflow_interview.py` 生成一份可填写的 `workflow_interview.md`

### 3. 用访谈答案生成阶段草稿

系统根据 7 个问题的答案，先生成一版“阶段草稿”，而不是直接当成最终工作流。

推导规则：

- 用 W1 锚定入口阶段
- 用 W2 和 W7 锚定末端阶段与交付完成态
- 用 W3 提取中间关键节点
- 用 W4 补每个阶段的工具与动作线索
- 用 W5 标出高摩擦阶段
- 用 W6 标出必须人工决策的阶段或节点

注意：

- 阶段数量不预设，2-8 个都可以
- 阶段名称优先贴近用户原话，不强行套 intake / clarify / execute 之类英文标签
- 如果用户描述的是循环流程，可以明确写成“阶段 A ↔ 阶段 B 反复迭代”

输出：

- `stage_draft[]`
- 推荐先用 `scripts/build_workflow_stage_confirmation.py` 生成一份 `stage_confirmation.md`，让用户确认阶段像不像

### 4. 逐阶段确认“像不像”

草稿生成后，不直接定稿，要让用户逐阶段确认。

确认重点：

- 这个阶段名像不像用户平时的说法
- 这个阶段目标是否准确
- 有没有缺的阶段
- 有没有顺序错误
- 哪些阶段其实会来回反复
- 哪些阶段必须由本人拍板

可以用这种确认方式：

1. 我理解你的流程大致是：`阶段A → 阶段B → 阶段C`
2. 其中最容易卡住的是：`阶段B`
3. 必须你本人决定的是：`阶段C`
4. 这版像不像？哪里要改？

只有用户确认后，阶段才进入正式蓝图。

输出：

- `confirmed_stages[]`

### 5. 为每个阶段绑定动作

把确认后的阶段落到实际动作，而不是抽象描述。

每个阶段必须能回答：

- 这一阶段的目标是什么
- 输入是什么
- 输出是什么
- 如何判断完成

输出：

- `stages[]`

动作要写成：

- 读取什么
- 生成什么
- 调什么工具
- 如何保存中间结果

例如：

- clarify：向用户追问直到形成可验收需求
- plan：把需求拆成周期任务与验收标准
- execute：调用 Codex / code_execution / file_handling 完成实现
- inspect：读取代码仓库并输出流程文档
- revise：对照原始需求生成修改单

输出：

- `stage_actions`

### 6. 为每个阶段绑定工具

不要只写“需要工具”，要精确到：

- 哪个工具负责什么
- 什么时候调
- 调用前需要什么条件
- 调用后如何验证结果

工具绑定模板：

- `tool_name`
- `when_to_call`
- `expected_input`
- `expected_output`
- `fallback_if_missing`

输出：

- `tool_map`

### 7. 定义阶段切换规则

如果没有阶段切换规则，Agent 只会“看起来有流程”，但不会推进。

每个阶段都要写：

- 进入条件
- 完成条件
- 失败条件
- 回退条件
- 升级给人工的条件

输出：

- `transition_rules`

### 8. 定义人工介入点

工作型替身不是“永不打扰用户”，而是“只在该打扰时打扰”。

人工介入点通常包括：

- 需求冲突
- 关键权限缺失
- 高风险修改
- 结果置信度不足
- 多方案权衡需要拍板

输出：

- `human_checkpoints`

### 9. 定义记忆与状态

如果工作会跨多轮推进，必须记录状态。

至少要定义：

- 当前任务 ID
- 当前阶段
- 已确认需求
- 已完成动作
- 未解决阻塞
- 待用户确认事项

输出：

- `workflow_state_schema`

### 10. 定义交付物

工作型替身的输出不能只是一句“我做完了”，必须是结构化交付。

交付物应至少包括：

- 最终结果
- 中间文档
- 关键决策
- 未解决问题
- 下一步建议

输出：

- `delivery_contract`

## 最小设计模板

设计任何通用工作流时，至少产出这份结构：

```yaml
workflow_name: ""
work_unit: ""
success_condition: ""
stop_condition: ""

workflow_interview_answers:
  trigger: ""
  completion_standard: ""
  stage_overview: []
  stage_tools: []
  common_blockers: []
  human_only_decisions: []
  final_deliverable: ""

stages:
  - name: ""
    goal: ""
    input: []
    output: []
    done_when: ""

tool_map:
  - tool_name: ""
    when_to_call: ""
    expected_input: ""
    expected_output: ""
    fallback_if_missing: ""

transition_rules:
  - from: ""
    to: ""
    when: ""
    fallback: ""

human_checkpoints:
  - stage: ""
    trigger: ""
    reason: ""

workflow_state_schema:
  current_stage: ""
  confirmed_requirements: []
  completed_actions: []
  blockers: []
  waiting_for_user: []

delivery_contract:
  outputs: []
  review_points: []
  unresolved_items: []
```

## 与当前 skill 的关系

`mind-clone-creator` 仍然以人格层为基础，但顶层已经支持 `persona-plus-workflow`。

当用户明确说：

- “我要能替我工作的分身”
- “我要工作型替身”
- “我要自动化执行工作流”

就不要假装当前产物已经够了，而是：

1. 先启动人格 + workflow 双轨 bundle
2. 交付人格层基础，并同步保留 `workflow_interview.md`
3. 如果第一类典型工作还没明确，先卡在 `workflow_target` blocker，而不是退出 workflow 轨道
4. 目标工作明确后，用本步骤的方法定义第一条通用工作流
5. 再把这条工作流实现成 workflow clone skill 和 runtime

## 用户可见话术

可以对用户这样说：

“你现在要的不是单纯更像你的分身，而是能替你推进工作的工作型替身。
我会把 workflow 轨道从现在就保留下来，不会等人格层做完后再把它忘掉。
如果第一类典型工作还没说清，我会先建好 `workflow_interview.md` 并把下一步卡点写明；
一旦目标明确，再用 7 个通用问题把你的典型工作建模出来，生成阶段草稿、逐阶段确认，最后输出 `workflow_blueprint.md`。” 

## 产出

最少要保留一份正在推进中的 workflow 轨道状态：

- `workflow_interview.md`
- pipeline README / bundle README 中的 blocker 与下一步命令

当 `target_work_unit` 明确并完成建模后，再产出：

- `workflow_blueprint.md`
- workflow clone skill
- workflow runtime bundle

优先使用：

- `templates/workflow_interview_template.md` 作为 W1-W7 访谈模板
- `scripts/init_workflow_interview.py` 初始化可填写的 workflow interview markdown
- `templates/workflow_stage_confirmation_template.md` 作为阶段确认模板
- `scripts/build_workflow_stage_confirmation.py` 从已填写访谈稿生成阶段确认稿
- `templates/workflow_blueprint_template.md` 作为蓝图模板
- `scripts/extract_workflow_draft.py` 从 `W1-W7` 访谈稿提取结构化 JSON 草稿；若已有 `stage_confirmation.md`，优先一并传入以覆盖原始阶段顺序
- `scripts/build_workflow_blueprint.py` 现在会把原始阶段草稿、确认后的最终阶段、回环关系和人工拍板说明一起渲染到最终蓝图
- `scripts/bootstrap_workflow_blueprint.py` 可把 `workflow_interview -> stage_confirmation -> draft -> blueprint` 串成单入口
- 如果 `workflow_interview.md` 还只是空白模板，这个单入口应先停在访谈阶段，不要把提示词误当成答案继续生成确认稿
- 这个单入口还应输出一份 pipeline README，明确当前停在哪一步、下一步该编辑哪个文件、下一条命令是什么
- 如果同时提供 `clone_config.yaml`，这个单入口还可以在 blueprint 完成后直接编译第一版 workflow clone skill
- 如果同时提供 runtime 相关参数，这个单入口还可以继续产出 workflow runtime bundle
- 如果人格层访谈产物也已经准备好，`scripts/bootstrap_working_clone_bundle.py` 可以再往上包一层，把 `personal clone -> workflow blueprint -> workflow runtime bundle` 串成总入口
- 如果人格层访谈还没开始，这个总入口现在也会先初始化 `personal_interview.md`，待填写后再继续
- `scripts/build_workflow_blueprint.py` 把结构化工作流数据渲染成 `workflow_blueprint.md`
- `scripts/build_workflow_clone_skill.py` 把人格层配置 + 工作流蓝图编译成可运行的 workflow clone skill
- `scripts/init_workflow_task_state.py` 从工作流蓝图初始化 `workflow_task_state.yaml`
- `scripts/advance_workflow_task.py` 根据当前输入推进 `workflow_task_state.yaml`
- `scripts/plan_workflow_action.py` 根据当前阶段生成结构化执行计划
- `scripts/execute_workflow_action.py` 把 action plan 转成可执行调用或人工执行项
- `scripts/run_workflow_turn.py` 一次完成 `advance -> plan -> execute`
- `scripts/run_workflow_until_stop.py` 多轮执行直到完成、需人工介入或达到轮数上限
- `scripts/bootstrap_workflow_clone_runtime.py` 高层入口：编译 workflow clone、初始化状态，并可直接启动运行
- `scripts/list_profession_adapters.py` 列出当前可用的 profession adapters
- `scripts/list_profession_adapters.py` 现在还会输出每个 adapter 的阶段覆盖、常用工具和执行偏置摘要，便于快速挑选可复用职业包
- `scripts/recommend_profession_adapter.py` 可根据职业名或一段工作描述推荐最接近的 profession adapter
- `scripts/bootstrap_workflow_clone_runtime.py` 现在会把 profession resolution 和 adapter recommendation 写进 runtime bundle；若用户未显式传 `--profession`，且推荐结果足够明确，会自动采用推荐 adapter
- `scripts/plan_workflow_action.py` 与 `scripts/execute_workflow_action.py` 现在也会输出 profession resolution 和 adapter recommendation；当未提供 profession 时，会尝试自动推荐并采用匹配 adapter
- profession adapter 的运行时匹配与推荐逻辑现已集中到 `scripts/profession_adapter_runtime.py`，供 bootstrap / planner / executor / repo profile 复用
- `scripts/validate_profession_adapters.py` 校验 profession adapter 结构是否仍符合约定
- profession adapter 不只影响阶段规划，也可以覆盖执行层偏好，例如测试命令候选顺序、仓库证据优先级，以及文档/任务系统动作对应的 Markdown artifact 模板
- `references/profession-adapter-schema.md` 作为 profession adapter 的正式字段约定
- `scripts/build_workflow_clone_skill.py` 与 `scripts/bootstrap_workflow_clone_runtime.py` 默认都会先校验 profession adapters，再开始构建；除非明确传 `--skip-adapter-validation`
- 当前内置示例 adapter 已覆盖 `AI Engineer`、`Product Manager`、`Designer`、`Lawyer`
- profession adapter 匹配现已支持规范化 alias，例如空格、连字符、下划线差异不会影响命中
- `templates/workflow_clarification_note_template.md` 作为需求澄清记录模板
- `templates/workflow_task_card_template.md` 作为任务卡片模板
- `prompts/workflow_interview_guide.md` 执行 7 问访谈与阶段确认
- `examples/ai_engineer/workflow_blueprint_input.json` 作为结构参考示例
- `examples/ai_engineer/workflow_interview_filled.md` 作为访谈输入示例

如果最终还要交付 personal clone skill 目录，优先通过 `scripts/build_personal_clone_skill.py --workflow-blueprint ...` 一并打包。
如果要把蓝图继续落成第一版工作型替身，优先通过 `scripts/build_workflow_clone_skill.py` 生成独立的 workflow clone skill 目录。
如果要让工作型替身按任务持续推进，优先再生成 `workflow_task_state.yaml` 作为任务状态载体。
如果要模拟或执行下一轮推进，优先通过 `scripts/advance_workflow_task.py` 更新状态并生成本轮执行结果。
如果要把“下一步动作”转成更细的工具计划，优先通过 `scripts/plan_workflow_action.py` 生成 action plan。
如果要实际落到调用层，优先通过 `scripts/execute_workflow_action.py` 执行安全只读动作；对于文档/任务系统，优先落成本地 Markdown artifact；其余项再转成结构化人工执行单。
如果要跑单轮完整闭环，优先通过 `scripts/run_workflow_turn.py` 一次产出更新后的状态、计划、执行结果和摘要。
如果要自动连续推进多轮，优先通过 `scripts/run_workflow_until_stop.py` 串起多个 turn。
如果要给用户一个更直接的入口，优先通过 `scripts/bootstrap_workflow_clone_runtime.py` 一次完成构建 + 初始化 + 运行。
如果要知道当前有哪些职业能力包可用，优先通过 `scripts/list_profession_adapters.py` 查看。

脚本示例：

```bash
python3 scripts/bootstrap_workflow_blueprint.py \
  --workflow-name "AI工程需求实现蓝图" \
  --work-unit "接到一个新 AI 需求后完成首版实现" \
  --known-context "用户是 AI 工程师，强调先澄清验收标准再开工" \
  --output-dir /tmp/workflow-blueprint-pipeline
```

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

```bash
python3 scripts/bootstrap_working_clone_bundle.py \
  --interview examples/ai_engineer/interview_filled.md \
  --name "AI工程师分身" \
  --profession "AI Engineer" \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --eval-report examples/ai_engineer/eval_report.md \
  --research-digest examples/ai_engineer/research_digest.md \
  --work-unit "接到一个新 AI 需求后完成首版实现" \
  --workflow-name "AI工程需求实现蓝图" \
  --workflow-interview examples/ai_engineer/workflow_interview_filled.md \
  --output-dir /tmp/working-clone-bundle \
  --execute-safe
```

```bash
python3 scripts/init_workflow_interview.py \
  --workflow-name "AI工程需求实现蓝图访谈" \
  --work-unit "接到一个新 AI 需求后完成首版实现" \
  --known-context "用户是 AI 工程师，强调先澄清验收标准再开工" \
  --output /tmp/workflow_interview.md
```

```bash
python3 scripts/build_workflow_stage_confirmation.py \
  --interview /tmp/workflow_interview.md \
  --workflow-name "AI工程需求实现蓝图" \
  --work-unit "接到一个新 AI 需求后完成首版实现" \
  --output /tmp/stage_confirmation.md
```

```bash
python3 scripts/extract_workflow_draft.py \
  --interview examples/ai_engineer/workflow_interview_filled.md \
  --stage-confirmation /tmp/stage_confirmation.md \
  --workflow-name "AI工程需求实现蓝图" \
  --work-unit "接到一个新 AI 需求后完成首版实现" \
  --output /tmp/workflow_blueprint_input.json
```

```bash
python3 scripts/build_workflow_blueprint.py \
  --input /tmp/workflow_blueprint_input.json \
  --output /tmp/workflow_blueprint.md
```

```bash
python3 scripts/build_workflow_clone_skill.py \
  --clone-config examples/ai_engineer/clone_config.yaml \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --output-dir /tmp/ai-engineer-workflow-clone
```

```bash
python3 scripts/init_workflow_task_state.py \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --task-id "task-001" \
  --task-summary "推进一个新的 AI 需求首版实现" \
  --output /tmp/workflow_task_state.yaml
```

```bash
python3 scripts/advance_workflow_task.py \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --state /tmp/workflow_task_state.yaml \
  --input "接收需求阶段已完成，问题背景和目标对象都明确了" \
  --output-state /tmp/workflow_task_state_next.yaml \
  --output-result /tmp/workflow_step_result.json
```

```bash
python3 scripts/plan_workflow_action.py \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --state /tmp/workflow_task_state_next.yaml \
  --output /tmp/workflow_action_plan.json
```

```bash
python3 scripts/execute_workflow_action.py \
  --action-plan /tmp/workflow_action_plan.json \
  --workspace . \
  --artifact-dir workflow-runtime-artifacts \
  --output /tmp/workflow_execution_result.json
```

```bash
python3 scripts/run_workflow_turn.py \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --state /tmp/workflow_task_state.yaml \
  --input "接收需求阶段已完成，问题背景和目标对象都明确了" \
  --workspace . \
  --artifact-dir workflow-runtime-artifacts \
  --execute-safe \
  --output-dir /tmp/workflow-turn-output
```

```bash
python3 scripts/run_workflow_until_stop.py \
  --workflow-blueprint /tmp/workflow_blueprint.md \
  --state /tmp/workflow_task_state.yaml \
  --initial-input "接收需求阶段已完成，问题背景和目标对象都明确了" \
  --workspace . \
  --artifact-dir workflow-runtime-artifacts \
  --execute-safe \
  --max-turns 4 \
  --output-dir /tmp/workflow-run-output
```

```bash
python3 scripts/bootstrap_workflow_clone_runtime.py \
  --clone-config examples/ai_engineer/clone_config.yaml \
  --workflow-blueprint examples/ai_engineer/workflow_blueprint.md \
  --mind-profile examples/ai_engineer/mind_profile.md \
  --system-prompt examples/ai_engineer/system_prompt.md \
  --task-id "task-001" \
  --task-summary "推进一个新的 AI 需求首版实现" \
  --initial-input "接收需求阶段已完成，问题背景和目标对象都明确了" \
  --run-until-stop \
  --execute-safe \
  --max-turns 5 \
  --workspace . \
  --artifact-dir workflow-runtime-artifacts \
  --output-dir /tmp/workflow-runtime-bundle
```

```bash
python3 scripts/list_profession_adapters.py \
  --workspace . \
  --output /tmp/profession_adapters.json
```
