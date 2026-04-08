# Operator Playbook

这份文档收拢 `mind-clone-creator` 的运维侧命令，避免主 README 持续膨胀。

精确命令语法的单一真源在：

- [operator_command_contract.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_contract.md)

如果你只想先扫一页生成版摘要：

- [operator_command_summary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_summary.md)

这份 playbook 更侧重什么时候用、为什么用、成功路径和失败路径怎么看。

## 日常最短路径

<!-- BEGIN GENERATED: operator-playbook-daily-path -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 重建一份可移植 sample stack，并同步导出新的 `/tmp/*-vN` latest-stack 兼容目录：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- 校验当前 sample stack：
  `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
- 校验指定 bundle 所属的 coherent stack：
  `python3 scripts/clone_ops.py doctor current-stack --bundle-dir /tmp/mind-clone-sample-stack/working-clone-bundle --summary-json /tmp/current-stack-summary.json`
- 解释并校验 `/tmp` 下最新 coherent stack：
  `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- 只做 latest-stack 校验：
  `python3 scripts/clone_ops.py validate latest-stack --summary-json /tmp/latest-stack-validate-summary.json`
- 只输出 latest-stack 的人类可读解释：
  `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json`
- 对比两份 coherent stack 摘要：
  `python3 scripts/clone_ops.py diff stack --left-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --right-summary /tmp/current-stack-summary.json`
<!-- END GENERATED: operator-playbook-daily-path -->

## Release Readiness

<!-- BEGIN GENERATED: operator-playbook-release-core -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 单独做文档防漂移校验：
  `python3 scripts/validate_repo_docs.py --format json`
- 一次性执行当前所有可自动化的 release-readiness 检查：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`
- 如果你想看更适合人工扫读的终端摘要，可以直接用：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --format text`
<!-- END GENERATED: operator-playbook-release-core -->

- 上面这条 `release-readiness` 现在已经内置文档防漂移校验，不再只覆盖单测和 stack/operator 链路
<!-- BEGIN GENERATED: operator-playbook-release-behavior -->
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
<!-- END GENERATED: operator-playbook-release-behavior -->
<!-- BEGIN GENERATED: operator-playbook-release-variants -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 如果你明确想保留成功日志，再显式加：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --keep-success-logs --summary-json /tmp/mind-clone-release-readiness.json`
- 如果只想复跑 operator 检查而不重复跑单测：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --summary-json /tmp/mind-clone-release-readiness.json`
- 如果 sample stack 已存在，只想复跑 doctor/validate/explain：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --skip-rebuild --summary-json /tmp/mind-clone-release-readiness.json`
- 单独校验某个 workflow blueprint 是否还是占位骨架：
  `python3 scripts/clone_ops.py validate workflow-blueprint --input /tmp/mind-clone-sample-stack-release/working-clone-bundle/workflow-blueprint-pipeline/workflow_blueprint.md --format json`
<!-- END GENERATED: operator-playbook-release-variants -->

- 汇总 JSON 不再承担完整命令输出；失败步骤或显式保留时的 stdout/stderr 会落到：
  `/tmp/mind-clone-sample-stack-release/release-logs/`

## 新维护者入口

- 如果你是第一次接手维护，先按：
  [new_maintainer_first_15_minutes.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/new_maintainer_first_15_minutes.md)
- 这份文档会把前 15 分钟该打开什么、该跑哪几条命令、失败后先看哪份报告压成一条最短路径

## /tmp 保留策略

- `scripts/rebuild_sample_stack.py` 默认会在输出 JSON 里报告 `/tmp/*-vN` 的保留情况，默认保留策略是每类 artifact 关注最新 `5` 个版本：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack --tmp-retain 5`
- 如果维护者确认旧版本可以清理，再显式开启裁剪：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack --tmp-retain 5 --prune-tmp`
- 如果你只想重建可移植 sample root，不想刷新 `/tmp/*-vN` 兼容目录：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack --skip-export-latest-tmp`

## Refresh 入口

<!-- BEGIN GENERATED: operator-playbook-refresh-entry -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 刷新整套 working bundle：
  `python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`
- 刷新 workflow pipeline：
  `python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`
- 刷新 workflow runtime bundle：
  `python3 scripts/refresh_workflow_runtime_bundle.py --manifest /tmp/my-workflow-runtime/workflow_runtime_manifest.json`
<!-- END GENERATED: operator-playbook-refresh-entry -->
- 父级 refresh 现在会把命中的 `workflow_shared` 变更同步写进被重建的下层 manifest：
  `refresh_working_clone_bundle.py` 会向 pipeline/runtime 追加传播后的 trigger，`refresh_workflow_blueprint_pipeline.py` 会向 runtime 追加传播后的 trigger
- 因此 `doctor current-stack --explain` / `explain latest-stack` 里的 pipeline/runtime `refresh_history` 和 `refresh_stats` 不再只反映“手动直刷”记录，也会包含父级刷新带来的真实重建原因
