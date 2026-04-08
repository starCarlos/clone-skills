---
name: clones
description: Use this skill whenever the user wants to build a clone-style advisor, digital twin, or reusable persona system but has not yet specified whether the clone should be based on the user's own experience or on public materials from another person.
---

# Clones

## Scope

Provide a single public entry point for clone-building tasks.
Route the task to the right clone workflow instead of guessing too early between self-cloning and public-figure cloning.

## Default Rule

If the user clearly names a more specific clone skill, use it.
Otherwise start here and choose the best internal path.

## Internal Routing

Use these local clone skills:

- `mind-clone-creator` for building the user's own digital twin, work clone, or personal AI advisor from their own experience, judgment, and habits
- `mind-clone-advisor` for building a compliant public-materials-based advisor, persona consultant, or mind-clone workflow based on another person's published materials
- `colleague-clone` for building a reusable colleague skill from private work materials such as chat exports, handoff docs, emails, screenshots, and pasted notes

## Fast Decision Rules

- If the user wants to "clone myself", "做我的分身", or package their own experience into an advisor, route to `mind-clone-creator`
- If the user wants to model a public figure's thinking from interviews, letters, books, talks, or other public sources, route to `mind-clone-advisor`
- If the user wants to recover a predecessor, mentor, teammate, or colleague from private work materials, route to `colleague-clone`
- If the task includes self-interview, personal habit extraction, or workflow capture, route to `mind-clone-creator`
- If the task includes compliance checks, public-material extraction, RAG design, or safe persona simulation, route to `mind-clone-advisor`
- If the task includes private chat exports, handoff docs, internal emails, or screenshots of work conversations, route to `colleague-clone`
- If the user only says "build me a clone" and the source identity is still unclear, start here and disambiguate before going deeper

## Output Contract

- Chosen sub-skill
- Short reason for the choice
- Final handoff to the selected clone workflow

## Boundary

This skill is a public clone router, not a replacement for the deeper clone-building skills.
