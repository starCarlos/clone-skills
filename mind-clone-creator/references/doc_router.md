# Doc Router

这份文档只做一件事：当你不知道该先看哪份文档时，帮你在 30 秒内选到第一份该打开的文件。

## 按问题找文档

<!-- BEGIN GENERATED: doc-router-question-table -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

| 你现在的问题 | 先看哪份文档 | 为什么 |
| --- | --- | --- |
| 这套系统现在到底做到了哪一步？ | [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md) | 这是当前实现地图，不是设计稿 |
| 我不知道该从哪个脚本入口开始 | [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md) | 第 6 节有入口选择和最短命令 |
| 我卡住了，只想知道下一步怎么跑 | [failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md) | 这里按失败点给了最快排障路径和命令 |
| 我看不懂 bundle / pipeline / runtime 是什么 | [glossary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/glossary.md) | 先对齐术语，再看流程 |
| 我想看一份完整示例到底长什么样 | [example_index.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/example_index.md) | 这里告诉你先读哪些 example 文件 |
| 我是维护者，只关心 operator 命令 | [operator_playbook.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_playbook.md) | 这里收拢了最短运维命令 |
| 我只想查 operator 命令的标准写法 | [operator_command_contract.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_contract.md) | 这里是 operator 命令的单一真源 |
| 我只想先扫一页常用 operator 命令摘要 | [operator_command_summary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_summary.md) | 这里是从命令数据源自动生成的快速摘要 |
| 我是第一次接手维护这个仓库 | [new_maintainer_first_15_minutes.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/new_maintainer_first_15_minutes.md) | 先用 15 分钟建立地图并确认主链路可跑 |
| 我准备发布，想知道上线前还要核对什么 | [RELEASE_READINESS_CHECKLIST.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/RELEASE_READINESS_CHECKLIST.md) | 这里是发布前人工检查清单 |
| 我想知道仓库已经具备哪些能力 | [capability_index.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/capability_index.md) | 这里按能力面和脚本分层 |
| 我想看工作型替身是怎么建模的 | [07_workflow_agent_design.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/steps/07_workflow_agent_design.md) | 这里是 workflow 建模方法和访谈框架 |
<!-- END GENERATED: doc-router-question-table -->

## 3 条最短阅读路径

### 1. 普通用户：只想先理解“我会得到什么”

<!-- BEGIN GENERATED: doc-router-user-value-path -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. [README.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/README.md)
2. [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
3. [example_index.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/example_index.md)
<!-- END GENERATED: doc-router-user-value-path -->

### 2. 工作型替身用户：我想继续把人格层编译成 workflow

<!-- BEGIN GENERATED: doc-router-workflow-path -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
2. [07_workflow_agent_design.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/steps/07_workflow_agent_design.md)
3. [failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md)
<!-- END GENERATED: doc-router-workflow-path -->

### 3. 维护者：我只想尽快确认仓库是不是绿的

<!-- BEGIN GENERATED: doc-router-maintainer-reading-path -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

1. [new_maintainer_first_15_minutes.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/new_maintainer_first_15_minutes.md)
2. [operator_command_summary.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_summary.md)
3. [operator_command_contract.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_command_contract.md)
4. [operator_playbook.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/operator_playbook.md)
5. [RELEASE_READINESS_CHECKLIST.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/RELEASE_READINESS_CHECKLIST.md)
<!-- END GENERATED: doc-router-maintainer-reading-path -->

## 如果你只愿意先读一份

<!-- BEGIN GENERATED: doc-router-single-read -->
<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->

- 想理解当前系统：读 [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md)
- 想最快排障：读 [failure_path_guide.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/failure_path_guide.md)
- 想第一次接手维护：读 [new_maintainer_first_15_minutes.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/new_maintainer_first_15_minutes.md)
<!-- END GENERATED: doc-router-single-read -->
