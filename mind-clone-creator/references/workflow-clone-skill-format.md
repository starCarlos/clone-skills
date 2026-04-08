# Workflow Clone Skill Format

## Purpose

定义 `mind-clone-creator` 输出的 workflow clone skill 的 `SKILL.md` 结构。

它和 personal clone skill 的区别是：

- personal clone 重点是“像这个人怎么判断和表达”
- workflow clone 重点是“按这个人的方法，把某一类工作分阶段推进到交付”

## Required Frontmatter

前言至少包含：

- `name`
- `description`
- `metadata.openclaw.emoji`
- `metadata.openclaw.clone.type`
- `metadata.openclaw.clone.workflow_name`
- `metadata.openclaw.clone.based_on`
- `metadata.openclaw.requires`

推荐结构：

```yaml
metadata:
  openclaw:
    emoji: "⚙️"
    clone:
      type: "workflow"
      version: "1.0"
      created_at: "2026-03-13"
      profession: "AI Engineer"
      workflow_name: "AI工程需求实现蓝图"
      based_on: "AI 工程师分身"
      draft_status: "final"
      quality_score: 78
    requires:
      config:
        - "clone.identity_confirmed"
        - "workflow.blueprint_present"
```

## Required Sections

workflow clone skill 的 `SKILL.md` 至少应包含：

1. `# {name} 工作型分身`
2. `## 身份声明`
3. `## 适用范围`
4. `## 激活规则`
5. `## 工作流入口`
6. `## 阶段执行规则`
7. `## 阶段动作`
8. `## 工具调用规则`
9. `## 阶段切换规则`
10. `## 人工介入点`
11. `## 状态记录要求`
12. `## 交付要求`
13. `## 表达方式`
14. `## 执行优先级`
15. `## 当前状态`

## Visible Runtime Metadata

除 frontmatter 外，编译后的 `SKILL.md` 顶部还应显示一小段可读元信息，至少包含：

- `生成时间 / Generated At`
- `版本 / Version`
- `草稿状态 / Draft Status`
- `质量评分 / Quality Score`

这样即使下游界面默认不展示 frontmatter，操作者也能直接判断当前 workflow clone 的状态。

## Source Mapping

- `clone_config.yaml` 提供人格基础、边界、表达风格、职业信息
- `workflow_blueprint.md` 提供工作单元、阶段、动作、工具、切换规则、人工介入点和交付要求

推荐转换路径：

`clone_config.yaml + workflow_blueprint.md -> scripts/build_workflow_clone_skill.py -> workflow clone skill directory`

如果要让 workflow clone 按任务持续推进，推荐再补：

`workflow_blueprint.md -> scripts/init_workflow_task_state.py -> workflow_task_state.yaml`

## Runtime Intent

workflow clone skill 不是“所有任务都自动执行”的通用 Agent。
它应该只负责：

- 一类明确工作单元
- 一条稳定工作流
- 明确的人工介入边界

如果工作类型不同，应该分别建不同的 workflow clone。

## Optional Runtime State

推荐在 workflow clone 目录中同时放一份 `workflow_task_state.yaml`，至少包含：

- `task_id`
- `task_summary`
- `status`
- `current_stage`
- `completed_stages`
- `pending_actions`
- `blockers`
- `waiting_for_user`
- `next_step`

这样 runtime 才能稳定判断“现在在哪一阶段、下一步做什么、何时暂停升级”。
