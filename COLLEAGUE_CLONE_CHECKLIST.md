# Colleague Clone Checklist

- [x] Compare external `colleague-skill` with current `clones/` architecture
- [x] Decide architectural direction: add `colleague-clone` as a third workflow
- [x] Define routing intent and workflow boundary
- [x] Define MVP scope and non-goals
- [x] Define bundle layout and state model
- [x] Define source, normalized, analysis, and evidence schemas
- [x] Define script responsibilities
- [x] Define correction, versioning, and validation strategy
- [x] Write repository spec document
- [x] Review spec for consistency and implementation readiness

## MVP Slice 1

- [x] Add `colleague-clone` routing at `clones/SKILL.md`
- [x] Add `colleague-clone` skill skeleton and local references
- [x] Add MVP implementation plan document
- [x] Implement bundle initialization CLI
- [x] Implement local markdown/text normalization CLI
- [x] Add CLI tests for init and normalize
- [x] Run targeted `unittest` verification

## MVP Slice 2

- [x] Implement `persona` analysis CLI
- [x] Implement `work` analysis CLI
- [x] Implement draft skill renderer
- [x] Implement draft validator
- [x] Implement update flow with source append and manual override
- [x] Add end-to-end pipeline and update tests
- [x] Run targeted `unittest` verification for the full local pipeline

## MVP Slice 3

- [x] Add pasted-text input support
- [x] Normalize pasted text into bundle-local source artifacts
- [x] Implement rollback from version snapshots
- [x] Add pasted-text and rollback tests
- [x] Run targeted `unittest` verification for the extended local pipeline

## MVP Slice 4

- [x] Add JSON message export normalization
- [x] Add `.eml` normalization
- [x] Add `.mbox` normalization
- [x] Add tests for JSON/email local inputs
- [x] Run targeted `unittest` verification for the expanded local input matrix

## MVP Slice 5

- [x] Add one-command local bootstrap CLI
- [x] Add bootstrap test coverage
- [x] Document current local commands
- [x] Run targeted `unittest` verification for the bootstrap flow

## MVP Slice 6

- [x] Add stricter final-grade validation gates
- [x] Add promote command for `draft -> final_confirmed`
- [x] Add tests for successful and rejected promotion
- [x] Run targeted `unittest` verification for the release flow

## MVP Slice 7

- [x] Add `colleague-clone/README.md`
- [x] Add a complete sample bundle under `examples/`
- [x] Document end-to-end local usage and common commands

## MVP Slice 8

- [x] Add workspace export normalization for Slack-style directory and zip bundles
- [x] Add Feishu-style export detection for JSON and directory bundles
- [x] Improve title, speaker, channel, and timestamp inference for platform exports
- [x] Add Slack/Feishu fixture-based normalization tests
- [x] Add validator final-gate edge-case tests
- [x] Update docs for platform export usage
- [x] Run targeted `unittest` verification for the platform import slice

## MVP Slice 9

- [x] Add explicit `source_kind` override support to init/update commands
- [x] Return source import summaries from init and normalize commands
- [x] Add DingTalk-style export fixture coverage
- [x] Add a platform-based complete example bundle
- [x] Update docs for `source_kind` and platform summaries
- [x] Run full `unittest discover` verification for the extended import workflow

## MVP Slice 10

- [x] Add richer persona/work analysis extraction for workflow, review, delivery, coordination, and boundary patterns
- [x] Expand evidence index coverage for stronger final validation
- [x] Strengthen final gate with evidence distribution and analysis coverage checks
- [x] Add analysis-quality and final-gate regression tests
- [x] Update docs for improved analysis and release quality gates
- [x] Run full `unittest discover` verification for the quality slice

## MVP Slice 11

- [x] Add `inspect_colleague_sources.py` for pre-normalization source diagnostics
- [x] Reuse existing platform detection and summarize counts, platform, timestamps, speakers, and channels
- [x] Add behavior-focused tests for inspect diagnostics
- [x] Add a complete Feishu-based example bundle
- [x] Update docs for inspect workflow and example bundles
- [x] Run full `unittest discover` verification for the diagnostics slice

## MVP Slice 12

- [x] Add conflict detection and field-level confidence to persona/work analysis outputs
- [x] Teach final validation to reject low-confidence or unresolved-conflict bundles
- [x] Add regression tests for conflict extraction and final-gate rejection
- [x] Update docs for confidence and conflict semantics
- [x] Run full `unittest discover` verification for the confidence slice

## MVP Slice 13

- [x] Add optional bootstrap preflight using inspect diagnostics
- [x] Allow bootstrap to stop early on risky sources
- [x] Add explicit conflict resolution flow in update/rebuild
- [x] Re-run analysis after conflict resolution and clear resolved conflicts
- [x] Add regression tests for preflight and conflict resolution
- [x] Update docs for preflight and conflict-resolution workflow
- [x] Run full `unittest discover` verification for the workflow slice

## MVP Slice 14

