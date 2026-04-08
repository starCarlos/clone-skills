# Personal Clone Skill Format

## Purpose

定义 `mind-clone-creator` 输出的 personal clone skill 的 `SKILL.md` 结构。

这个文件不是普通工具 skill 的“触发说明”，而是用户数字分身在 OpenClaw 中的运行人格入口。

## Core Difference

- 普通 skill：按任务触发，完成任务后退出
- 分身 skill：持续作为当前人格层存在
- 普通 skill：重点描述“怎么做”
- 分身 skill：重点描述“这个人是谁、怎么判断、怎么说话”

## Required Frontmatter

前言必须包含：

- `name`
- `description`
- `metadata.openclaw.emoji`
- `metadata.openclaw.clone`
- `metadata.openclaw.requires`

推荐字段：

```yaml
metadata:
  openclaw:
    emoji: "🧠"
    clone:
      type: "personal"
      version: "1.0"
      quality_score: 78
      draft_status: "final"
      created_at: "2026-03-13"
      profession: "AI Engineer"
      expertise:
        - "RAG 系统设计"
        - "模型评估"
    requires:
      config:
        - "clone.identity_confirmed"
```

## Required Sections

Personal clone skill 的 `SKILL.md` 至少应包含：

1. `# {name} 数字分身`
2. `## 身份声明`
3. `## 始终激活规则`
4. `## 能力范围`
5. `## 思维方式`
6. `## 核心信念`
7. `## 决策原则`
8. `## 表达方式`
9. `## 不确定性处理`
10. `## 可用工具`
11. `## Use This Clone When`
12. `## Do Not Use This Clone When`
13. `## 记忆规则`
14. `## 当前状态`

## Visible Runtime Metadata

除 frontmatter 外，编译后的 `SKILL.md` 顶部还应显示一小段可读元信息，至少包含：

- `生成时间 / Generated At`
- `版本 / Version`
- `草稿状态 / Draft Status`
- `质量评分 / Quality Score`

这样即使下游界面默认不展示 frontmatter，操作者也能直接看见当前产物状态。

## Source Mapping

这些 section 主要从 `clone_config.yaml` 映射而来：

- `meta.*` -> frontmatter metadata + `当前状态`
- `identity.*` -> `身份声明` / `能力范围`
- `mind_profile.*` -> `思维方式` / `核心信念` / `决策原则`
- `expression.*` -> `表达方式`
- `runtime.*` -> `始终激活规则` / `Use This Clone When` / `Do Not Use This Clone When` / `记忆规则`
- `skills.*` -> `可用工具`
- `eval_summary.*` -> `当前状态`

## Source Shape Recommendation

为了让 `SKILL.md` 真正成为编译产物，`clone_config.yaml` 推荐至少包含：

- `meta.platform_target`
- `meta.identity_confirmed`
- `runtime.activation_mode`
- `runtime.exit_commands`
- `runtime.use_this_clone_when`
- `runtime.do_not_use_this_clone_when`
- `runtime.memory.remember`
- `runtime.memory.forget`

## Compilation Rule

`clone_config.yaml` 是 creator 的内部源文件。

`SKILL.md` 是运行时编译产物。

推荐转换路径：

`clone_config.yaml -> scripts/build_personal_clone_skill.py -> personal clone skill directory`

不要让用户手工拼装这些 section。
