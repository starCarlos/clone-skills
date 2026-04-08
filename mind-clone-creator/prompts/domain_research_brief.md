# Prompt: Domain Research Brief

## 用途

为职业深度研究生成一个边界明确的研究 brief，供 `deep-research` skill 使用。

## Prompt

```text
You are preparing a bounded research brief for a digital-twin creation workflow.
Research the profession only as external context. Do not invent personal traits.

Goals:
1. Identify common tasks, decision frameworks, and capability boundaries for the profession.
2. Suggest practical source materials that this kind of professional may have.
3. Propose realistic evaluation scenarios for testing a digital twin.
4. Separate profession-level common patterns from person-specific statements.

Output structure:

## Profession Snapshot
## Common Workflows
## Common Boundaries
## Recommended Source Materials
## Evaluation Scenario Ideas
## Tensions To Confirm With User

Inputs:
- Profession: {profession}
- Core Skills: {skills}
- Known User Statements: {user_statements}
```

## Few-shot 示例

输入：

- Profession: AI Engineer
- Core Skills: RAG, evaluation, Python
- Known User Statements: 务实，先定义问题，不追新技术

输出片段：

```markdown
## Common Workflows
- 先定义业务目标和验收指标，再拆系统链路
- 用失败样本和评估集定位问题，而不是只看主观体验

## Tensions To Confirm With User
- 外部资料常强调快速试错，但该用户明确更重视可落地性，需要确认其在探索阶段对速度的容忍度
```
