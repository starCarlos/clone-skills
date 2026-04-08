---
name: mind-clone-advisor
description: Use this skill whenever the user wants to build a persona advisor, mind clone, digital twin, or public-materials-based consultant workflow, including profile extraction, prompt design, RAG structure, evaluation, and compliance checks.
---

# Mind Clone Advisor

## Scope

Build compliant persona/mind-clone workflows. Follow `SKILL-OPERATING-STANDARD.md`.

## Use This Skill When

- The user wants to clone a public figure's thinking style from public materials
- The task includes persona extraction, system prompts, RAG, evaluation, or update workflow design
- The user asks for a compliant process rather than a one-off impersonation prompt

## Do Not Use This Skill When

- The user only needs one answer in a persona's tone, not a build workflow
- Authorization or source legitimacy is unclear and cannot be resolved
- The task is ordinary research or content harvesting without advisor construction

## Mandatory Gates

1. Registry compliance check and authorization review
2. Source scope and metadata quality check
3. Output quality and safety review

## Fast Workflow

1. Define objective, persona scope, and deliverables
2. Register or inspect the persona via `scripts/person.py`
3. Ingest and normalize corpus
4. Extract profile and compose system prompt
5. Build optional RAG workflow
6. Run artifact-coverage evaluation, validation, and compliance review

## Output Contract

- Facts: source range, dates, authorization status
- Inference: profile extraction logic
- Delivery: generated files and paths
- Risks: authorization gaps, sample bias, update plan

## Failure / Fallback Rules

- If authorization is unclear, keep the registry record in `needs_review` and stop before profile synthesis
- If source quality is weak, return an upgrade plan instead of pretending the clone is ready
- If the user needs corpus collection first, hand off to `content-harvester`

## Reference

Full scripts, folder standards, compliance review flow, and advanced pipeline: `references/long-form.md`
