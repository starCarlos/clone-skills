# clone-skills

Clone-oriented skills extracted from a private monorepo and prepared for standalone open-source use.

## Included modules

- `mind-clone-creator`: package your own experience into a reusable advisor or workflow-oriented clone
- `mind-clone-advisor`: build a compliant advisor workflow from public materials about another person
- `colleague-clone`: recover a bounded work proxy from private local materials such as handoff docs, chat exports, and screenshots

## Current state

This is the first public extraction of the clone skill set.
The repository keeps code, prompts, references, and sample-oriented assets.
Local runtime artifacts and environment-specific workspace data are excluded from version control.

## Layout

```text
clone-skills/
├── SKILL.md
├── colleague-clone/
├── docs/
├── mind-clone-advisor/
└── mind-clone-creator/
```

## Notes

- Prefer relative paths in local configs and generated artifacts.
- Treat files under `mind-clone-advisor/registry/` as templates, not production data.
- Local test/runtime outputs should stay ignored and out of commits.
- Review generated examples before publishing downstream forks if you add your own artifacts.

## License

MIT
