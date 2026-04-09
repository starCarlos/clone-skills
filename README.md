# clone-skills

[中文 README](README.zh.md)

An open-source repository of clone-building skills extracted from a private monorepo.

This repository currently publishes two clone-oriented workflows:

| Skill | Purpose |
| --- | --- |
| `mind-clone-creator` | Turn your own experience, judgment, and work habits into a reusable advisor or workflow-oriented clone. |
| `mind-clone-advisor` | Build a compliant advisor workflow from public materials about another person. |

The root [SKILL.md](SKILL.md) is the public router for clone-related requests.

## How To Choose

- Use `mind-clone-creator` when the source of truth is you: your answers, your materials, and your work style.
- Use `mind-clone-advisor` when the source of truth is a public corpus about another person and you need authorization, compliance, and source-quality checks.

## Quick Start

In a skill-enabled environment, start with prompts like these:

- `I want to create my own digital twin`
- `I want to turn my experience into an AI advisor`
- `I want to build an advisor clone of someone from public materials`

If the source identity is still unclear, start from the root router and let it disambiguate.

## Repository Focus

This repository is intentionally narrow in scope:

- Public self-clone creation
- Public-materials-based advisor creation
- Reusable prompts, scripts, references, and evaluation assets for those two flows

Local runtime artifacts, session logs, and environment-specific workspace data stay out of version control.

## Layer Overview

The two published workflows use different layer models:

- `mind-clone-creator`: persona layer -> tool layer -> workflow layer -> decision layer
- `mind-clone-advisor`: corpus and compliance layer -> profile and prompt layer -> optional graph layer

For `mind-clone-advisor`, the optional concept hierarchy inside the graph layer is modeled as:

- belief -> model -> topic

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
- [mind-clone-creator/README.md](mind-clone-creator/README.md): the self-clone workflow overview
- [mind-clone-creator/README.zh.md](mind-clone-creator/README.zh.md): the Chinese README for the self-clone workflow
- [mind-clone-creator/SKILL.md](mind-clone-creator/SKILL.md): the full skill contract for self-clone creation
- [mind-clone-advisor/README.md](mind-clone-advisor/README.md): the public-materials-based advisor workflow overview
- [mind-clone-advisor/README.zh.md](mind-clone-advisor/README.zh.md): the Chinese README for the public-materials-based advisor workflow
- [mind-clone-advisor/SKILL.md](mind-clone-advisor/SKILL.md): the full skill contract for the advisor workflow
- [mind-clone-advisor/references/guide.md](mind-clone-advisor/references/guide.md): the longer Chinese guide for building a public-materials-based mind clone

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
