# Operator Command Summary

<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

这份文档是从 operator 命令数据源自动生成的快速摘要，适合只想先扫一眼最常用命令的人。

## 最常用的 4 条命令

- 文档防漂移：
  `python3 scripts/validate_repo_docs.py --format json`
- sample root 重建：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- latest stack 解释式校验：
  `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- 标准 release-readiness：
  `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`

## 常见 Stack 级入口

- sample stack 校验：
  `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
- current stack 校验：
  `python3 scripts/clone_ops.py doctor current-stack --bundle-dir /tmp/mind-clone-sample-stack/working-clone-bundle --summary-json /tmp/current-stack-summary.json`
- latest stack 对称校验：
  `python3 scripts/clone_ops.py validate latest-stack --summary-json /tmp/latest-stack-validate-summary.json`
- latest stack 人类解释：
  `python3 scripts/clone_ops.py explain latest-stack --summary-json /tmp/latest-stack-explain-summary.json`
- coherent stack 对比：
  `python3 scripts/clone_ops.py diff stack --left-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --right-summary /tmp/current-stack-summary.json`

## 继续看

- 完整命令合同： [operator_command_contract.md](./operator_command_contract.md)
- 维护者解释与排障： [operator_playbook.md](./operator_playbook.md)
- 第一次接手维护： [new_maintainer_first_15_minutes.md](./new_maintainer_first_15_minutes.md)
