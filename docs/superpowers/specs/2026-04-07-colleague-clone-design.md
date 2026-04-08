# Colleague Clone Design

## Summary

Add a third clone workflow under `clones/` named `colleague-clone`.

This workflow is for building a reusable colleague skill from private work materials such as chat exports, handoff docs, emails, screenshots, and pasted notes. It is distinct from:

- self-cloning via `mind-clone-creator`
- public-material persona advisors via `mind-clone-advisor`

The goal is not to imitate a person perfectly. The goal is to recover enough of their working judgment, communication style, and recurring operating habits to support bounded consultation, review, and context restoration.

## Motivation

The current clone routing layer only handles two source-of-truth models:

- the user's own answers and self-authored materials
- another person's public materials, with compliance gates

It does not handle the common internal workflow where a colleague, predecessor, mentor, or partner leaves behind fragmented private materials and the user wants a stable working proxy.

External inspiration exists in `titanwings/colleague-skill`, especially in its intake UX, persona/work split, and iterative correction flow. This repository should not copy that implementation directly. It should absorb the product strengths while preserving the current architecture's separation of routing, normalization, analysis, validation, and release.

## Goals

- Add a dedicated `colleague-clone` workflow with clear routing semantics.
- Support local-file and pasted-text ingestion in MVP.
- Normalize heterogeneous private materials into one machine-readable intermediate layer.
- Analyze the target in two separate tracks: `persona` and `work`.
- Generate a runnable colleague skill package.
- Support additive updates and user corrections.
- Preserve evidence traceability from conclusions back to source records.
- Support `draft` vs `final` readiness.

## Non-Goals

- Perfect identity simulation
- Autonomous job replacement
- Default live integration with enterprise systems in MVP
- Public-figure compliance workflow reuse
- Generic “act like X” one-shot prompting
- Full workflow runtime generation in MVP

## Routing

Update the root router at `clones/SKILL.md` to route into three clone classes:

- `mind-clone-creator`
  - clone the user from self knowledge and self interview
- `mind-clone-advisor`
  - build a compliant advisor from public materials of another person
- `colleague-clone`
  - build a private-materials-based colleague skill from work traces

### Trigger Examples

- `/create-colleague-clone`
- "给我做一个同事分身"
- "把前任负责人做成 skill"
- "根据这些聊天记录和交接文档做个工作替身"

## User Flow

Keep the user-facing flow to five steps:

1. Identify the target and relationship
2. Collect source materials
3. Normalize and summarize evidence
4. Review persona/work draft summaries
5. Generate the skill and allow later correction

This mirrors the simplicity of `mind-clone-creator` while changing the evidence source from self-interview to imported materials.

## Directory Layout

Add a new skill:

```text
clones/
  colleague-clone/
    SKILL.md
    references/
      design.md
      schemas.md
    templates/
      colleague_skill_template.md
      persona_template.md
      work_template.md
      meta_template.json
    scripts/
      init_colleague_intake.py
      normalize_colleague_sources.py
      analyze_colleague_persona.py
      analyze_colleague_work.py
      build_colleague_skill.py
      update_colleague_skill.py
      validate_colleague_skill.py
    examples/
      sample_colleague/
```

Each generated colleague bundle lives under:

```text
colleague-clones/{slug}/
  SKILL.md
  persona.md
  work.md
  meta.json
  evidence_index.jsonl
  version_history.jsonl
  sources/
    intake_request.yaml
    manifest.jsonl
  normalized/
    messages/
    docs/
    emails/
    pasted/
  analysis/
    persona_profile.json
    work_profile.json
    merge_report.json
  versions/
    v1/
    v2/
```

## State Model

Persist workflow state in `meta.json`:

```json
{
  "state": "intake_started|sources_pending|sources_normalized|analysis_ready|draft_generated|final_confirmed"
}
```

This makes the workflow resumable and keeps it aligned with the explicit-state pattern already used in the clone stack.

## Source Model

### Intake Request

`sources/intake_request.yaml`

