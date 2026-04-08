# Step 04: System Prompt 生成

> 后台自动步骤，属于用户可见 Step 4 的一部分

## 输入

- `mind_profile.md`（来自 Step 03）
- `skill_config`（来自 Step 01）

## 处理逻辑

1. 调用 `prompts/prompt_generator.md`。
2. 生成 System Prompt。
3. 向用户展示并确认。

## System Prompt 约束

- 不超过 800 字。
- 用第一人称，但不扮演“那个人本人”。
- 必须包含能力边界声明。
- 必须包含不确定性处理方式。
- 语言风格匹配用户的表达习惯。

## 输出

`system_prompt.md`，结构见 `templates/system_prompt_template.md`。
