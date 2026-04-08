# Colleague Clone Schemas

## Bundle Layout

```text
colleague-clones/{slug}/
  sources/
    intake_request.yaml
    manifest.jsonl
  normalized/
    messages/
    docs/
    images/
    emails/
    pasted/
  analysis/
  versions/
  meta.json
  release_manifest.json
  runtime_package.json
  runtime_release_health.json
  runtime_smoke.json
  runtime_prompt_eval.json
```

## `meta.json`

```json
{
  "name": "Alice",
  "slug": "alice",
  "relationship": "predecessor",
  "state": "sources_pending",
  "created_at": "2026-04-07T12:00:00Z",
  "updated_at": "2026-04-07T12:00:00Z",
  "runtime_release_review": {
    "status": "pending_ack",
    "requires_ack": true,
    "last_drift_id": "2026-04-08T12:00:00Z#1",
    "last_drift_at": "2026-04-08T12:00:00Z",
    "last_drift": {
      "drift_id": "2026-04-08T12:00:00Z#1",
      "detected_at": "2026-04-08T12:00:00Z",
      "trigger": "source_update",
      "changed": true,
      "entered_required_caveat": true,
      "entered_privacy_limited": true,
      "added_required_fields": [],
      "removed_required_fields": [],
      "before": {},
      "after": {}
    },
    "drift_summary": {
      "changed": true,
      "entered_required_caveat": true,
      "entered_privacy_limited": true,
      "new_required_caveat_fields": [],
      "removed_required_caveat_fields": [],
      "new_restrictions": ["entered privacy-limited runtime boundary"],
      "new_uncertainty": ["entered required runtime caveat state"],
      "cleared_caveats": [],
      "severity": "blocking"
    },
    "last_ack": {
      "acknowledged_at": "2026-04-08T12:30:00Z",
      "acknowledged_by": "qa-reviewer",
      "note": "Reviewed privacy-limited runtime shift for the new source.",
      "acked_drift_id": "2026-04-08T12:00:00Z#1"
    },
    "last_ack_covers_latest_drift": true,
    "history": [
      {
        "event": "drift_detected",
        "event_at": "2026-04-08T12:00:00Z",
        "drift_id": "2026-04-08T12:00:00Z#1",
        "trigger": "source_update",
        "summary": {
          "changed": true,
          "entered_required_caveat": true,
          "entered_privacy_limited": true,
          "new_required_caveat_fields": [],
          "removed_required_caveat_fields": [],
          "new_restrictions": ["entered privacy-limited runtime boundary"],
          "new_uncertainty": ["entered required runtime caveat state"],
          "cleared_caveats": []
        }
      },
      {
        "event": "drift_acknowledged",
        "event_at": "2026-04-08T12:30:00Z",
        "drift_id": "2026-04-08T12:00:00Z#1",
        "acknowledged_by": "qa-reviewer",
        "note": "Reviewed privacy-limited runtime shift for the new source."
      }
    ]
  }
}
```

`runtime_release_review` is optional and appears after `update_colleague_skill.py --rebuild` detects a material runtime drift. Its status is:

- `clear`: no pending runtime release review
- `pending_ack`: runtime drift was detected and must be acknowledged before final release
- `acknowledged`: the latest pending drift was explicitly reviewed

Additional semantics:

- `last_drift_id` identifies the latest detected drift
- `last_ack.acked_drift_id` identifies which drift was acknowledged
- `last_ack_covers_latest_drift` must be `true` before final release
- `history[]` keeps the chronological `drift_detected` / `drift_acknowledged` trail
- `drift_summary.severity` classifies the release impact as `blocking`, `caution`, or `informational`

## `sources/manifest.jsonl`

Each line represents an imported source artifact.