- [x] Add structured resolution history to persona/work analysis outputs
- [x] Preserve resolved conflict snapshots for auditability after rebuild
- [x] Surface resolved conflict metadata in validation output
- [x] Add a complete DingTalk-based example bundle
- [x] Update docs for resolution audit fields and example bundles
- [x] Run full `unittest discover` verification for the audit/example slice

## MVP Slice 15

- [x] Re-check external `titanwings/colleague-skill` against current local implementation
- [x] Write a structured external comparison report with concrete architectural conclusions
- [x] Link the comparison report from `colleague-clone/README.md`

## MVP Slice 16

- [x] Add PDF source detection and normalization
- [x] Add image and screenshot source detection with optional OCR fallback
- [x] Surface PDF/image risks in inspect diagnostics
- [x] Add PDF/image fixture-based tests and bootstrap coverage
- [x] Add a complete PDF/image-based example bundle
- [x] Update README, SKILL, and schema docs for document inputs

## MVP Slice 17

- [x] Add a script to regenerate all example bundles from local fixtures
- [x] Add a rebuildable local markdown fixture for the predecessor example
- [x] Add tests for example generation and README link verification
- [x] Update README with the example regeneration command

## MVP Slice 18

- [x] Refactor image OCR into a provider-based normalization path
- [x] Stabilize image normalized record schema across OCR success and fallback states
- [x] Filter non-success image OCR placeholders out of evidence and term extraction
- [x] Add tests for mock OCR success, empty OCR, and inspect warnings

## MVP Slice 19

- [x] Add WeChat-compatible JSON export detection and normalization
- [x] Add inspect diagnostics and fixture-based tests for WeChat exports
- [x] Add a complete WeChat-based example bundle
- [x] Register the WeChat example in example regeneration and README docs

## MVP Slice 20

- [x] Add source-level field mapping overrides for non-standard exports
- [x] Make platform export parsing more tolerant to field-name variants
- [x] Surface platform detection reasons and field coverage in inspect diagnostics
- [x] Add regression tests for mapped imports, degraded exports, and generic fallback
- [x] Update docs for field mapping and platform diagnostics

## MVP Slice 21

- [x] Add user-facing semantic views closer to role, work method, communication style, and boundaries
- [x] Keep existing persona/work files and validators backward compatible
- [x] Update rendered markdown and draft skill wording to prefer the new semantic framing
- [x] Add regression tests for the semantic view outputs
- [x] Update README and schema docs for the new outward-facing terminology

## MVP Slice 22

- [x] Add privacy classification for work-related, work-adjacent, and private-sensitive content
- [x] Exclude private-sensitive content from default analysis and rendered outputs
- [x] Record auditable privacy filtering results in analysis outputs
- [x] Surface privacy-heavy source risks in inspect and final validation
- [x] Add regression tests and docs for privacy boundary behavior

## MVP Slice 23

- [x] Add explicit runtime refusal rules for private and out-of-scope questions
- [x] Derive runtime boundary guidance from privacy and confidence signals
- [x] Update generated SKILL wording to frame the clone as a bounded work proxy
- [x] Add regression tests for generated refusal and redirection rules
- [x] Update README and schema docs for runtime boundary behavior

## MVP Slice 24

- [x] Add runtime `Known Unknowns` output derived from low-confidence, conflict, and privacy signals
- [x] Validate runtime contract text against analysis outputs
- [x] Add regression tests for runtime caveat rendering and validator enforcement
- [x] Update README and schema docs for runtime caveat behavior

## MVP Slice 25

- [x] Classify runtime caveats into critical uncertainty, privacy-limited area, and minor sparse signal
- [x] Render only high-priority runtime caveats in `Known Unknowns`
- [x] Validate that minor sparse caveats stay out of the draft contract
- [x] Update README and schema docs for runtime caveat prioritization

## MVP Slice 26

- [x] Add structured `analysis/runtime_contract.json` output for runtime rules, caveats, and refusal guidance
- [x] Make draft rendering and validation consume the structured runtime contract
- [x] Add final-readiness runtime contract checks for unresolved conflicts, critical uncertainty, and privacy redirect coverage
- [x] Update tests, docs, and examples for the structured runtime contract

## MVP Slice 27

- [x] Add explicit promote-time runtime contract gate with user-facing failure reasons
- [x] Detect runtime boundary drift after update/rebuild operations
- [x] Surface a flattened runtime contract summary in validation output
- [x] Update tests, docs, and examples for runtime release/drift reporting

## MVP Slice 28

- [x] Persist runtime drift review state in bundle metadata
- [x] Add explicit drift acknowledgement flow to update
- [x] Block promote/final validation on unacknowledged runtime drift
- [x] Update tests and docs for runtime drift acknowledgement

## MVP Slice 29

- [x] Persist runtime release review history instead of only the latest snapshot
- [x] Make acknowledgements cover only the latest detected runtime drift
- [x] Add grouped human-readable runtime drift review summaries
- [x] Update tests, docs, and examples for runtime review history semantics

## MVP Slice 30

- [x] Add severity classification for runtime release review drift
- [x] Surface a concise review brief in promote and validate outputs
- [x] Update tests, docs, and examples for runtime review severity and brief output

## MVP Slice 31

