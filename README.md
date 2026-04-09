# clone-skills

[中文 README](README.zh.md)

Build clone-style advisors that are more structured, auditable, and reusable than a one-off persona prompt.

`clone-skills` is an open-source repository of clone-building workflows extracted from a private monorepo. It is built for people who want more than tone imitation: the goal is to turn judgment style, source material, and workflow logic into reusable skills.

## What You Get

This repository currently publishes two clone-oriented workflows:

| Skill | What It Helps You Build |
| --- | --- |
| `mind-clone-creator` | A clone based on your own experience, judgment, work habits, and expression style |
| `mind-clone-advisor` | A compliant advisor workflow built from public-source materials about another person |

The root [SKILL.md](SKILL.md) is the router that decides which workflow to use.

## Why These Skills Are Useful

Most clone projects stop at "write a prompt that sounds like someone." These workflows go further:

- They separate source-of-truth questions from prompt-writing questions, so the clone is grounded before it is styled.
- They make the clone structure explicit instead of hiding everything inside one large system prompt.
- They keep boundaries visible: what is supported, what still needs workflow design, and what must stop for compliance review.
- They give you reusable assets such as profiles, prompts, workflow artifacts, and evaluation outputs.
- They are easier to maintain, review, and extend than ad hoc persona setups.

## Layer Models

The two published workflows use different layer models. That matters because this repository treats clone-building as a stack, not a voice filter.

### `mind-clone-creator`

`mind-clone-creator` is built as an upward-expanding stack:

1. Persona layer
2. Tool layer
3. Workflow layer
4. Decision layer

The default deliverable starts from the persona layer first. Higher layers become meaningful only after a concrete work unit is defined, which keeps the clone grounded before it grows into workflow or decision support.

### `mind-clone-advisor`

`mind-clone-advisor` is built as a compliance-first analysis stack:

1. Corpus and compliance layer
2. Profile and prompt layer
3. Optional graph layer

When the graph layer is enabled, the concept hierarchy is modeled as:

- belief -> model -> topic

This gives you a way to represent not only what someone says, but how their ideas are organized.

## What You Can Use It For

- Build a digital twin that responds more like you in review, planning, and advisory contexts
- Turn your own work style into a clone that can later grow into a workflow-oriented work clone
- Build a public-materials-based advisor around a writer, investor, founder, or public thinker
- Produce structured clone assets instead of loose notes: profile files, prompts, evaluation outputs, and workflow artifacts
- Explore a person's thinking at multiple levels, from beliefs and models down to topics and evidence structures

## How To Choose

- Use `mind-clone-creator` when the source of truth is you: your answers, your materials, and your work style.
- Use `mind-clone-advisor` when the source of truth is a public corpus about another person and you need authorization, compliance, and source-quality checks.

If the source identity is still unclear, start from the root router and let it disambiguate.

## Quick Start

In a skill-enabled environment, start with prompts like these:

- `I want to create my own digital twin`
- `I want to turn my experience into an AI advisor`
- `I want to build an advisor clone of someone from public materials`

## Repository Focus

This repository is intentionally narrow in scope:

- Public self-clone creation
- Public-materials-based advisor creation
- Reusable prompts, scripts, references, and evaluation assets for those two flows

Local runtime artifacts, session logs, and environment-specific workspace data stay out of version control.

## Layout

```text
clone-skills/
├── SKILL.md
├── README.md
├── README.zh.md
├── mind-clone-advisor/
└── mind-clone-creator/
```

## Related Docs

- [SKILL.md](SKILL.md): the root router for clone-related requests
- [mind-clone-creator/README.md](mind-clone-creator/README.md): self-clone workflow overview
- [mind-clone-creator/README.zh.md](mind-clone-creator/README.zh.md): Chinese README for the self-clone workflow
- [mind-clone-creator/SKILL.md](mind-clone-creator/SKILL.md): full skill contract for self-clone creation
- [mind-clone-advisor/README.md](mind-clone-advisor/README.md): public-materials-based advisor workflow overview
- [mind-clone-advisor/README.zh.md](mind-clone-advisor/README.zh.md): Chinese README for the advisor workflow
- [mind-clone-advisor/SKILL.md](mind-clone-advisor/SKILL.md): full skill contract for the advisor workflow
- [mind-clone-advisor/references/guide.md](mind-clone-advisor/references/guide.md): longer Chinese guide for public-materials-based mind-clone work

## Boundaries

- This repository does not claim a fully autonomous work-replacing agent by default.
- `mind-clone-advisor` should only be used with legitimate public-source workflows and proper authorization review.
- Files under `mind-clone-advisor/registry/` should be treated as templates, not production data.
- Generated examples should be reviewed before publishing downstream forks.

## Repository Hygiene

- Prefer relative paths in local configs and generated artifacts.
- Keep local runtime outputs, logs, and session artifacts out of commits.
- Keep public docs aligned with the currently published modules.

## License

MIT
