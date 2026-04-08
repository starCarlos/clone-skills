# Failure Path Guide

这份文档只回答一件事：流程没顺利走通时，先看什么，下一步怎么排。

## 1. 人格层常见失败点

### `personal_interview.md` 还是空白

这说明人格层还没真正开始采集。

先看：

<!-- BEGIN GENERATED: failure-guide-personal-empty-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `personal_interview.md`
- `working_clone_bundle_manifest.json`
<!-- END GENERATED: failure-guide-personal-empty-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-personal-empty-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先补访谈内容
<!-- END GENERATED: failure-guide-personal-empty-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-personal-empty-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 补完访谈后，重算 working bundle，跑：
  `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`
<!-- END GENERATED: failure-guide-personal-empty-commands -->

### `NEXT_INTERVIEW_UPDATE.md` 一直要求补同一块

这通常说明当前 section 仍是 `missing` 或 `insufficient`。

先看：

<!-- BEGIN GENERATED: failure-guide-next-interview-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `NEXT_INTERVIEW_UPDATE.md`
- `PENDING_INTERVIEW_ACTIONS.json`
- `clone_interview_state.json`
<!-- END GENERATED: failure-guide-next-interview-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-next-interview-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 优先按 `NEXT_INTERVIEW_UPDATE.md` 补当前最关键的一块
- 如果只是想先放行，确认当前流程是否允许临时 accept
<!-- END GENERATED: failure-guide-next-interview-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-next-interview-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 补完当前最关键的一块后，重算 working bundle，跑：
  `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`
<!-- END GENERATED: failure-guide-next-interview-commands -->

### `eval_report.md` 还是 `draft`

这说明人格层已能编译，但还没达到当前 release 要求。

先看：

<!-- BEGIN GENERATED: failure-guide-eval-draft-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `eval_report.md`
- `clone_config.yaml`
<!-- END GENERATED: failure-guide-eval-draft-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-eval-draft-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先读 `eval_report.md` 里的失败项或低分项
- 按失败项回到对应访谈或画像文件补料
<!-- END GENERATED: failure-guide-eval-draft-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-eval-draft-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 按失败项补料后，重算 working bundle，跑：
  `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`
<!-- END GENERATED: failure-guide-eval-draft-commands -->

## 2. Workflow 常见失败点

### `workflow_interview.md` 顶部的 `target_work_unit` 还不明确

这是最常见的 workflow blocker。

先看：

<!-- BEGIN GENERATED: failure-guide-workflow-blocker-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `workflow_interview.md`
- working bundle / pipeline README 里的 `recommended_next_command`
<!-- END GENERATED: failure-guide-workflow-blocker-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-workflow-blocker-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先把“第一类典型工作单元”写清楚
- 再补 W1-W7
- 补完后按下方对应入口重算 bundle 或 pipeline
<!-- END GENERATED: failure-guide-workflow-blocker-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-workflow-blocker-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 场景 | 命令 |
| --- | --- |
| 已有 bundle，只想重算整套 | `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json` |
| 已有 pipeline，只想重算 workflow 蓝图 | `python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json` |
<!-- END GENERATED: failure-guide-workflow-blocker-commands -->

### `stage_confirmation.md` 还没确认

这说明阶段草稿已经抽出来了，但还没变成正式蓝图。

先看：

<!-- BEGIN GENERATED: failure-guide-stage-confirmation-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `stage_confirmation.md`
- `workflow_interview.md`
<!-- END GENERATED: failure-guide-stage-confirmation-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-stage-confirmation-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 改阶段顺序、缺失阶段、回环关系、人工拍板点
<!-- END GENERATED: failure-guide-stage-confirmation-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-stage-confirmation-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 改完阶段确认稿后，重算 pipeline，跑：
  `python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`
<!-- END GENERATED: failure-guide-stage-confirmation-commands -->

### `workflow_blueprint.md` 校验失败

常见原因：

<!-- BEGIN GENERATED: failure-guide-blueprint-reasons -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 仍有 placeholder
- 还退化成 `阶段1/阶段2/阶段3`
- 阶段动作、工具映射、切换规则还是空
<!-- END GENERATED: failure-guide-blueprint-reasons -->

先看：

<!-- BEGIN GENERATED: failure-guide-blueprint-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `workflow_blueprint.md`
- `stage_confirmation.md`
- 必要时先跑一次下方 blueprint 校验命令
<!-- END GENERATED: failure-guide-blueprint-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-blueprint-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先回到 workflow 访谈或阶段确认稿补实
- 再重建 blueprint
<!-- END GENERATED: failure-guide-blueprint-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-blueprint-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 场景 | 命令 |
| --- | --- |
| 只想看 blueprint 失败细节 | `python3 scripts/clone_ops.py validate workflow-blueprint --input <workflow_blueprint.md> --format json` |
| 改完后重算 pipeline | `python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json` |
<!-- END GENERATED: failure-guide-blueprint-commands -->