```yaml
subject:
  name: "Alice"
  slug: "alice"
  relationship: "predecessor"
  org_context: "search infra team"
manual_profile:
  role_summary: "P6 backend engineer"
  personality_tags: ["direct", "strict"]
  culture_tags: ["byte-style"]
  subjective_impression: "CR 很狠，但结论清楚"
sources:
  - type: "markdown"
    path: "/path/to/notes.md"
    note: "handoff notes"
    trust_level: "direct"
```

### Source Manifest

`sources/manifest.jsonl`

One line per imported artifact, including:

- original path or inline origin
- source type
- import timestamp
- parse status
- parser used
- content summary
- trust level

## Normalized Record Model

All materials must normalize into one record format before analysis:

```json
{
  "record_id": "msg_001",
  "source_type": "slack_export",
  "content_type": "message",
  "speaker": "target",
  "timestamp": "2026-04-07T10:00:00Z",
  "channel": "proj-alpha",
  "title": "",
  "text": "这个接口先补幂等，再谈重试",
  "tags": ["review", "backend"],
  "privacy_scope": "private_workspace",
  "confidence": 0.92
}
```

### Required Concepts

- `source_type`
- `content_type`
- `speaker`
- `timestamp`
- `text`
- `confidence`
- `privacy_scope`

### Optional Concepts

- `channel`
- `thread_id`
- `title`
- `participants`
- `attachment_refs`
- `topic_tags`

## Analysis Model

The system must never collapse persona and work into one undifferentiated blob.

### Persona Profile

`analysis/persona_profile.json`

```json
{
  "expression_style": {},
  "decision_patterns": {},
  "collaboration_style": {},
  "stress_behaviors": {},
  "boundaries_and_taboos": {},
  "stable_patterns": [],
  "conditional_patterns": [],
  "conflicts": [],
  "manual_overrides": []
}
```

### Work Profile

`analysis/work_profile.json`

```json
{
  "responsibility_scope": {},
  "workflow_patterns": {},
  "review_preferences": {},
  "delivery_preferences": {},
  "domain_knowledge": [],
  "explicit_rules": [],
  "stable_patterns": [],
  "conditional_patterns": [],
  "conflicts": [],
  "manual_overrides": []
}
```

## Evidence Model

Every important conclusion should be traceable.

`evidence_index.jsonl`

```json
{
  "evidence_id": "ev_014",
  "record_id": "msg_001",
  "field_path": "work_profile.review_preferences.api_design",
  "quote": "这个接口先补幂等，再谈重试",
  "source_type": "slack_export",
  "confidence": 0.92
}
```

### Evidence Rules

- Important behavioral claims require at least one evidence anchor.
- Strong rules should require either two evidence anchors or one explicit manual override.
- User-supplied impressions must remain labeled as `manual_input`, not disguised as observed evidence.

## Script Responsibilities

### `init_colleague_intake.py`

- create bundle directory
- initialize `intake_request.yaml`
- initialize `manifest.jsonl`
- validate minimum identity fields

### `normalize_colleague_sources.py`

- parse imported materials
- standardize them into normalized records
- optionally redact sensitive values
- write normalization summary

### `analyze_colleague_persona.py`

Extract:

- expression style
- disagreement style
- decision priorities
- collaboration habits
- stress reactions
- boundaries and taboo patterns

### `analyze_colleague_work.py`

Extract:

- ownership scope
- repeated work procedures
- delivery preferences
- review focus
- reusable rules and heuristics
- domain-specific judgment

### `build_colleague_skill.py`

- render `persona.md`
- render `work.md`
- render final `SKILL.md`
- write `meta.json`
- compile evidence index

### `update_colleague_skill.py`

Support two update modes:

- new evidence
- manual correction

### `validate_colleague_skill.py`

Validate:

- file completeness
- schema completeness
- evidence coverage
- final-readiness gates
- consistency between analysis outputs and rendered files

## Rendering Strategy

Templates should control structure, not invent content.

### `persona.md`

Suggested sections:

- core stable style
- decision behavior
- collaboration behavior
- stress behavior
- boundaries and red flags
- correction notes

### `work.md`

Suggested sections:

- ownership and domain
- recurring work paths
- output and document preferences
- review priorities
- explicit heuristics
- known limits

### `SKILL.md`

Suggested sections:

- skill metadata
- work layer
- persona layer
- runtime rules
- confidence and boundary rules
- version metadata

