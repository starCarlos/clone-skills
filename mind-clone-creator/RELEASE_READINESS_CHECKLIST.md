# Release Readiness Checklist

Use this checklist before publishing, handing off, or treating `mind-clone-creator` as release-ready.

## 1. Metadata And Docs

- [ ] `SKILL.md` trigger description still describes when to use the skill, not its full workflow.
<!-- BEGIN GENERATED: release-checklist-metadata-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- [ ] `python3 scripts/validate_repo_docs.py --format json`
<!-- END GENERATED: release-checklist-metadata-commands -->
- [ ] `README.md` includes the current operator playbook for `sample-stack`, `latest-stack`, `current-stack`, and `diff stack`.
- [ ] `README.md` still exposes the 3 scenario homepage and the decision table.
- [ ] `OPTIMIZATION_CHECKLIST.md` reflects the latest completed optimization round.
- [ ] `references/failure_path_guide.md`, `references/glossary.md`, `references/example_index.md`, `references/doc_router.md`, `references/operator_command_contract.md`, `references/operator_command_summary.md`, and `references/new_maintainer_first_15_minutes.md` remain linked from the main indexes.
- [ ] Example references and output paths in docs match the current scripts and templates.
- [ ] `validate_repo_docs.py` also checks release-readiness 文档顺序，不只是检查文件存在。
- [ ] `references/operator_command_contract.md` remains the canonical operator command surface.
- [ ] `references/operator_command_summary.md` and `references/operator_command_contract.md` both match the JSON data source.

## 2. Artifact Contracts

- [ ] Personal / workflow / bundle / pipeline / runtime manifests all emit normalized `source_artifacts`.
- [ ] Bundle / pipeline / runtime outputs each emit `STACK_SUMMARY.json`.
- [ ] `working_clone_until_final_summary.json` is present in the bundle output immediately after bootstrap.
- [ ] `scripts/rebuild_sample_stack.py` exports a fresh `/tmp/*-vN` compatible stack unless `--skip-export-latest-tmp` is used.
- [ ] Generated `workflow_blueprint.md` artifacts no longer degrade to generic `阶段1/阶段2/阶段3` placeholder stage names.

## 3. Validation Commands

<!-- BEGIN GENERATED: release-checklist-validation-commands -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- [ ] `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`
- [ ] `python3 scripts/clone_ops.py validate workflow-blueprint --input /tmp/mind-clone-sample-stack-release/working-clone-bundle/workflow-blueprint-pipeline/workflow_blueprint.md --format json`
- [ ] `python3 -m unittest tests.test_stack_discovery tests.test_stack_validators tests.test_stack_operator_flow`
- [ ] `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- [ ] `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
- [ ] `python3 scripts/clone_ops.py doctor current-stack --bundle-dir /tmp/mind-clone-sample-stack/working-clone-bundle --summary-json /tmp/current-stack-summary.json`
- [ ] `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- [ ] `python3 scripts/clone_ops.py validate latest-stack --summary-json /tmp/latest-stack-validate-summary.json`
- [ ] `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json`
<!-- END GENERATED: release-checklist-validation-commands -->
- [ ] `validate release-readiness` output includes the repo-docs validation step before the operator chain.

## 4. Operator Handoff

<!-- BEGIN GENERATED: release-checklist-handoff-items -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- [ ] `doctor latest-stack --explain` shows candidate rejection counts and freshness information instead of silent failure.
- [ ] release-readiness 汇总 JSON 现在会为每一步输出 `compact_summary`，方便先扫 headline 和 detail 再决定是否打开日志
- [ ] latest-stack 相关步骤的摘要细节现在会优先使用单条 `stack_ref:`，不再重复拆成 `selection / stack / skills`
- [ ] 同一轮 `release-readiness` 里的 latest doctor/validate/explain 现在会复用一份 pinned latest summary，保证三步看到的是同一个 coherent stack
- [ ] latest coherent stack 现在会在“最新内容签名组”内优先选择版本更整齐的 bundle/pipeline/runtime/personal/workflow cohort，减少 `bundle vN` 搭配 `pipeline/runtime vN+1` 的混搭
- [ ] latest-stack 的 freshness 报告现在会把“为了 cohort 对齐而选旧”降级成 `notes`，只把真正落后于同签名组更优候选的情况记成 `warnings`
- [ ] `explain latest-stack` / `--format text` 里的 freshness 摘要现在会按状态聚合，例如 `aligned_to_v144=pipeline,runtime,personal,workflow`，不再只显示一个裸计数
- [ ] 原始 `clone_ops.py explain latest-stack` 文本现在也复用同一套 grouped freshness 语义，并且不会再把整份 explain 打印两次
- [ ] 原始 explain 里的 `candidate_rejections` 现在也会压成单行非零摘要；如果所有类别都是 `0`，该段会直接省略
- [ ] 原始 explain 里的 `*_rejected_candidates` 现在会按 rejection reason 分组，并只保留代表性样本名，不再展开成长 bullet 列表
- [ ] `rebuild_sample_stack` 的成功摘要也已进一步压缩，不再重复输出 bundle/signature 细节
- [ ] `doctor sample-stack` / `doctor current-stack` / `doctor latest-stack` / `validate latest-stack` 的成功摘要都已下沉 `signatures:`，把这类细节主要留给 `explain latest-stack`
- [ ] 成功的 `explain latest-stack` 摘要现在会额外输出一条 `refresh_hotspots:`，帮助维护者直接扫描最近 refresh churn 的主因
- [ ] 成功步骤默认不再写 preview，也不再保留 success logs；失败步骤或显式 `--keep-success-logs` 时才会把 stdout/stderr 落到 `release-logs/`
- [ ] 默认成功路径下如果没有失败步骤，`release-logs/` 目录也不会预先创建
- [ ] `--format text` 现在会输出更短的 operator 视图：成功步骤只显示摘要，失败步骤才展开命令和排障线索
- [ ] `validate release-readiness` 会把完整命令日志落到 `release-logs/`，同时保持 summary JSON 适合快速扫读
- [ ] Workflow clone validators reject placeholder-heavy blueprints instead of treating them as release-ready.
- [ ] 父级 refresh 现在会把匹配下层 `refresh_dependency_groups` 的变更传播到被重建的 child manifest，避免 pipeline/runtime 的 `refresh_history` 被低估
- [ ] `/tmp/*-vN` 兼容导出现在会在并发版本冲突时自动重试，避免并行 rebuild/sample release 检查互相撞号
- [ ] `diff stack` can compare either two summary JSON files or two bundle-root-derived summaries.
- [ ] The known-good sample output root is documented and reproducible.
- [ ] `/tmp/*-vN` export retention is visible in `rebuild_sample_stack.py` output, and pruning only happens with explicit `--prune-tmp`.
- [ ] A maintainer can rebuild, validate, explain, and diff the stack without editing script internals.
<!-- END GENERATED: release-checklist-handoff-items -->
