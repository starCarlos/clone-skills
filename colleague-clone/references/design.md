# Colleague Clone Design Reference

The current design source of truth lives in:

- `docs/superpowers/specs/2026-04-07-colleague-clone-design.md`
- `docs/superpowers/plans/2026-04-07-colleague-clone-mvp.md`

This local reference exists to keep the skill self-describing.

## MVP Boundary

The first implementation slice only supports:

- root routing
- bundle initialization
- local markdown and text normalization

The current local MVP additionally supports:

- one-command bootstrap for the local pipeline
- persona analysis
- work analysis
- draft rendering
- draft validation
- final promotion gate
- bundle updates via new local sources
- pasted-text source import
- JSON message export normalization
- Slack-style export directory and zip normalization
- Feishu-style export JSON and directory normalization
- DingTalk-style export JSON normalization
- WeChat-compatible export JSON normalization
- PDF text extraction
- image and screenshot normalization with optional OCR
- `.eml` email normalization
- `.mbox` mailbox normalization
- manual overrides with version snapshots
- rollback from version snapshots
- import summaries with explicit source detection metadata
- richer persona/work extraction for coordination, boundaries, delivery shape, and incident mode
- final gates based on evidence balance and field coverage
- pre-normalization diagnostics for source quality before bundle creation
- field-level confidence and conflict extraction for analysis outputs
- bootstrap preflight gating before bundle creation
- explicit conflict-resolution notes that clear resolved analysis conflicts
- source-level field mapping overrides for non-standard platform exports
- inspect diagnostics that explain platform detection mode, reasons, and field coverage

It does not yet support:

- live Feishu/Slack/DingTalk connectors
- final-grade confidence review
- workflow runtime integration
