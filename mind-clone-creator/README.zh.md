# mind-clone-creator

[返回根 README](../README.zh.md)
[English README](README.md)

帮你把自己的经验、判断方式和工作习惯整理成可复用的 AI 顾问，并在需要时继续扩展成 workflow-oriented work clone。

## 它做什么

`mind-clone-creator` 的核心是把“你怎么判断、怎么表达、怎么推进工作”结构化出来。

当前支持两条主线：

- `persona-only`：先交付人格层 clone，用于建议、澄清、评审和边界清晰的协作
- `persona-plus-workflow`：在同一个 working bundle 里同时保留人格层和 workflow 轨道，后续再继续编译成 workflow-oriented clone

## 适合什么场景

- 你想先得到一个更像你回答问题的顾问型分身
- 你想沉淀自己的判断方式、表达风格和工作边界
- 你想把顾问型分身逐步扩展成 workflow-oriented work clone
- 你在维护 sample stack、latest stack 或 release-readiness 检查

## 快速开始

- `我想创建自己的数字分身`
- `我想做一个人格 + workflow 的工作型替身`

如果你还没决定具体该走哪条 clone 工作流，可以先从根目录的 [SKILL.md](../SKILL.md) 进入。

## 典型产物

- personal clone skill
- `clone_config.yaml`
- `mind_profile.md`
- `system_prompt.md`
- `eval_report.md`
- `workflow_interview.md`
- `workflow_blueprint.md`
- workflow runtime bundle

## 维护者常用命令

- `python3 scripts/validate_repo_docs.py --format json`
- `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`

## 相关文档

- [SKILL.md](SKILL.md)：完整 skill 说明
- [references/current_system_flow.md](references/current_system_flow.md)：当前系统流程
- [references/capability_index.md](references/capability_index.md)：脚本与能力索引
- [references/doc_router.md](references/doc_router.md)：文档导航入口
- [references/operator_playbook.md](references/operator_playbook.md)：操作侧说明
- [references/new_maintainer_first_15_minutes.md](references/new_maintainer_first_15_minutes.md)：维护者快速入口
- [RELEASE_READINESS_CHECKLIST.md](RELEASE_READINESS_CHECKLIST.md)：发布检查清单

## 诚实边界

默认情况下，这条工作流擅长：

- 以更像你的方式回答问题
- 作为边界清晰的咨询或评审代理
- 保留你的显性经验、表达风格和常用判断框架

默认情况下，它不等于：

- 全自治执行 Agent
- 已完成的工作流系统
- 能自主路由并跑完任意工作的完整替身

## 项目结构

```text
mind-clone-creator/
├── SKILL.md
├── README.md
├── README.zh.md
├── scripts/
├── steps/
├── prompts/
├── templates/
├── references/
├── tests/
└── examples/
```
