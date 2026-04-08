# clone-skills

Public clone-building skills extracted from a private monorepo and prepared for standalone open-source use.

This repository currently publishes two clone-oriented workflows:

- `mind-clone-creator`: turn your own experience, judgment, and work habits into a reusable advisor or workflow-oriented clone
- `mind-clone-advisor`: build a compliant advisor workflow from public materials about another person

The root [SKILL.md](SKILL.md) acts as the public router and sends clone-related requests to the right workflow.

## Which One To Use

- Use `mind-clone-creator` when the source of truth is you: your answers, your materials, your work style.
- Use `mind-clone-advisor` when the source of truth is a public corpus about someone else and you need authorization, compliance, and source-quality checks.

## Quick Start

In a skill-enabled environment, start with a direct request such as:

- `我想创建自己的数字分身`
- `我想把自己的经验做成 AI 顾问`
- `我想用公开资料构建某个人的顾问型分身`

If the source identity is still unclear, start from the root router and let it disambiguate.

## Repository Focus

This repo is intentionally narrow:

- public self-clone creation
- public-materials-based advisor creation
- reusable prompts, scripts, references, and evaluation assets for those two flows

Local runtime artifacts, session logs, and environment-specific workspace data stay out of version control.

## Layout

```text
clone-skills/
├── SKILL.md
├── README.md
├── mind-clone-advisor/
└── mind-clone-creator/
```

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
