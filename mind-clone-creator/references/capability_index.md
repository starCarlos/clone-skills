# Capability Index

这份文档收拢 `mind-clone-creator` 当前已经具备的主要能力面，避免主 README 持续退化成脚本清单。

## 1. 人格分身访谈与 working bundle

核心入口：

- `scripts/init_personal_interview.py`
- `scripts/init_clone_interview_state.py`
- `scripts/plan_clone_interview_next.py`
- `scripts/advance_clone_interview_state.py`
- `scripts/run_clone_interview_turn.py`
- `scripts/build_next_interview_update.py`
- `scripts/build_pending_interview_actions.py`
- `scripts/refresh_working_clone_bundle.py`
- `scripts/run_working_clone_until_final.py`
- `scripts/bootstrap_working_clone_bundle.py`

当前能力：

- 生成可直接填写的 `personal_interview.md`
- 维护 `clone_interview_state.json`，按轮次记录当前题目、历史和状态
- 把题目区分为 `missing / insufficient / sufficient`
- 对不足题目输出 `follow_up_question`、`example_hint`、`must_answer_before_continue`
- 支持 `answer / confirm / revise / skip` 等 `user_action`
- 支持 section 级 override：
  `accept_for_now` 只临时放行，`accept_final` 计入最终就绪
- 输出 `NEXT_INTERVIEW_UPDATE.md/.json` 和 `PENDING_INTERVIEW_ACTIONS.json`
- 在 working bundle README/manifest 中持续写入 `recommended_next_command`、动作分组和 `Shortest Paths`
- 支持基于 `refresh_cache` 的增量刷新

常用 validator：

- `scripts/validate_clone_interview_state.py`
- `scripts/validate_working_clone_bundle.py`
- `scripts/validate_working_clone_dispatch.py`

## 2. 通用 workflow blueprint 管线

核心入口：

- `scripts/init_workflow_interview.py`
- `scripts/validate_workflow_interview.py`
- `scripts/build_workflow_stage_confirmation.py`
- `scripts/extract_workflow_draft.py`
- `scripts/build_workflow_blueprint.py`
- `scripts/bootstrap_workflow_blueprint.py`
- `scripts/refresh_workflow_blueprint_pipeline.py`

当前能力：

- 基于通用 `W1-W7` 问题生成 `workflow_interview.md`
- 生成 `stage_confirmation.md` 让用户逐阶段确认
- 当 `stage_confirmation.md` 仍为空白时，不会把蓝图退化成 `阶段1/阶段2/阶段3`
- 输出 `workflow_blueprint.md` 时保留：
  原始阶段草稿、确认后的最终阶段、回环说明、人工拍板说明
- 当访谈仍是空白模板时，会停在 `workflow_interview.md`，不会误把提示词继续编译成蓝图
- pipeline README 和 manifest 使用同一套 `recommended_next_command` 合同
- 如同时提供 `clone_config.yaml`，可直接继续编译 workflow clone skill
- 如继续提供 runtime 参数，可继续产出 workflow runtime bundle

常用 validator：

- `scripts/validate_workflow_blueprint.py`
- `scripts/workflow_blueprint_quality.py`
- `scripts/validate_workflow_pipeline_dispatch.py`

## 3. Workflow runtime 与 profession adapters

核心入口：

- `scripts/init_workflow_task_state.py`
- `scripts/advance_workflow_task.py`
- `scripts/plan_workflow_action.py`
- `scripts/execute_workflow_action.py`
- `scripts/run_workflow_turn.py`
- `scripts/run_workflow_until_stop.py`
- `scripts/bootstrap_workflow_clone_runtime.py`

当前能力：

- 初始化 `workflow_task_state.yaml` 作为跨轮状态载体
- 根据当前输入推进状态并输出本轮执行结果
- 生成结构化工具执行计划
- 把计划进一步下沉为安全只读执行或人工执行项
- 对文档/任务系统类动作优先生成本地 Markdown artifact
- 支持单轮闭环运行与多轮连续推进
- runtime README 和 manifest 共用同一套调度合同与 `Shortest Paths`

