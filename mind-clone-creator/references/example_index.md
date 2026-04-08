# Example Index

这份文档告诉你 `examples/ai_engineer` 里每个文件该怎么读。

示例目录：

- `examples/ai_engineer`

## 建议阅读顺序

1. 先看 `interview_filled.md`
2. 再看 `mind_profile.md`
3. 再看 `system_prompt.md`
4. 再看 `eval_report.md`
5. 如果要看 workflow 轨道，再看 `workflow_interview_filled.md`
6. 再看 `workflow_blueprint.md`
7. 最后看两个 skill 成品：
   `personal_clone_skill_SKILL.md`
   `workflow_clone_skill_SKILL.md`

## 文件对照表

| 文件 | 它代表什么 | 什么时候看 |
| --- | --- | --- |
| `interview_filled.md` | 一份完成的人格层访谈输入 | 想看“原始访谈长什么样”时 |
| `interview_filled_loose.md` | 更松散的一份访谈输入 | 想看系统能否从较松散输入里抽结构时 |
| `mind_profile.md` | 访谈抽成的思维画像 | 想看“访谈如何变成画像”时 |
| `system_prompt.md` | 画像下沉后的系统提示 | 想看“画像如何变成 prompt”时 |
| `eval_report.md` | 质量评估结果 | 想看为什么是 `final` / `draft` 时 |
| `research_digest.md` | 可选的职业研究补充 | 想看外部研究层怎样补充人物上下文时 |
| `clone_config.yaml` | 人格层配置主文件 | 想看最终配置长什么样时 |
| `clone_config_input.json` | 组装 `clone_config.yaml` 的结构化输入 | 想看配置生成前的中间层时 |
| `workflow_interview_filled.md` | workflow 访谈输入 | 想看 W1-W7 填完后长什么样时 |
| `workflow_blueprint.md` | workflow 蓝图成品 | 想看工作流最终如何落成结构化蓝图时 |
| `workflow_blueprint_input.json` | workflow 蓝图的结构化输入 | 想看蓝图渲染前的中间层时 |
| `personal_clone_skill_SKILL.md` | 人格层 skill 成品示例 | 想看最终 personal skill 大致格式时 |
| `workflow_clone_skill_SKILL.md` | workflow skill 成品示例 | 想看最终 workflow skill 大致格式时 |

## 读哪份最划算

- 想快速理解人格层：看 `interview_filled.md` → `mind_profile.md` → `system_prompt.md`
- 想快速理解 workflow 层：看 `workflow_interview_filled.md` → `workflow_blueprint.md`
- 想直接看成品：看 `personal_clone_skill_SKILL.md` 和 `workflow_clone_skill_SKILL.md`