## Corrections

Support two correction classes.

### 1. New Evidence

When the user adds files or pasted content:

- append to source manifest
- normalize only new inputs
- recompute affected profile fields
- write `merge_report.json`
- create new version snapshot

### 2. Manual Override

When the user says things like:

- "他不会这样"
- "这条判断不对"
- "他一般会先问 context"

record:

```json
{
  "target_field": "persona.decision_patterns.disagreement_style",
  "old_value": "direct rejection",
  "new_value": "usually asks questions first",
  "reason": "user correction",
  "source": "manual_override",
  "created_at": "2026-04-07T12:00:00Z"
}
```

Manual overrides must remain explicit and auditable.

## Privacy and Redaction

Private-material colleague cloning is more sensitive than the existing clone workflows.

### Default Rules

- keep raw source materials local
- do not upload artifacts by default
- prefer analysis outputs to reference evidence instead of duplicating raw content
- redact obvious secrets and PII when requested

### Optional Flags

```bash
--redact-secrets
--redact-pii
```

Minimum redaction targets:

- email addresses
- phone numbers
- tokens and keys
- internal URLs
- customer-specific identifiers

## Failure Modes

### Sparse Materials

If the system does not have enough evidence:

- produce `draft`, not `final`
- list the missing material types
- do not hallucinate stable patterns

### Conflicting Evidence

If sources disagree:

- preserve conflicts
- distinguish stable vs conditional behavior
- avoid flattening into a single fake personality

### Render Failure

If template rendering fails:

- do not overwrite the current stable version
- fail before switching current version pointers

## Validation Gates

### Minimum Viable

- `persona.md` exists
- `work.md` exists
- `SKILL.md` exists
- `meta.json` exists
- `persona_profile.json` exists
- `work_profile.json` exists

### Final Readiness

- no unresolved placeholder text
- evidence coverage exists for key claims
- manual overrides are reflected in rendered output
- final output respects confidence and boundary rules

## MVP Scope

MVP input types:

- pasted text
- markdown / txt
- pdf
- message export files
- email files

MVP excludes:

- Feishu live collection
- Slack live collection
- DingTalk browser collection
- workflow runtime generation
- full connector ecosystem

## Reuse Strategy

### Reuse

- explicit workflow state ideas from `mind-clone-creator`
- ingest layering ideas from `mind-clone-advisor`
- existing validator culture and release-gate mindset

### Do Not Reuse Directly

- self-interview flow from `mind-clone-creator`
- public-person authorization registry from `mind-clone-advisor`
- prompt-heavy direct generation style from external `colleague-skill`

## Milestones

### Phase 1

- add routing
- define schemas
- support local-file and pasted-text intake
- support normalization
- support persona/work analysis
- support skill rendering
- support validation

### Phase 2

- additive updates
- manual overrides
- version snapshots
- rollback support

### Phase 3

- Feishu/Slack/DingTalk collectors
- browser-assisted or API-assisted ingestion

### Phase 4

- optional workflow blueprint generation from `work_profile`
- deeper integration with workflow clone runtime

## Acceptance Criteria

### Structural

- generated bundle matches expected layout
- schemas parse cleanly
- state transitions are valid

### Content

- persona and work are clearly separated
- key rules are evidence-backed
- final output contains no unresolved placeholders

### Behavioral

Given a review or decision prompt, the skill should:

- reflect the target's likely work concerns
- reflect the target's recognizable communication pattern
- admit uncertainty when evidence is weak

## Open Questions

- Should `colleague-clone` output into a clone-specific root like `colleague-clones/` or reuse a shared artifact root with manifest routing?
- Should manual overrides always win over evidence, or should some fields remain evidence-dominant?
- Should OCR for screenshots be part of MVP or deferred behind a helper dependency?
- Should version snapshots be full file copies or manifest-addressed diffs?

## Recommended First Slice

Build the smallest vertical slice that proves the architecture:

1. root routing to `colleague-clone`
2. local text and markdown intake
3. normalization into standard records
4. persona/work analysis into JSON
5. rendering of `persona.md`, `work.md`, `SKILL.md`
6. validation for draft readiness

Do not start with live collectors.
Do not start with rollback.
Do not start with workflow runtime.