- [x] Add machine-friendly release decision output for runtime review
- [x] Return consistent release decision data from promote success and failure paths
- [x] Update tests, docs, and examples for runtime release decision semantics

## MVP Slice 32

- [x] Add professional/temperament/family-boundary semantic views
- [x] Render the new semantic views in persona/work markdown
- [x] Update tests, docs, and examples for the new portrait framing

## MVP Slice 33

- [x] Add runtime-consumable portrait summaries to generated SKILL.md
- [x] Validate portrait semantic views and runtime portrait rendering consistency
- [x] Update tests, docs, and examples for runtime portrait usage

## MVP Slice 34

- [x] Add structured runtime portrait JSON output for scripts and UI layers
- [x] Validate consistency across semantic_view, runtime_portraits.json, and SKILL.md
- [x] Update tests, docs, and examples for structured runtime portrait usage

## MVP Slice 35

- [x] Add flattened runtime portrait summaries to validate/promote outputs
- [x] Add runtime portrait drift reporting to update/rebuild outputs
- [x] Update tests, docs, and examples for runtime portrait summaries and drift

## MVP Slice 36

- [x] Integrate portrait drift into runtime release review
- [x] Add runtime portrait review brief to validate/promote outputs
- [x] Update tests, docs, and examples for portrait-aware release review

## MVP Slice 37

- [x] Add stable `release_manifest.json` for finalized bundles
- [x] Generate the release manifest during promote and validate its consistency
- [x] Update tests, docs, and schemas for the release package contract

## MVP Slice 38

- [x] Add release compare report against the latest previous finalized snapshot
- [x] Expose compare report and compare brief in promote/validate outputs
- [x] Add tests, docs, and schema coverage for release comparison

## MVP Slice 39

- [x] Add stable `runtime_package.json` for runtime consumers
- [x] Generate and validate the runtime package from final bundle state
- [x] Update tests, docs, schemas, and snapshots for the runtime package contract

## MVP Slice 40

- [x] Add deterministic runtime smoke checks for final runtime packages
- [x] Expose smoke results through a dedicated CLI and optional validate hook
- [x] Update tests, docs, and schemas for runtime smoke reporting

## MVP Slice 41

- [x] Expose three stable portrait layers through runtime summary outputs
- [x] Keep runtime package answer-style fields flat while adding portrait-layer blocks
- [x] Update tests, docs, schemas, and examples for layered runtime portrait summaries

## MVP Slice 42

- [x] Add deterministic prompt eval previews for finalized runtime packages
- [x] Expose prompt eval through a dedicated CLI and optional validate hook
- [x] Update tests, docs, and schemas for runtime prompt eval reporting

## MVP Slice 43

- [x] Support custom prompt eval case sets via external JSON config
- [x] Add configurable prompt eval rules and expose profile/case source in reports
- [x] Update tests, docs, and schemas for configurable prompt eval cases

## MVP Slice 44

- [x] Add optional model-backed prompt eval mode alongside deterministic preview mode
- [x] Reuse the same prompt eval rules for deterministic and model-generated answers
- [x] Update tests, docs, and schemas for prompt eval model mode

## MVP Slice 45

- [x] Add severity-aware prompt eval reporting
- [x] Add prompt eval score and decision summaries
- [x] Gate final validation on blocking prompt eval failures only
- [x] Update tests, docs, and schemas for prompt eval severity semantics

## MVP Slice 46

- [x] Persist stable `runtime_prompt_eval.json` for finalized bundles
- [x] Surface prompt eval summary through `release_manifest.json` and `runtime_package.json`
- [x] Add prompt eval compare report against the latest previous finalized snapshot
- [x] Validate prompt eval artifact drift as part of final release outputs
- [x] Update tests, docs, and schemas for persisted prompt eval artifacts

## MVP Slice 47

- [x] Persist stable `runtime_smoke.json` for finalized bundles
- [x] Surface runtime smoke summary through `release_manifest.json` and `runtime_package.json`
- [x] Add runtime smoke compare report against the latest previous finalized snapshot
- [x] Validate runtime smoke artifact drift as part of final release outputs
- [x] Update tests, docs, and schemas for persisted runtime smoke artifacts

## MVP Slice 48

- [x] Persist stable `runtime_release_health.json` for finalized bundles
- [x] Surface a unified `release_health` summary through `release_manifest.json` and `runtime_package.json`
- [x] Validate release health artifact drift as part of final release outputs
- [x] Update tests, docs, and schemas for unified release health outputs

## MVP Slice 49

- [x] Add compare report and compare brief for `runtime_release_health.json`
- [x] Expose runtime release health compare results through promote, validate, and export
- [x] Add a dedicated CLI for inspecting runtime release health
- [x] Update tests, docs, and schemas for runtime release health comparison

## MVP Slice 50

- [x] Add a unified inspect CLI for finalized release bundles
- [x] Support focused inspect views for `release`, `runtime`, `health`, and `full`
- [x] Surface stable artifact paths, availability, and compare briefs through one output
- [x] Update tests, docs, schemas, and examples for the inspect workflow