### runtime 停在人工介入

这通常不是坏事，而是 workflow 明确要求停下来等人判断。

先看：

<!-- BEGIN GENERATED: failure-guide-runtime-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `workflow_task_state.yaml`
- 本轮 turn 输出目录
<!-- END GENERATED: failure-guide-runtime-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-runtime-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 读当前 stage 和 stop reason
- 补一条新的人工输入
<!-- END GENERATED: failure-guide-runtime-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-runtime-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 补完人工输入后，只推进一轮，跑：
  `python3 scripts/run_workflow_turn.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --input "继续推进下一步" --output-dir /tmp/my-workflow-runtime/turn-output --execute-safe`
- 想继续跑到下一个 stop condition，跑：
  `python3 scripts/run_workflow_until_stop.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --initial-input "继续推进直到需要人工介入" --output-dir /tmp/my-workflow-runtime/until-stop-output --execute-safe`
<!-- END GENERATED: failure-guide-runtime-commands -->

## 3. Release / Operator 常见失败点

### `validate release-readiness` 失败

先看：

<!-- BEGIN GENERATED: failure-guide-release-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- release report JSON
- 失败 step 的 `compact_summary`
- 失败 step 的 `summary_json_path`
- `release-logs/`
<!-- END GENERATED: failure-guide-release-inspect -->

下一步顺序：

<!-- BEGIN GENERATED: failure-guide-release-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. 先找第一个失败 step
2. 先读它的 `compact_summary`
3. 如果还不够，再打开 `summary_json_path`
4. 如果是命令失败，再看 `release-logs/` 里的 stdout / stderr
5. 修完后只重跑对应命令，确认绿了再重跑总检查
<!-- END GENERATED: failure-guide-release-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-release-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 目标 | 命令 |
| --- | --- |
| 先看更短的人类摘要 | `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --format text` |
| 保留汇总 JSON 方便定位失败 step | `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json` |
| 只复跑 operator 链路，不重复跑单测 | `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --summary-json /tmp/mind-clone-release-readiness.json` |
| sample stack 已存在，只复跑 doctor/validate/explain | `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --skip-rebuild --summary-json /tmp/mind-clone-release-readiness.json` |
<!-- END GENERATED: failure-guide-release-commands -->

### `doctor latest-stack` / `validate latest-stack` 结果不对

先看：

<!-- BEGIN GENERATED: failure-guide-latest-stack-inspect -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `stack_ref`
- `rejections`
- `refresh_hotspots`
- 必要时先跑一次下方 explain 命令
<!-- END GENERATED: failure-guide-latest-stack-inspect -->

下一步：

<!-- BEGIN GENERATED: failure-guide-latest-stack-next-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先确认是不是 mixed-version 或 freshness 对齐导致的选择变化
- 再看 rejection summary 是 bundle / pipeline / runtime / skill 哪一层在拦
<!-- END GENERATED: failure-guide-latest-stack-next-steps -->

可直接跑：

<!-- BEGIN GENERATED: failure-guide-latest-stack-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 目标 | 命令 |
| --- | --- |
| 解释当前 latest-stack 选择原因 | `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json` |
| 先做人类可读的 doctor 解释 | `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json` |
<!-- END GENERATED: failure-guide-latest-stack-commands -->

## 4. 常用失败命令速查

<!-- BEGIN GENERATED: failure-guide-quick-reference -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 问题 | 先看什么 | 最快命令 |
| --- | --- | --- |
| 人格层还没达到 `final`，`eval_report.md` 还是 `draft` | `eval_report.md`、`clone_config.yaml` | `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json` |
| `target_work_unit` 未定义，workflow 轨道还没起飞 | `workflow_interview.md`、`recommended_next_command` | `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json` |
| `workflow_blueprint.md` 校验失败 | `workflow_blueprint.md`、`stage_confirmation.md` | `python3 scripts/clone_ops.py validate workflow-blueprint --input <workflow_blueprint.md> --format json` |
| 发布前总检查失败 | release report JSON、`compact_summary`、`release-logs/` | `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json` |
<!-- END GENERATED: failure-guide-quick-reference -->

### 只想快速定位最近失败，不想读完全部文档

建议顺序：

<!-- BEGIN GENERATED: failure-guide-reading-order -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. 先看 [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md) 第 7 节“各层停点与续跑点”
2. 再看 [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md) 第 8 节“关键文件速查”
3. 如果是 operator 问题，再看 [operator_playbook.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_playbook.md)
<!-- END GENERATED: failure-guide-reading-order -->