```json
{
  "source_id": "src_001",
  "source_type": "pdf_document",
  "path": "/abs/path/to/review-handoff.pdf",
  "origin": "cli",
  "trust_level": "direct",
  "imported_at": "2026-04-07T12:00:00Z",
  "detection_mode": "explicit",
  "field_mapping": {
    "platform": "wechat",
    "items": "payload.entries",
    "speaker": "actor",
    "channel": "roomName",
    "timestamp": "sentAt",
    "text": "body.text"
  },
  "parse_status": "normalized",
  "normalized_path": "/abs/path/to/bundle/normalized/docs/src_001.jsonl",
  "detected_platform": "wechat",
  "platform_detection_mode": "platform_hint",
  "platform_detection_reasons": ["used explicit platform hint: wechat"],
  "field_coverage": {
    "text": 1.0,
    "speaker": 1.0,
    "channel": 1.0,
    "timestamp": 1.0
  },
  "missing_fields": []
}
```

`detection_mode` is one of:

- `auto`
- `explicit`
- `generated`

`source_type` currently includes:

- `markdown`
- `text`
- `pdf_document`
- `image_file`
- `json_export`
- `workspace_export`
- `wechat_export` can be detected within `workspace_export` or `json_export` payload parsing
- `email_eml`
- `email_mbox`
- `pasted_text`

`field_mapping` is optional and lets one source override non-standard message fields without changing the parser globally.

## Normalized Record

```json
{
  "record_id": "src_001_001",
  "source_id": "src_001",
  "source_type": "image_file",
  "content_type": "image_source",
  "speaker": "unknown",
  "timestamp": "2026-04-07T12:00:00Z",
  "channel": "",
  "title": "rollback-risk-screenshot",
  "text": "Image source: rollback-risk-screenshot.png\nOCR status: unavailable in current environment.",
  "tags": ["image_ocr_unavailable"],
  "privacy_scope": "private_workspace",
  "confidence": 1.0,
  "image_metadata": {
    "format": "PNG",
    "width": 320,
    "height": 120,
    "mode": "RGB"
  },
  "image_analysis": {
    "ocr_provider": "",
    "ocr_status": "unavailable",
    "ocr_text": ""
  }
}
```

For PDF inputs, `content_type` is usually `document_page`.
For image inputs, `content_type` stays `image_source`.
OCR availability is expressed through `image_analysis.ocr_provider` and `image_analysis.ocr_status`, where `ocr_status` is one of `success`, `empty`, or `unavailable`.

## Final Validation Report

`validate_colleague_skill.py --format json --require-final` returns a report like:

```json
{
  "ok": true,
  "state": "final_confirmed",
  "evidence_count": 8,
  "evidence_balance": {
    "persona": 4,
    "work": 4
  },
  "evidence_field_coverage": {
    "persona": ["persona.decision_patterns", "persona.stress_behaviors"],
    "work": ["work.review_preferences", "work.workflow_patterns"]
  },
  "analysis_conflicts": [],
  "low_confidence_fields": [],
  "privacy_counts": {
    "work_related": 8,
    "work_adjacent": 1,
    "private_sensitive": 0
  },
  "privacy_issues": ["private-sensitive content was excluded from default analysis"],
  "final_placeholders": [],
  "final_quality_issues": []
}
```

## Analysis Output

The internal analysis files are still:

- `analysis/persona_profile.json`
- `analysis/work_profile.json`
- `analysis/runtime_contract.json`
- `analysis/runtime_portraits.json`

For backward compatibility, these files keep the existing `persona.*` and `work.*` evidence-bearing fields.
In addition, each file now exposes a `semantic_view` section for user-facing reading:

- `persona_profile.json -> semantic_view.communication_style`
- `persona_profile.json -> semantic_view.collaboration_style`
- `persona_profile.json -> semantic_view.boundary_constraints`
- `persona_profile.json -> semantic_view.temperament_profile`
- `persona_profile.json -> semantic_view.family_boundary_profile`
- `work_profile.json -> semantic_view.role_scope`
- `work_profile.json -> semantic_view.work_method`
- `work_profile.json -> semantic_view.review_and_delivery`
- `work_profile.json -> semantic_view.professional_profile`

Rendered markdown keeps the old filenames:

- `persona.md`
- `work.md`

