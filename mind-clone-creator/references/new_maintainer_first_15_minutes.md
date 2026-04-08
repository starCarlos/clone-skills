# New Maintainer First 15 Minutes

这份文档只回答一个问题：第一次接手 `mind-clone-creator` 时，前 15 分钟先做什么，才能知道仓库是不是健康、主链路是不是通的。

## 0-5 分钟：先建立地图

先按这个顺序打开：

<!-- BEGIN GENERATED: new-maintainer-map-reading -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. [doc_router.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/doc_router.md)
2. [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
3. [operator_command_summary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_summary.md)
4. [operator_command_contract.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_contract.md)
5. [operator_playbook.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_playbook.md)
6. [failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md)
<!-- END GENERATED: new-maintainer-map-reading -->

你要先知道 5 件事：

<!-- BEGIN GENERATED: new-maintainer-map-goals -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 当前系统的主产物是什么
- operator 常用命令的快速摘要是什么
- operator 命令的标准写法是什么
- operator 最常跑的命令是什么
- 如果失败，日志和下一步一般看哪里
<!-- END GENERATED: new-maintainer-map-goals -->

## 5-10 分钟：先确认仓库是绿的

<!-- BEGIN GENERATED: new-maintainer-preflight -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 先跑文档防漂移校验：
  `python3 scripts/validate_repo_docs.py --format json`
- 再重建一份 sample stack：
  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
<!-- END GENERATED: new-maintainer-preflight -->

如果这两步都绿，说明你接手时的文档地图、样例产物和脚本主入口大致是一致的。

## 10-15 分钟：跑一遍 operator 主链路

按这个顺序跑：

<!-- BEGIN GENERATED: new-maintainer-operator-path -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. `python3 scripts/clone_ops.py doctor sample-stack --sample-summary /tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json --summary-json /tmp/sample-stack-doctor.json`
2. `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
3. `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`
<!-- END GENERATED: new-maintainer-operator-path -->

你应该重点确认：

<!-- BEGIN GENERATED: new-maintainer-confirm -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- `doctor sample-stack` 能过，说明 sample root 可用
- `doctor latest-stack --explain` 有稳定的 `stack_ref`、`rejections`、`freshness` 和 `refresh_hotspots`
- `validate release-readiness` 能把文档校验、sample rebuild、blueprint gate、doctor/validate/explain 收进同一份总报告
<!-- END GENERATED: new-maintainer-confirm -->

## 看见失败时怎么做

<!-- BEGIN GENERATED: new-maintainer-failure-steps -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 如果是文档问题，先回到 `validate_repo_docs.py` 的输出，看缺的是哪份文档或哪个模式
- 如果是 stack 问题，先看 `compact_summary`，再看 `summary_json_path`
- 如果是命令失败，再看 `release-logs/`
- 如果你只想快定位，不想重读整套文档，直接回 [failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md)
<!-- END GENERATED: new-maintainer-failure-steps -->

## 15 分钟后你应该已经知道

<!-- BEGIN GENERATED: new-maintainer-after-15 -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 仓库当前主链路能不能从文档、样例和 operator 视角同时走通
- 出问题时先去哪份文档、哪个 JSON、哪个日志目录
- 接下来该继续修文档、修 sample stack，还是修 operator/validator
<!-- END GENERATED: new-maintainer-after-15 -->
