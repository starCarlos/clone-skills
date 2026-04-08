# Operator Command Contract

<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

这份文档是 operator 命令的单一真源。

如果 README、维护者入口、排障文档里只保留了命令名或缩写说明，以这里的命令行为准。以后命令语法改动，优先先改这份合同，再改其他引用文档。

## Canonical Commands

- 文档防漂移：
  `python3 scripts/validate_repo_docs.py --format json`
- sample root 重建：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- sample stack 校验：
  `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
- current stack 校验：
  `python3 scripts/clone_ops.py doctor current-stack --bundle-dir /tmp/mind-clone-sample-stack/working-clone-bundle --summary-json /tmp/current-stack-summary.json`
- latest stack 解释式校验：
  `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- latest stack 对称校验：
  `python3 scripts/clone_ops.py validate latest-stack --summary-json /tmp/latest-stack-validate-summary.json`
- latest stack 人类解释：
  `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json`
- coherent stack 对比：
  `python3 scripts/clone_ops.py diff stack --left-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --right-summary /tmp/current-stack-summary.json`
- 标准 release-readiness：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`

## Daily Stack Commands

最常用的日常顺序：

1. `python3 scripts/validate_repo_docs.py --format json`
2. `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
3. `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
4. `python3 scripts/clone_ops.py doctor current-stack --bundle-dir /tmp/mind-clone-sample-stack/working-clone-bundle --summary-json /tmp/current-stack-summary.json`
5. `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
6. `python3 scripts/clone_ops.py validate latest-stack --summary-json /tmp/latest-stack-validate-summary.json`
7. `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json`

## Release Commands

- 标准 release-readiness：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`
- release-readiness 文本人类摘要：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --format text`
- 只复跑 operator，不跑单测：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --summary-json /tmp/mind-clone-release-readiness.json`
- sample stack 已存在，只复跑 doctor/validate/explain：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --skip-tests --skip-rebuild --summary-json /tmp/mind-clone-release-readiness.json`
- 显式保留成功日志：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --keep-success-logs --summary-json /tmp/mind-clone-release-readiness.json`

## 使用原则

- 想知道“为什么用这条命令、失败后看哪里”，看 [operator_playbook.md](./operator_playbook.md)
- 想知道“第一次接手维护先跑什么”，看 [new_maintainer_first_15_minutes.md](./new_maintainer_first_15_minutes.md)
- 想知道“某个失败态下一步怎么排”，看 [failure_path_guide.md](./failure_path_guide.md)
