# mind-clone-creator

帮你把自己的经验打包成可复用的 AI 顾问，也支持继续编译成工作型替身。

## 这是什么

这是一个把“你怎么判断、怎么表达、怎么推进工作”结构化出来的 skill。

目前支持两条主线：

- `persona-only`：先交付人格层分身，更像你本人地回答、澄清、评审、给建议
- `persona-plus-workflow`：在同一个 working bundle 里同时保留人格层和 workflow 轨道，后续继续编译成工作型替身

## 适合什么场景

- 想先得到一个更像你回答的顾问型分身
- 想沉淀自己的判断方式、表达风格和边界意识
- 想逐步把顾问型分身继续编译成 workflow-oriented work clone
- 想维护 sample stack、latest stack 和 release-readiness 检查

## 快速入口

- 直接对支持 skill 的环境说：`我想创建自己的数字分身`
- 或说：`我想做一个人格 + workflow 的工作型替身`

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

## 关键文档

- [references/current_system_flow.md](references/current_system_flow.md)
- [references/capability_index.md](references/capability_index.md)
- [references/doc_router.md](references/doc_router.md)
- [references/failure_path_guide.md](references/failure_path_guide.md)
- [references/glossary.md](references/glossary.md)
- [references/operator_command_contract.md](references/operator_command_contract.md)
- [references/operator_command_summary.md](references/operator_command_summary.md)
- [references/operator_playbook.md](references/operator_playbook.md)
- [references/new_maintainer_first_15_minutes.md](references/new_maintainer_first_15_minutes.md)
- [steps/07_workflow_agent_design.md](steps/07_workflow_agent_design.md)
- [RELEASE_READINESS_CHECKLIST.md](RELEASE_READINESS_CHECKLIST.md)

## 诚实边界

默认产物擅长：

- 更像你地回答问题、澄清需求、做评审
- 在边界清晰的场景中作为你的咨询代理
- 保留你的显性经验、表达风格和常用判断框架

默认产物不等于：

- 全自动接活到交付的执行 Agent
- 已编码完成的工作流系统
- 能自主判断任务阶段并编排全流程的替身

## 项目结构

```text
mind-clone-creator/
├── SKILL.md
├── README.md
├── scripts/
├── steps/
├── prompts/
├── templates/
├── references/
├── tests/
└── examples/
```