profession adapter 相关：

- `scripts/list_profession_adapters.py`
- `scripts/recommend_profession_adapter.py`
- `scripts/validate_profession_adapters.py`
- `scripts/profession_adapter_runtime.py`

当前内置示例 adapter：

- `AI Engineer`
- `Product Manager`
- `Designer`
- `Lawyer`

adapter 影响范围：

- 阶段规划
- 执行层候选命令顺序
- 仓库采集重点
- 文档/任务卡模板
- 测试命令优先级与执行证据

## 4. Skill 构建与最终发布校验

构建入口：

- `scripts/build_personal_clone_skill.py`
- `scripts/build_workflow_clone_skill.py`
- `scripts/build_clone_from_artifacts.py`

最终 validator：

- `scripts/validate_personal_clone_skill.py`
- `scripts/validate_workflow_clone_skill.py`
- `scripts/validate_personal_clone_release.py`
- `scripts/validate_workflow_clone_release.py`
- `scripts/validate_clone_stack.py`

当前能力：

- 对 personal skill / workflow skill 做结构校验
- 对 `draft / final` 发布要求做独立校验
- 对 bundle / pipeline / runtime / personal skill / workflow skill 做跨产物一致性校验
- 明确校验 `clone_config` 与 `workflow_blueprint` 是否属于同一条内容链，而不是只看单点文件存在
- manifest 中补充 `source_artifacts`，显式记录上游输入来源

## 5. Operator 与 sample stack 维护

统一入口：

<!-- BEGIN GENERATED: capability-index-operator-entry -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `scripts/clone_ops.py`
- `scripts/rebuild_sample_stack.py`
- `scripts/run_release_readiness.py`
- `scripts/stack_discovery.py`
<!-- END GENERATED: capability-index-operator-entry -->

当前能力：

<!-- BEGIN GENERATED: capability-index-operator-capabilities -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 统一触发常见 bootstrap / refresh / validate / doctor / explain / diff 动作
- `doctor latest-stack` 会自动选择 `/tmp` 下最新、通过契约校验、且属于同一条内容链的 coherent stack；如果同一内容链存在多个 `-vN` 版本，会优先挑版本更整齐的 cohort，而不是默认拼出 mixed-version 组合
- `doctor current-stack --bundle-dir <bundle-dir>` 可从 working bundle 反推整条 coherent stack
- `validate latest-stack` 可作为 `doctor latest-stack` 的对称别名使用
- `doctor` / `validate latest-stack` / `explain latest-stack` 都支持 `--summary-json`
- `rebuild_sample_stack.py` 会输出 `/tmp/*-vN` 保留报告，并支持 `--tmp-retain` / `--prune-tmp`
- `validate release-readiness` 会收束文档防漂移、单测、sample rebuild、blueprint gate、doctor/validate/explain latest-stack
<!-- END GENERATED: capability-index-operator-capabilities -->

最近增强：

