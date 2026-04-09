---
name: clones
description: Use this skill whenever the user wants to build a clone-style advisor, digital twin, or reusable persona system but has not yet specified whether the clone should be based on the user's own experience or on public materials from another person.
---

# Clones

## Scope

Provide a single public entry point for clone-building tasks.
Route the task to the right clone workflow instead of guessing too early between self-cloning and public-figure cloning.

提供一个统一的公开入口，用来处理 clone 构建相关任务。
它的作用是把请求路由到正确的子工作流，而不是过早猜测应该走“自我 clone”还是“公开资料人物 clone”。

## Default Rule

If the user clearly names a more specific clone skill, use it.
Otherwise start here and choose the best internal path.

如果用户已经明确点名某个更具体的 clone skill，就直接使用那个 skill。
如果用户只是泛泛地说“做个 clone / 分身 / advisor”，就先从这里开始分流。

## Internal Routing

Use these local clone skills:

- `mind-clone-creator` for building the user's own digital twin, work clone, or personal AI advisor from their own experience, judgment, and habits
- `mind-clone-advisor` for building a compliant public-materials-based advisor, persona consultant, or mind-clone workflow based on another person's published materials

当前公开路由只会分到下面两个本地 skill：

- `mind-clone-creator`：当来源是用户自己，目标是构建自己的数字分身、工作型 clone 或个人 AI 顾问
- `mind-clone-advisor`：当来源是他人的公开资料，目标是构建合规的 advisor、persona consultant 或 mind-clone workflow

## Fast Decision Rules

- If the user wants to "clone myself", "做我的分身", or package their own experience into an advisor, route to `mind-clone-creator`
- If the user wants to model a public figure's thinking from interviews, letters, books, talks, or other public sources, route to `mind-clone-advisor`
- If the task includes self-interview, personal habit extraction, or workflow capture, route to `mind-clone-creator`
- If the task includes compliance checks, public-material extraction, RAG design, or safe persona simulation, route to `mind-clone-advisor`
- If the user only says "build me a clone" and the source identity is still unclear, start here and disambiguate before going deeper

可以按下面的快速规则理解：

- 想“克隆自己”、整理自己的经验、做自己的顾问型分身，走 `mind-clone-creator`
- 想基于某个公众人物或他人的公开资料构建 advisor，走 `mind-clone-advisor`
- 如果需求里出现自我访谈、个人习惯提取、workflow capture，更接近 `mind-clone-creator`
- 如果需求里出现公开资料提取、合规检查、RAG 设计、安全 persona 模拟，更接近 `mind-clone-advisor`
- 如果用户只说“帮我做个 clone”，但没有讲清楚来源对象是谁，就先从这里开始澄清再分流

## Output Contract

- Chosen sub-skill
- Short reason for the choice
- Final handoff to the selected clone workflow

这个路由入口本身不负责产出完整 clone。
它的输出应该只有三件事：

- 选择了哪个子 skill
- 为什么这么选
- 把任务正式交给对应的子工作流

## Boundary

This skill is a public clone router, not a replacement for the deeper clone-building skills.

这个 skill 的边界很明确：它是公开路由入口，不是具体 clone 构建流程本身。
