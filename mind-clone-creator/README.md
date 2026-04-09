# mind-clone-creator

[Back to root README](../README.md)
[中文 README](README.zh.md)

Turn your own experience, judgment, and work habits into a reusable AI advisor, and extend it toward a workflow-oriented work clone when needed.

## What It Does

`mind-clone-creator` structures how you think, respond, and move work forward.

It currently supports two main paths:

- `persona-only`: deliver a persona-layer clone first for advice, clarification, review, and bounded collaboration
- `persona-plus-workflow`: keep both the persona layer and a workflow track in the same working bundle, then continue compiling it into a workflow-oriented clone

## Layer Model

This workflow is easiest to understand as a four-layer model:

1. Persona layer: judgment standards, boundaries, expression style, and collaboration preferences
2. Tool layer: what tools and skills are available in the real environment
3. Workflow layer: how a task moves stage by stage, with inputs and outputs for each stage
4. Decision layer: how the clone decides what stage it is in and what to do next

The current default flow always starts from the persona layer.
`persona-plus-workflow` extends upward only after a concrete work unit is defined.

## Good Fits

- You want an advisor that answers more like you
- You want to capture your judgment style, expression, and working boundaries
- You want to grow a persona clone into a workflow-oriented work clone over time
- You maintain sample stacks, latest stacks, or release-readiness checks for this workflow

## Quick Start

- `I want to create my own digital twin`
- `I want to build a persona + workflow work clone`

If you have not decided which clone workflow you need yet, start from the root [SKILL.md](../SKILL.md).

## Typical Outputs

- personal clone skill
- `clone_config.yaml`
- `mind_profile.md`
- `system_prompt.md`
- `eval_report.md`
- `workflow_interview.md`
- `workflow_blueprint.md`
- workflow runtime bundle

## Maintainer Commands

- `python3 scripts/validate_repo_docs.py --format json`
- `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`
- `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`
- `python3 scripts/clone_ops.py validate release-readiness --output-root /tmp/mind-clone-sample-stack-release --summary-json /tmp/mind-clone-release-readiness.json`

## Related Docs

- [SKILL.md](SKILL.md): full skill contract
- [references/current_system_flow.md](references/current_system_flow.md): current system flow
- [references/capability_index.md](references/capability_index.md): script and capability map
- [references/doc_router.md](references/doc_router.md): documentation router
- [references/operator_playbook.md](references/operator_playbook.md): operator-oriented guidance
- [references/new_maintainer_first_15_minutes.md](references/new_maintainer_first_15_minutes.md): fast maintainer entry
- [RELEASE_READINESS_CHECKLIST.md](RELEASE_READINESS_CHECKLIST.md): release gate checklist

## Honest Boundaries

By default, this workflow is good at:

- answering in a way that sounds more like you
- acting as a bounded consultation or review proxy
- preserving your explicit experience, style, and decision habits

By default, it is not:

- a fully autonomous execution agent
- a finished workflow system
- a clone that can route and run arbitrary work end to end on its own

In other words, the default deliverable reliably covers the persona layer first.
The higher workflow and decision layers require additional workflow modeling.

## Layout

```text
mind-clone-creator/
├── SKILL.md
├── README.md
├── README.zh.md
├── scripts/
├── steps/
├── prompts/
├── templates/
├── references/
├── tests/
└── examples/
```
