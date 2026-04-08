---
name: colleague-clone
description: Use when the user wants to build a reusable colleague skill from private work materials such as chat exports, handoff docs, internal emails, screenshots, and pasted notes.
---

# Colleague Clone

## Scope

Build a reusable colleague-oriented clone from private work materials.
This workflow is for predecessors, mentors, teammates, or colleagues whose working style needs to be recovered from internal traces rather than self-interview or public materials.

## Use This Skill When

- The user wants to rebuild a former teammate or predecessor from private work artifacts
- The source of truth is private work material such as chats, handoff docs, emails, screenshots, or pasted notes
- The user needs a bounded work proxy for consultation, review, or context restoration

## Do Not Use This Skill When

- The user wants to clone themselves; use `mind-clone-creator`
- The user wants to model a public figure from public materials; use `mind-clone-advisor`
- The user only wants a one-off impression prompt, not a reusable skill

## MVP Workflow

1. Capture target identity and relationship
2. Import local files or pasted text
3. Normalize source materials into a standard record format
4. Split analysis into `persona` and `work`
5. Generate a draft bundle that can later be refined or updated

The current outward-facing reading model prefers four user-facing views layered on top of those internal files:

- role scope
- work method
- communication style
- boundary constraints

## Output Contract

- `sources/intake_request.yaml`
- `sources/manifest.jsonl`
- `normalized/`
- `analysis/`
- `meta.json`
- rendered draft skill files in a colleague bundle
- update support for new files and manual overrides
- rollback support via version snapshots

## Current Local Inputs

- Markdown and plain text files
- PDF files
- Image and screenshot files such as `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, and `.gif`
- Pasted text stored into bundle-local artifacts
- Generic JSON message exports
- Slack-style export directories and zip bundles
- Feishu-style export JSON files and directories
- DingTalk-style export JSON files
- WeChat-compatible export JSON files
- `.eml` email files
- `.mbox` mailboxes

## Current Local Commands

- `inspect_colleague_sources.py` for pre-normalization source diagnostics
- `bootstrap_colleague_clone.py` for one-shot local draft generation
- `promote_colleague_skill.py` for promoting a draft bundle to `final_confirmed`
- `inspect_colleague_release_bundle.py` for unified reading of finalized release artifacts
- `update_colleague_skill.py` for new local sources and manual overrides
- `rollback_colleague_skill.py` for restoring a previous snapshot

`init_colleague_intake.py` and `update_colleague_skill.py` both support optional `--source-kind` overrides when auto detection is not enough.
For non-standard chat exports, `init_colleague_intake.py`, `update_colleague_skill.py`, and `inspect_colleague_sources.py` also support source-level `--field-map` JSON overrides for item, speaker, channel, timestamp, and text fields.
PDF text extraction works locally with `pypdf`. Image files normalize into metadata-backed records and optionally run OCR when both `pytesseract` and the `tesseract` binary are available.
`validate_colleague_skill.py --require-final` checks placeholder content, persona/work evidence balance, field coverage, unresolved conflicts, and low-confidence critical fields before final promotion.
`inspect_colleague_sources.py` surfaces platform detection reasons, field coverage, and missing fields for platform-style exports.
Default analysis excludes private-sensitive material such as family, health, finance, and direct contact details; mixed records are sanitized into work-only sentences and the filtering is recorded in `privacy_filter`.
`bootstrap_colleague_clone.py` supports optional `--preflight` and `--stop-on-risky-preflight`, and `update_colleague_skill.py` supports explicit conflict resolution plus rebuild.

## Boundary

This skill is private-materials-first and draft-first.
It should preserve evidence and boundaries, and it should not pretend to have stronger certainty than the available materials support.

## Reference

- Detailed design: `references/design.md`
- Bundle and schema details: `references/schemas.md`
