# mind-clone-advisor

[Back to root README](../README.md)
[中文 README](README.zh.md)

Build a compliant advisor workflow from public-source materials about another person.

## What It Does

`mind-clone-advisor` is for persona-advisor construction based on public-source corpora.

It focuses on:

- persona extraction and profile synthesis
- system prompt design
- optional RAG workflow design
- evaluation, validation, and compliance review

## Layer Model

This workflow is easiest to understand as three stacked layers:

1. Corpus and compliance layer: public-source materials, metadata quality, and authorization review
2. Profile and prompt layer: thinking/profile extraction, system prompt composition, and evaluation
3. Optional graph layer: deeper structured views such as relations, argument chains, and concept hierarchy

When the graph layer is enabled, the concept hierarchy is modeled as:

- belief -> model -> topic

## Good Fits

- You want to model a public figure's thinking style from public-source materials
- You need a build workflow, not just a one-off impersonation prompt
- You need source review, authorization checks, and quality gates before claiming the advisor is usable

## Mandatory Gates

1. Registry compliance check and authorization review
2. Source scope and metadata quality check
3. Output quality and safety review

## Quick Start

- Register or inspect a person with `python3 scripts/person.py ...`
- Ingest and normalize public-source materials
- Extract the profile, compose the system prompt, and evaluate the result

If authorization or source legitimacy is unclear, stop before profile synthesis.
If you have not decided which clone workflow fits the case yet, start from the root [SKILL.md](../SKILL.md).

## Typical Outputs

- registry entry
- normalized corpus
- thinking/profile artifacts
- system prompt
- optional RAG plan or workflow artifacts
- evaluation and compliance review outputs

## Related Docs

- [SKILL.md](SKILL.md): full skill contract
- [references/long-form.md](references/long-form.md): long-form workflow guide
- [references/guide.md](references/guide.md): practical guide for corpus prep and extraction
- [思维克隆_私人顾问构建指南.md](思维克隆_私人顾问构建指南.md): longer Chinese guide
- [references/acceptance.md](references/acceptance.md): acceptance expectations
- [references/case_template.md](references/case_template.md): case structure template

## Boundaries

- This workflow is for compliant construction from public-source materials, not casual impersonation.
- If authorization is unclear, keep the case in review and stop before synthesis.
- If source quality is weak, return an upgrade plan instead of pretending the advisor is ready.

By default, a usable result depends first on the corpus and profile/prompt layers.
The graph layer is optional and exists to deepen analysis, not to replace the core gates.

## Layout

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