<!-- BEGIN GENERATED: capability-index-recent-release-behavior -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- release-readiness 汇总 JSON 现在会为每一步输出 `compact_summary`，方便先扫 headline 和 detail 再决定是否打开日志
- latest-stack 相关步骤的摘要细节现在会优先使用单条 `stack_ref:`，不再重复拆成 `selection / stack / skills`
- 同一轮 `release-readiness` 里的 latest doctor/validate/explain 现在会复用一份 pinned latest summary，保证三步看到的是同一个 coherent stack
- latest coherent stack 现在会在“最新内容签名组”内优先选择版本更整齐的 bundle/pipeline/runtime/personal/workflow cohort，减少 `bundle vN` 搭配 `pipeline/runtime vN+1` 的混搭
- latest-stack 的 freshness 报告现在会把“为了 cohort 对齐而选旧”降级成 `notes`，只把真正落后于同签名组更优候选的情况记成 `warnings`
- `explain latest-stack` / `--format text` 里的 freshness 摘要现在会按状态聚合，例如 `aligned_to_v144=pipeline,runtime,personal,workflow`，不再只显示一个裸计数
- 原始 `clone_ops.py explain latest-stack` 文本现在也复用同一套 grouped freshness 语义，并且不会再把整份 explain 打印两次
- 原始 explain 里的 `candidate_rejections` 现在也会压成单行非零摘要；如果所有类别都是 `0`，该段会直接省略
- 原始 explain 里的 `*_rejected_candidates` 现在会按 rejection reason 分组，并只保留代表性样本名，不再展开成长 bullet 列表
- `rebuild_sample_stack` 的成功摘要也已进一步压缩，不再重复输出 bundle/signature 细节
- `doctor sample-stack` / `doctor current-stack` / `doctor latest-stack` / `validate latest-stack` 的成功摘要都已下沉 `signatures:`，把这类细节主要留给 `explain latest-stack`
- 成功的 `explain latest-stack` 摘要现在会额外输出一条 `refresh_hotspots:`，帮助维护者直接扫描最近 refresh churn 的主因
- 成功步骤默认不再写 preview，也不再保留 success logs；失败步骤或显式 `--keep-success-logs` 时才会把 stdout/stderr 落到 `release-logs/`
- 默认成功路径下如果没有失败步骤，`release-logs/` 目录也不会预先创建
- `--format text` 现在会输出更短的 operator 视图：成功步骤只显示摘要，失败步骤才展开命令和排障线索
- `validate release-readiness` 会把完整命令日志落到 `release-logs/`，同时保持 summary JSON 适合快速扫读
- Workflow clone validators reject placeholder-heavy blueprints instead of treating them as release-ready.
- 父级 refresh 现在会把匹配下层 `refresh_dependency_groups` 的变更传播到被重建的 child manifest，避免 pipeline/runtime 的 `refresh_history` 被低估
- `/tmp/*-vN` 兼容导出现在会在并发版本冲突时自动重试，避免并行 rebuild/sample release 检查互相撞号
<!-- END GENERATED: capability-index-recent-release-behavior -->

- `workflow_blueprint` 质量问题现在可以独立 fail-fast，而不必先编译成 workflow skill

## 6. 维护者优先打开这些文档

- 当前实现的完整流程地图：
  [references/current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
- Operator 命令摘要：
  [references/operator_command_summary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_summary.md)
- Operator 命令合同：
  [references/operator_command_contract.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_contract.md)
- 失败态速查：
  [references/failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md)
- 术语表：
  [references/glossary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/glossary.md)
- 示例索引：
  [references/example_index.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/example_index.md)
- 不确定先看哪份文档时先看：
  [references/doc_router.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/doc_router.md)
- 第一次接手维护先看：
  [references/new_maintainer_first_15_minutes.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/new_maintainer_first_15_minutes.md)
- 常见目标该从哪个脚本入口进：
  [references/current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
  看第 6 节“常见入口选择”
- 入口对应的最短命令示例：
  [references/current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
  看第 6 节里的“最短命令示例”
- 各层停点与续跑点：
  [references/current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
  看第 7 节“各层停点与续跑点”
- 关键文件和典型路径速查：
  [references/current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
  看第 8 节“关键文件速查”
- 运维命令与最短路径：
  [references/operator_playbook.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_playbook.md)
- 发布前人工清单：
  [RELEASE_READINESS_CHECKLIST.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/RELEASE_READINESS_CHECKLIST.md)
- 当前优化轮次：
  [OPTIMIZATION_CHECKLIST.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/OPTIMIZATION_CHECKLIST.md)
- 通用工作流访谈设计：
  [steps/07_workflow_agent_design.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/steps/07_workflow_agent_design.md)
