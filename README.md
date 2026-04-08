# clone-skills

Public clone-building skills extracted from a private monorepo and prepared for standalone open-source use.

## Included Skills

- `mind-clone-creator`: package your own experience, judgment, and work habits into a reusable advisor or workflow-oriented clone
- `mind-clone-advisor`: build a compliant advisor workflow from public materials about another person

## Repository Focus

This repository currently focuses on two public-facing workflows:

- self-clone creation
- public-materials-based advisor creation

Local runtime artifacts, session logs, and environment-specific workspace data are kept out of version control.

## Layout

```text
clone-skills/
├── SKILL.md
├── mind-clone-advisor/
└── mind-clone-creator/
```

## Notes

- The root `SKILL.md` acts as the public router for clone-related tasks.
- Prefer relative paths in local configs and generated artifacts.
- Treat files under `mind-clone-advisor/registry/` as templates, not production data.
- Local test/runtime outputs should stay ignored and out of commits.
- Review generated examples before publishing downstream forks if you add your own artifacts.

## License

MIT