But the headings now prefer the more natural framing of:

- `Communication And Boundaries`
- `Role And Work Method`

These semantic views now also support a more direct reading layer:

- `professional_profile`: work-facing "career/professional portrait"
- `temperament_profile`: work-facing "temperament/personality portrait"
- `family_boundary_profile`: explicit family/private-life boundary portrait, not family inference

Each analysis file also includes a `privacy_filter` audit section:

- `counts.work_related`
- `counts.work_adjacent`
- `counts.private_sensitive`
- `excluded_record_ids`
- `entries[]`

`work_adjacent` means one record mixed work context with private-sensitive sentences; those private sentences are removed before default analysis.
`private_sensitive` means the record is excluded from default analysis entirely.

When `build_colleague_skill.py` renders the draft `SKILL.md`, it now also emits:

- `Runtime Portraits`
- `Runtime Rules`
- `Runtime Boundaries`
- `Known Unknowns`
- `Refusal Pattern`

Those runtime sections are derived from:

- `persona_profile.json -> semantic_view.temperament_profile`
- `persona_profile.json -> semantic_view.family_boundary_profile`
- `work_profile.json -> semantic_view.professional_profile`
- `persona_profile.json -> semantic_view.boundary_constraints.summary`
- `work_profile.json -> privacy_filter.counts`
- existing evidence and confidence signals already present in the bundle
- `runtime_contract.json -> runtime_rules / runtime_boundaries / known_unknowns / refusal_pattern`
- `runtime_portraits.json -> professional_portrait / temperament_portrait / family_boundary_portrait / answer_strategy`

`Runtime Portraits` is a runtime-facing summary layer:

- `Professional Portrait` mirrors `professional_profile.summary / scope_modules / operating_sequence / review_focus_areas / confidence`
- `Temperament Portrait` mirrors `temperament_profile.summary / tendency_tags / pressure_mode / confidence`
- `Family Boundary Portrait` mirrors `family_boundary_profile.summary / policy / allowed_scope / confidence`

`runtime_portraits.json` also provides a structured `answer_strategy` block for scripts and UI layers:

- `default_modules[]`
- `default_review_focus[]`
- `workflow_sequence[]`
- `interaction_tendencies[]`
- `questioning_tendency`
- `disagreement_style`
- `delivery_preferences[]`
- `boundary_policy`
- `redirect_topics[]`

The generated draft must frame the clone as a bounded work proxy rather than a complete person simulation.
It must refuse questions about family, health, finances, contact details, addresses, identity documents, or unsupported biography details, and redirect back to work-scoped topics.
If privacy filtering removed relevant material, or if evidence is weak or conflicting, the runtime text should say so explicitly instead of guessing.
`Known Unknowns` should enumerate low-confidence fields, unresolved conflict fields, and privacy-limited areas when those signals exist; otherwise it should emit an explicit no-major-issues fallback.
Runtime caveats are now prioritized into:

- `critical uncertainty`
- `privacy-limited area`
- `minor sparse signal`

Only the first two categories should be rendered into the draft `SKILL.md` by default.
`validate_colleague_skill.py` now treats these runtime sections as part of the draft contract and reports `runtime_contract_issues` when the rendered `SKILL.md` omits required caveats implied by the analysis outputs or incorrectly includes minor sparse caveats.
`runtime_contract.json` also carries:

- `contract_scope`
- `refusal_pattern.say`
- `refusal_pattern.redirect_to[]`
- `final_policy`
- `final_contract_issues[]`

`final_contract_issues[]` is consumed by `validate_colleague_skill.py --require-final` and should be empty before a bundle is considered final-ready.
Validation output now also includes:

- `portrait_issues`
- `release_manifest`
- `release_manifest_issues`
- `release_compare_report`
- `release_compare_brief`
- `runtime_package`
- `runtime_package_issues`
- `runtime_release_health`
- `runtime_release_health_artifact`
- `runtime_release_health_compare_report`
- `runtime_release_health_compare_brief`
- `runtime_release_health_artifact_issues`
- `runtime_smoke_artifact`
- `runtime_smoke_artifact_issues`
- `runtime_smoke_compare_report`
- `runtime_smoke_compare_brief`
- `runtime_prompt_eval_report`
- `runtime_prompt_eval_decision`
- `runtime_prompt_eval_summary`
- `runtime_prompt_eval_issues`
- `runtime_prompt_eval_blocking_issues`
- `runtime_prompt_eval_artifact`
- `runtime_prompt_eval_artifact_issues`
- `runtime_prompt_eval_compare_report`
- `runtime_prompt_eval_compare_brief`
- `runtime_smoke_report`
- `runtime_smoke_summary`
- `runtime_smoke_issues`
- `runtime_portraits_summary`
- `runtime_portraits_review_brief`
- `runtime_contract_summary`
- `runtime_contract_final_issues`
- `runtime_release_review`
- `runtime_release_review_brief`
- `runtime_release_decision`
- `runtime_release_review_issues`

`portrait_issues[]` is raised when:

- a required portrait semantic view is missing required fields, confidence, or redirect scope
- `runtime_portraits.json` drifts away from the current semantic views or runtime contract
- runtime `SKILL.md` omits a required portrait section
- runtime portrait summaries drift away from the current analysis outputs

`runtime_portraits_summary` is the stable consumption layer for scripts and UI. It includes three portrait blocks plus the flattened answer-style fields:

- `professional_portrait`
  - `summary`
  - `scope_modules[]`
  - `operating_sequence[]`
  - `review_focus_areas[]`
  - `confidence`
- `temperament_portrait`
  - `summary`
  - `tendency_tags[]`
  - `pressure_mode[]`
  - `questioning_tendency`
  - `disagreement_style`
  - `confidence`
- `family_boundary_portrait`
  - `summary`
  - `policy`
  - `allowed_scope[]`
  - `redirect_topics[]`
  - `refusal_say`
  - `confidence`

- `default_modules[]`
- `default_review_focus[]`
- `workflow_sequence[]`
- `interaction_tendencies[]`
- `delivery_preferences[]`
- `questioning_tendency`
- `disagreement_style`
- `boundary_policy`
- `private_signal_present`
- `redirect_topics[]`

`runtime_portraits_review_brief` summarizes only portrait-related review impact:

- `changed`
- `severity`
- `headline`
- `items[]`

`runtime_contract_summary` is a flattened view intended for scripts and UI layers. It includes:

- `has_required_caveats`
- `privacy_limited`
- `critical_uncertainty_fields[]`
- `required_caveat_fields[]`
- `redirect_topics[]`
- `final_issue_count`

`update_colleague_skill.py --rebuild` returns `runtime_contract_drift` with:

- `changed`
- `entered_required_caveat`
- `entered_privacy_limited`
- `added_required_fields[]`
- `removed_required_fields[]`
- `before`
- `after`

It now also returns `runtime_portraits_drift` with:

- `changed`
- `added_default_modules[]` / `removed_default_modules[]`
- `added_review_focus[]` / `removed_review_focus[]`
- `added_interaction_tendencies[]` / `removed_interaction_tendencies[]`
- `added_redirect_topics[]` / `removed_redirect_topics[]`
- `questioning_tendency_changed`
- `disagreement_style_changed`
- `boundary_policy_changed`
- `private_signal_changed`
- `before`
- `after`

When portrait drift exists, it also feeds the bundle's `runtime_release_review`. High-impact portrait drift currently includes:

- `boundary_policy_changed`
- `private_signal_changed`
- redirect-topic changes

These changes can surface in:

- `runtime_release_review.drift_summary.new_restrictions[]`
- `runtime_portraits_review_brief`
- `runtime_release_decision.reason_codes[]` as `portrait_boundary_shift`

Lower-risk portrait scope/style changes surface as:

- `runtime_release_review.drift_summary.new_uncertainty[]`
- `runtime_release_decision.reason_codes[]` as `portrait_scope_shift`

Its nested `runtime_release_review.drift_summary` also groups the drift into:

- `new_restrictions[]`
- `new_uncertainty[]`
- `cleared_caveats[]`
- `severity`

`runtime_release_review_brief` is a compact release-facing summary:

- `severity`
- `headline`
- `items[]`
- `requires_ack`

`runtime_release_decision` is the machine-friendly release gate output:

- `decision`: `allow`, `block`, or `caution`
- `reason_codes[]`
- `requires_ack`
- `review_brief`

`update_colleague_skill.py --ack-runtime-drift --ack-note "..."` records an acknowledgement in `meta.json.runtime_release_review.last_ack` and clears the pending release gate.

`promote_colleague_skill.py` checks both `runtime_contract.json` and `meta.json.runtime_release_review` before finalizing state. It returns:

- `runtime_contract_final_issues`
- `runtime_release_review`
- `runtime_release_review_brief`
- `runtime_release_decision`
- `runtime_release_review_issues`

## `release_manifest.json`

Finalized bundles also write a release package for downstream consumers:

```json
{
  "schema_version": "colleague_clone_release_manifest/v1",
  "generated_at": "2026-04-08T12:30:00Z",
  "bundle": {
    "bundle_dir": "/abs/path/to/bundle",
    "name": "Alice",
    "slug": "alice",
    "relationship": "predecessor",
    "state": "final_confirmed",
    "created_at": "2026-04-07T12:00:00Z",
    "updated_at": "2026-04-08T12:30:00Z",
    "finalized_at": "2026-04-08T12:30:00Z"
  },
  "release": {
    "snapshot_dir": "/abs/path/to/bundle/versions/v3",
    "version_count": 3,
    "version_history_count": 5,
    "latest_review_status": "acknowledged",
    "requires_ack": false
  },
  "sources": {
    "source_count": 2,
    "normalized_source_count": 2,
    "source_type_counts": {
      "markdown": 1,
      "pasted_text": 1
    },
    "detected_platform_counts": {},
    "detection_mode_counts": {
      "auto": 1,
      "generated": 1
    }
  },
  "evidence": {
    "evidence_count": 8,
    "balance": {
      "persona": 4,
      "work": 4
    },
    "field_coverage": {
      "persona": ["persona.decision_patterns", "persona.stress_behaviors"],
      "work": ["work.review_preferences", "work.workflow_patterns"]
    }
  },
  "runtime_contract_summary": {},
  "runtime_portraits_summary": {},
  "runtime_release_review": {},
  "runtime_release_review_brief": {},
  "runtime_portraits_review_brief": {},
  "runtime_release_decision": {},
  "release_health": {},
  "runtime_smoke_summary": {},
  "runtime_prompt_eval_summary": {}
}
```

`validate --require-final` now treats this file as part of the final release contract:

- it must exist for `final_confirmed` bundles
- it must stay consistent with current bundle state, source summary, evidence summary, and runtime summaries
- drift surfaces in `release_manifest_issues[]`

`compare_colleague_release.py` and finalized `validate` / `promote` responses also surface a release diff report derived from the current manifest and the latest previous snapshot manifest that exists:

- `has_previous`
- `changed`
- `headline`
- `items[]`
- `changed_sections[]`
- `sections.<section>.changed`
- `sections.<section>.changed_fields[]`

`release_compare_brief` is the compact consumption layer:

- `has_previous`
- `changed`
- `headline`
- `items[]`

## `runtime_package.json`

Finalized bundles also write a runtime-facing package for downstream agent/runtime adapters:

```json
{
  "schema_version": "colleague_clone_runtime_package/v1",
  "generated_at": "2026-04-08T12:30:00Z",
  "bundle": {
    "bundle_dir": "/abs/path/to/bundle",
    "name": "Alice",
    "slug": "alice",
    "relationship": "predecessor",
    "state": "final_confirmed",
    "finalized_at": "2026-04-08T12:30:00Z"
  },
  "system_prompt": {
    "identity": "You are Alice, a bounded work-focused colleague proxy built from reviewed local materials.",
    "runtime_rules": [],
    "runtime_boundaries": [],
    "known_unknowns": [],
    "refusal_pattern": {
      "say": "That goes beyond this work-focused colleague proxy, and I do not have evidence to answer it safely.",
      "redirect_to": ["role scope", "work method"]
    },
    "answer_style": {}
  },
  "runtime_contract_summary": {},
  "runtime_portraits_summary": {
    "professional_portrait": {},
    "temperament_portrait": {},
    "family_boundary_portrait": {},
    "default_modules": [],
    "default_review_focus": [],
    "workflow_sequence": [],
    "interaction_tendencies": [],
    "delivery_preferences": [],
    "questioning_tendency": "unknown",
    "disagreement_style": "unknown",
    "boundary_policy": "refuse_and_redirect",
    "private_signal_present": false,
    "redirect_topics": []
  },
  "release_health": {},
  "runtime_smoke_summary": {},
  "runtime_prompt_eval_summary": {},
  "release": {
    "decision": {},
    "review_brief": {},
    "compare_brief": {}
  },
  "provenance": {
    "release_manifest_path": "/abs/path/to/bundle/release_manifest.json",
    "release_manifest_schema": "colleague_clone_release_manifest/v1",
    "source_summary": {},
    "evidence_summary": {}
  }
}
```

`system_prompt.answer_style` remains the flattened answer-strategy subset. The three stable portrait blocks live under `runtime_portraits_summary`.

`validate --require-final` also treats this file as part of the final release contract:

- it must exist for `final_confirmed` bundles
- it must stay consistent with current runtime summaries, release outputs, and manifest-backed provenance
- drift surfaces in `runtime_package_issues[]`

## `runtime_release_health.json`

Finalized bundles also write a stable unified release-health artifact for direct UI/runtime consumption:

```json
{
  "schema_version": "colleague_clone_runtime_release_health/v1",
  "generated_at": "2026-04-08T12:30:00Z",
  "release_manifest_path": "/abs/path/to/bundle/release_manifest.json",
  "runtime_package_path": "/abs/path/to/bundle/runtime_package.json",
  "runtime_smoke_path": "/abs/path/to/bundle/runtime_smoke.json",
  "runtime_prompt_eval_path": "/abs/path/to/bundle/runtime_prompt_eval.json",
  "release_health": {
    "ok": true,
    "headline": "Runtime release health is clear.",
    "decision": {},
    "review": {},
    "compare": {},
    "smoke": {},
    "prompt_eval": {},
    "contract": {},
    "portraits": {}
  },
  "runtime_release_health_compare_report": {},
  "runtime_release_health_compare_brief": {}
}
```

`release_health` is the unified summary also embedded into `release_manifest.json` and `runtime_package.json`. It concentrates:

- final release decision and review brief
- release compare brief
- stable smoke summary
- stable prompt-eval summary
- compact runtime contract summary
- compact portrait summary

`runtime_release_health_compare_report` compares the current artifact with the latest previous finalized `runtime_release_health.json` that exists in bundle snapshots. It exposes:

- `has_previous`
- `changed`
- `headline`
- `items[]`
- `changed_sections[]`
- `sections.<section>.changed`
- `sections.<section>.changed_fields[]`

`validate --require-final` treats this file as part of the final release contract:

- it must exist for `final_confirmed` bundles
- it must stay consistent with the current release/runtime summaries
- drift surfaces in `runtime_release_health_artifact_issues[]`

## Inspect CLI

`inspect_colleague_release_bundle.py` is the unified read-only entrypoint for stable finalized artifacts.

It supports:

- `--view release`
- `--view runtime`
- `--view health`
- `--view full`

Its top-level JSON payload includes:

- `ok`
- `bundle_dir`
- `view`
- `artifact_paths`
- `availability`
- `issues[]`
- `compare_briefs.release`
- `compare_briefs.runtime_release_health`
- `compare_briefs.runtime_smoke`
- `compare_briefs.runtime_prompt_eval`

`full` view additionally includes:

- `release`
- `runtime`
- `health`

## `runtime_smoke.json`

Finalized bundles also write a stable runtime smoke artifact derived from the deterministic runtime smoke checks:

```json
{
  "schema_version": "colleague_clone_runtime_smoke_artifact/v1",
  "generated_at": "2026-04-08T12:30:00Z",
  "runtime_package_path": "/abs/path/to/bundle/runtime_package.json",
  "runtime_smoke_report": {},
  "runtime_smoke_brief": {},
  "runtime_smoke_compare_report": {},
  "runtime_smoke_compare_brief": {}
}
```

`runtime_smoke_brief` is the stable flattened summary consumed by `release_manifest.json`, `runtime_package.json`, `promote`, and `validate`.

`runtime_smoke_compare_report` compares the current artifact with the latest previous finalized `runtime_smoke.json` that exists in bundle snapshots. It exposes:

- `has_previous`
- `changed`
- `headline`
- `items[]`
- `changed_sections[]`
- `sections.<section>.changed`
- `sections.<section>.changed_fields[]`

`validate --require-final` treats this file as part of the final release contract:

- it must exist for `final_confirmed` bundles
- it must stay consistent with the current `runtime_package.json`
- drift surfaces in `runtime_smoke_artifact_issues[]`

## `runtime_prompt_eval.json`

Finalized bundles also write a stable prompt-eval artifact derived from the default deterministic runtime prompt eval:

```json
{
  "schema_version": "colleague_clone_runtime_prompt_eval_artifact/v1",
  "generated_at": "2026-04-08T12:30:00Z",
  "runtime_package_path": "/abs/path/to/bundle/runtime_package.json",
  "runtime_prompt_eval_report": {},
  "runtime_prompt_eval_brief": {},
  "runtime_prompt_eval_compare_report": {},
  "runtime_prompt_eval_compare_brief": {}
}
```

`runtime_prompt_eval_brief` is the stable flattened summary consumed by `release_manifest.json`, `runtime_package.json`, `promote`, and `validate`.

`runtime_prompt_eval_compare_report` compares the current artifact with the latest previous finalized `runtime_prompt_eval.json` that exists in bundle snapshots. It exposes:

- `has_previous`
- `changed`
- `headline`
- `items[]`
- `changed_sections[]`
- `sections.<section>.changed`
- `sections.<section>.changed_fields[]`

`validate --require-final` treats this file as part of the final release contract:

- it must exist for `final_confirmed` bundles
- it must stay consistent with the current `runtime_package.json`
- drift surfaces in `runtime_prompt_eval_artifact_issues[]`

## Runtime Smoke Report

`run_colleague_runtime_smoke.py` reads `runtime_package.json` and runs deterministic runtime-readiness checks without calling a model.

It returns:

- `schema_version`
- `ok`
- `headline`
- `case_count`
- `failed_cases[]`
- `issues[]`
- `cases[]`

Each item in `cases[]` includes:

- `case_id`
- `question`
- `ok`
- `checks[]`

`validate_colleague_skill.py --run-runtime-smoke` includes:

- `runtime_smoke_report`
- `runtime_smoke_summary`
- `runtime_smoke_issues[]`
- `runtime_smoke_artifact`
- `runtime_smoke_artifact_issues[]`
- `runtime_smoke_compare_report`
- `runtime_smoke_compare_brief`

When combined with `--require-final`, any smoke failure is added to `final_quality_issues[]`.

## Runtime Prompt Eval Report

`run_colleague_prompt_eval.py` reads `runtime_package.json` and produces deterministic runtime answer previews for fixed prompts without calling a model.

It also supports a `model` mode where an external executable generates answers case by case. The command contract is:

- read JSON from `stdin`
- input includes `profile`, `case`, and `runtime_package`
- return JSON with at least `answer`

It can optionally read a custom cases file:

```json
{
  "schema_version": "colleague_clone_prompt_eval_cases/v1",
  "profile": "custom_review_only",
  "cases": [
    {
      "case_id": "custom_review_gate",
      "prompt": "Review this API diff and call out the key review focus.",
      "expected_checks": ["must_include_review_focus", "must_include_workflow"],
      "severity": "high"
    }
  ]
}
```

Supported `expected_checks[]` values:

- `must_include_default_modules`
- `must_include_review_focus`
- `must_include_workflow`
- `must_refuse_and_redirect`
- `must_acknowledge_uncertainty`
- `must_include_style_signals`

It returns:

- `schema_version`
- `mode`
  - `deterministic_runtime_preview`
  - `model_runtime_eval`
- `profile`
- `case_source`
- `ok`
- `headline`
- `case_count`
- `summary`
  - `passed_count`
  - `failed_count`
  - `blocking_failures[]`
  - `caution_failures[]`
  - `informational_failures[]`
  - `score`
- `decision`
  - `decision`: `allow`, `caution`, or `block`
  - `blocking`
  - `headline`
- `failed_cases[]`
- `issues[]`
- `blocking_issues[]`
- `cases[]`

Each item in `cases[]` includes:

- `case_id`
- `prompt`
- `answer`
- `severity`
- `severity_bucket`
  - `blocking`: input `severity` is `high`, `blocking`, or `critical`
  - `caution`: input `severity` is `medium`, `caution`, `warn`, or `warning`
  - `informational`: all other values
- `expected_checks[]`
- `ok`
- `checks[]`

`summary.score` is the integer pass-rate percentage across all configured cases.

`decision.decision` is derived from failed-case severity buckets:

- `block`: at least one failed case is in the `blocking` bucket
- `caution`: no blocking failures, but at least one failed case is in the `caution` bucket
- `allow`: no blocking or caution failures

`ok` remains strict: it is `true` only when every configured case passes and a runtime package was present.

`validate_colleague_skill.py --run-prompt-eval [--prompt-eval-cases-file PATH] [--prompt-eval-mode deterministic|model]` includes:

- `runtime_prompt_eval_report`
- `runtime_prompt_eval_decision`
- `runtime_prompt_eval_summary`
- `runtime_prompt_eval_issues[]`
- `runtime_prompt_eval_blocking_issues[]`

`runtime_prompt_eval_summary` is the flattened consumption layer and includes:

- `ok`
- `mode`
- `profile`
- `case_source`
- `headline`
- `score`
- `decision`
- `failed_cases[]`
- `issues[]`

When combined with `--require-final`, only `runtime_prompt_eval_blocking_issues[]` are added to `final_quality_issues[]`.
`runtime_prompt_eval_issues[]` still contains all failed cases, including `caution` and `informational` results, for operator review.

`validate_colleague_skill.py --require-final` also consumes `runtime_release_review_issues`; any pending runtime drift acknowledgement blocks final validation.

## Inspect Report

`inspect_colleague_sources.py` returns a report like:

```json
{
  "ok": true,
  "source_count": 1,
  "sources": [
    {
      "path": "/abs/path/to/slack-export",
      "source_type": "workspace_export",
      "detection_mode": "auto",
      "detected_platform": "slack",
      "platform_detection_mode": "slack_directory_metadata",
      "platform_detection_reasons": ["found Slack metadata files in the export directory"],
      "field_coverage": {
        "text": 1.0,
        "speaker": 1.0,
        "channel": 1.0,
        "timestamp": 1.0
      },
      "missing_fields": [],
      "record_count": 42,
      "speaker_count": 5,
      "channel_count": 3,
      "sample_speakers": ["Alice Example"],
      "timestamp_range": {
        "earliest": "2026-04-07T10:00:00Z",
        "latest": "2026-04-07T12:00:00Z"
      },
      "missing_speaker_rate": 0.0,
      "missing_channel_rate": 0.0,
      "privacy_counts": {
        "work_related": 42,
        "work_adjacent": 0,
        "private_sensitive": 0
      },
      "tags": [],
      "risks": []
    }
  ]
}
```

`risk_level` is one of:

- `safe`
- `warning`
- `risky`
