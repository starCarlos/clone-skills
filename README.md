# clone-skills

从私有 monorepo 中抽离出来、面向开源发布的 clone 构建技能仓库。
An open-source repository of clone-building skills extracted from a private monorepo.

当前仓库公开提供两条 clone 工作流。
This repository currently publishes two clone-oriented workflows.

| Skill | 中文 | English |
| --- | --- | --- |
| `mind-clone-creator` | 把你自己的经验、判断方式和工作习惯整理成可复用的顾问型或 workflow-oriented clone。 | Turn your own experience, judgment, and work habits into a reusable advisor or workflow-oriented clone. |
| `mind-clone-advisor` | 基于他人的公开资料构建合规的 advisor workflow。 | Build a compliant advisor workflow from public materials about another person. |

根目录的 [SKILL.md](SKILL.md) 是公开入口，会把 clone 相关请求路由到合适的子工作流。
The root [SKILL.md](SKILL.md) is the public router for clone-related requests.

## 如何选择 / How To Choose

- 当事实来源是你自己，也就是你的回答、你的材料和你的工作风格时，使用 `mind-clone-creator`。
- Use `mind-clone-creator` when the source of truth is you: your answers, your materials, and your work style.
- 当事实来源是某个人的公开资料，而且你需要处理授权、合规和资料质量检查时，使用 `mind-clone-advisor`。
- Use `mind-clone-advisor` when the source of truth is a public corpus about another person and you need authorization, compliance, and source-quality checks.

## 快速开始 / Quick Start

在支持 skill 的环境里，可以直接这样开始。
In a skill-enabled environment, you can start with prompts like these.

- `我想创建自己的数字分身`
- `我想把自己的经验做成 AI 顾问`
- `我想用公开资料构建某个人的顾问型分身`
- `I want to create my own digital twin`
- `I want to turn my experience into an AI advisor`
- `I want to build an advisor clone of someone from public materials`

如果你还没想清楚来源对象是谁，可以先从根路由进入，再让它继续分流。
If the source identity is still unclear, start from the root router and let it disambiguate.

## 仓库范围 / Repository Focus

这个仓库有意保持在较窄的公开范围内。
This repository is intentionally narrow in scope.

- 面向公开发布的自我 clone 构建。
- Public self-clone creation.
- 基于公开资料的 advisor 构建。
- Public-materials-based advisor creation.
- 为这两条流程服务的 prompts、scripts、references 和 evaluation 资产。
- Reusable prompts, scripts, references, and evaluation assets for those two flows.

本地 runtime 产物、会话日志和环境相关工作区数据不会纳入版本控制。
Local runtime artifacts, session logs, and environment-specific workspace data stay out of version control.

## 目录结构 / Layout

```text
clone-skills/
├── SKILL.md
├── README.md
├── mind-clone-advisor/
└── mind-clone-creator/
```

## 边界说明 / Boundaries

- 这个仓库默认不承诺交付一个可完全替代人工工作的自治 Agent。
- This repository does not claim a fully autonomous work-replacing agent by default.
- `mind-clone-advisor` 只适合用于合法公开资料和合规审查明确的场景。
- `mind-clone-advisor` should only be used with legitimate public-source workflows and proper authorization review.
- `mind-clone-advisor/registry/` 下的文件应视为模板，不应直接当作生产数据。
- Files under `mind-clone-advisor/registry/` should be treated as templates, not production data.
- 任何生成出来的示例内容，在继续对外发布前都应先人工复查。
- Generated examples should be reviewed before publishing downstream forks.

## 仓库维护约定 / Repository Hygiene

- 本地配置和生成物尽量使用相对路径。
- Prefer relative paths in local configs and generated artifacts.
- 本地 runtime 输出、日志和会话产物不要提交进仓库。
- Keep local runtime outputs, logs, and session artifacts out of commits.
- 公开文档应始终与当前实际发布的模块保持一致。
- Keep public docs aligned with the currently published modules.

## 许可 / License

MIT
