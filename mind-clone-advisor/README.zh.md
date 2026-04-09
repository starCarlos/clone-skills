# mind-clone-advisor

[返回根 README](../README.zh.md)
[English README](README.md)

基于他人的公开资料构建合规的 advisor workflow。

## 它做什么

`mind-clone-advisor` 用于基于公开语料构建人物顾问型 clone。

它重点覆盖：

- 人物画像提取与 profile synthesis
- system prompt 设计
- 可选的 RAG workflow 设计
- 评测、校验与合规审查

## 适合什么场景

- 你想根据某个公众人物的公开资料还原其思考风格
- 你需要的是完整构建流程，而不是一次性的模仿式 prompt
- 你需要在声称可用之前先完成来源审查、授权检查和质量门控

## 强制门槛

1. Registry 合规检查与授权审查
2. 来源范围与元数据质量检查
3. 输出质量与安全审查

## 快速开始

- 用 `python3 scripts/person.py ...` 注册或检查人物
- 拉取并规范化公开资料
- 提取画像、生成 system prompt，并对结果做评测

如果授权状态或来源合法性不明确，就必须在画像合成前停止。
如果你还没决定该走哪条 clone 工作流，也可以先从根目录的 [SKILL.md](../SKILL.md) 进入。

## 典型产物

- registry 条目
- 规范化后的语料
- thinking / profile 相关产物
- system prompt
- 可选的 RAG 方案或 workflow 产物
- 评测与合规审查结果

## 相关文档

- [SKILL.md](SKILL.md)：完整 skill 说明
- [references/long-form.md](references/long-form.md)：长文档工作流说明
- [references/guide.md](references/guide.md)：语料准备与提取实践指南
- [思维克隆_私人顾问构建指南.md](思维克隆_私人顾问构建指南.md)：更完整的中文长指南
- [references/acceptance.md](references/acceptance.md)：验收预期
- [references/case_template.md](references/case_template.md)：案例模板

## 边界说明

- 这条工作流面向合规的公开资料构建，不是随意的人物模仿。
- 如果授权不明确，应保留在 review 状态，并在画像合成前停止。
- 如果来源质量不足，应返回补强计划，而不是假装 advisor 已经可用。

## 目录结构

```text
mind-clone-advisor/
├── SKILL.md
├── README.md
├── README.zh.md
├── references/
├── registry/
├── scripts/
└── assets/
```
