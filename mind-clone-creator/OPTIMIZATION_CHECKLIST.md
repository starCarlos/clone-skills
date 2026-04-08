# Working Clone Stack Optimization Checklist

## Objective

Start Round 15 from the already-compacted success path and trim one more layer of latest-stack metadata:

1. `doctor_latest_stack` and `validate_latest_stack` still emitted `signatures:` on success even though operators can usually identify the selected coherent stack from `stack_ref` plus `release` and `rejections`.
2. Signature hashes remain useful on `explain_latest_stack`, where the operator explicitly asked for a deeper identity/coherence view.

## Round 15 Checklist

1. Drop success-path signatures from latest doctor/validate summaries
status: done
reason: on successful release-readiness scans, `doctor_latest_stack` and `validate_latest_stack` are confirmation steps, so `signatures:` was still extra scan noise after `stack_ref:` compression
done_when: successful `doctor_latest_stack` and `validate_latest_stack` summaries keep `stack_ref`, `rejections`, and `release`, but no longer include `signatures:`
outcome: `scripts/run_release_readiness.py` now suppresses success-path `signatures:` for `doctor_latest_stack` and `validate_latest_stack`, while keeping them for `explain_latest_stack`

2. Add regression coverage for latest-signature retention boundaries
status: done
reason: later summary refactors should not accidentally reintroduce signature noise on latest doctor/validate success paths or strip it from explain output where it still adds operator value
done_when: tests assert successful local/latest doctor+validate summaries omit `signatures:`, while successful `explain_latest_stack` still keeps them
outcome: `tests/test_stack_operator_flow.py` now covers both direct summary builders and integrated release-readiness output for the new latest-signature boundary

3. Update maintainer docs for the refined latest success-path policy
status: done
reason: operator docs should explain why signatures still appear in explain output but not in routine success confirmation steps
done_when: operator docs and capability index both describe that success-path signature details are now effectively explain-only in release-readiness summaries
outcome: `references/operator_playbook.md` and `references/capability_index.md` now document the Round 15 latest-signature policy

## Round 16 Checklist

1. Surface refresh hotspots in explain success-path summaries
status: done
reason: after `stack_discovery` started emitting `refresh_stats`, the operator-facing `explain_latest_stack` summary still only exposed `stack_ref` and `signatures`, so recent refresh churn remained hidden unless someone opened the full summary JSON
done_when: `scripts/run_release_readiness.py` includes a compact `refresh_hotspots:` detail for successful `explain_latest_stack` summaries, while keeping doctor/validate success paths compact
outcome: `build_explain_step_summary()` now emits one `refresh_hotspots:` line summarizing bundle/pipeline/runtime top groups, classes, and representative files

2. Add regression coverage for explain hotspot summaries
status: done
reason: the new explain-only hotspot signal should stay visible in both direct summary-builder tests and integrated release-readiness runs
done_when: tests assert `refresh_hotspots:` appears in `build_explain_step_summary()` output and in `release_report["steps"]["explain_latest_stack"]["compact_summary"]["details"]`
outcome: `tests/test_stack_operator_flow.py` now covers both the unit-level and end-to-end summary paths

3. Update operator docs for the new explain hotspot signal
status: done
reason: maintainers need to know that refresh churn can now be scanned directly from explain summaries without opening the full stack JSON
done_when: operator playbook and capability index both mention that successful `explain latest-stack` summaries now surface `refresh_hotspots:`
outcome: `references/operator_playbook.md` and `references/capability_index.md` now document the Round 16 explain-hotspot behavior

## Round 17 Checklist

1. Propagate parent refresh triggers into rebuilt child manifests
status: done
reason: bundle/pipeline refreshes were rebuilding nested artifacts, but only the parent manifest recorded the workflow-shared trigger, so pipeline/runtime refresh history understated real churn
done_when: parent refreshes append filtered propagated triggers to rebuilt child manifests whenever changed files intersect the child's `refresh_dependency_groups`
outcome: `scripts/refresh_working_clone_bundle.py` now propagates relevant workflow-shared changes into pipeline/runtime manifests, and `scripts/refresh_workflow_blueprint_pipeline.py` now propagates relevant changes into the runtime manifest

2. Centralize propagated refresh filtering in manifest helpers
status: done
reason: without a shared helper, parent/child propagation logic would drift across refresh scripts and make later refresh semantics harder to reason about
done_when: filtering by dependency groups and trigger application live in `scripts/manifest_utils.py`, and refresh scripts only orchestrate when propagation should occur
outcome: `filter_refresh_report_to_groups()` and `propagate_refresh_to_manifest()` now centralize the propagation contract

3. Add regression coverage for propagated refresh history
status: done
reason: nested refresh history and explain stats are easy to regress because rebuilds can silently reset manifests
done_when: tests verify filtered propagation at helper level and confirm `test_refresh_scripts_and_release_readiness` observes propagated child triggers plus updated explain stats
outcome: `tests/test_stack_discovery.py` and `tests/test_stack_operator_flow.py` now lock the propagated refresh behavior

## Round 18 Checklist

1. Pin one latest coherent stack per release-readiness run
status: done
reason: adjacent latest-stack steps in `run_release_readiness.py` could rediscover different but content-equivalent `/tmp/*-vN` exports, making `stack_ref` jitter across doctor/validate/explain summaries
done_when: one release-readiness run computes a single latest coherent stack summary once, then reuses it for all latest-stack steps
outcome: `scripts/run_release_readiness.py` now writes `release_pinned_latest_stack.json` and passes it into doctor/validate/explain latest-stack calls

2. Add CLI support for reusing a pinned latest summary
status: done
reason: release-readiness needed a supported way to validate/explain an already-selected latest coherent stack without rediscovery
done_when: `scripts/clone_ops.py` accepts `--stack-summary` for `doctor latest-stack`, `validate latest-stack`, and `explain latest-stack`
outcome: latest-stack commands can now reuse a precomputed summary while preserving the same validation/explain surfaces

3. Add regression coverage for latest stack_ref stability
status: done
reason: the release-readiness report should guarantee that latest doctor/validate/explain are talking about the same coherent stack within one run
done_when: tests assert the `stack_ref:` detail matches across `doctor_latest_stack`, `validate_latest_stack`, and `explain_latest_stack`
outcome: `tests/test_stack_operator_flow.py` now locks pinned latest-stack summary reuse end to end

## Round 19 Checklist

1. Prefer version-aligned cohorts inside the latest signature group
status: done
reason: the pinned latest summary removed intra-run jitter, but latest selection could still choose `bundle vN` plus `pipeline/runtime vN+1` even when a more version-aligned content-equivalent cohort already existed
done_when: `select_latest_coherent_stack_with_report()` keeps latest-content semantics across signature groups, but ranks bundle/pipeline/runtime/personal/workflow candidates inside one signature group by deterministic cohort alignment before validation
outcome: `scripts/stack_discovery.py` now groups equivalent bundle signatures and prefers the best version-aligned cohort instead of blindly taking the newest matching artifact in each category

2. Add regression coverage for mixed-version fallback boundaries
status: done
reason: latest-stack discovery is easy to regress because content-linkage and version-alignment pull in different directions
done_when: tests cover both "single bundle prefers aligned child artifacts over newer mixed ones" and "older bundle wins when it completes the best aligned signature group"
outcome: `tests/test_stack_discovery.py` now locks both aligned-cohort preference cases

3. Update maintainer docs for aligned latest-stack selection
status: done
reason: operator docs and release checklists should explain why latest-stack may intentionally choose an older bundle inside the newest signature group when that produces a cleaner cohort
done_when: capability index, operator playbook, and release readiness checklist all describe the new aligned-cohort behavior
outcome: `references/capability_index.md`, `references/operator_playbook.md`, and `RELEASE_READINESS_CHECKLIST.md` now document the Round 19 selection policy

## Round 20 Checklist

1. Split aligned freshness notes from real freshness warnings
status: done
reason: after aligned-cohort selection landed, freshness reporting could still flag an intentional version-aligned choice as if the selector had simply picked a stale artifact
done_when: `build_freshness_report()` emits `warnings` only for same-signature candidates that genuinely outrank the selected artifact, and emits `notes` when an older artifact is kept to preserve cohort alignment
outcome: `scripts/stack_discovery.py` now classifies freshness as `current` / `aligned_selection` / `stale_same_signature` / `newer_other_signatures`, and explain output can distinguish notes from warnings

2. Keep compact operator summaries explain-only for freshness notes
status: done
reason: intentional alignment notes help during explain/debug flows, but would be extra scan noise on routine doctor/validate success paths
done_when: release-readiness explain summaries surface `freshness notes:` counts when present, while doctor/validate summaries continue to omit them
outcome: `scripts/run_release_readiness.py` now includes `freshness notes:` only in `build_explain_step_summary()`

3. Add regression coverage for aligned freshness semantics
status: done
reason: the new warning/note boundary is subtle and easy to regress during later summary cleanup
done_when: tests prove aligned selection produces notes without warnings at the discovery layer, and explain summaries surface notes without leaking them into doctor/validate summaries
outcome: `tests/test_stack_discovery.py` and `tests/test_stack_operator_flow.py` now lock the aligned freshness behavior

## Round 21 Checklist

1. Replace freshness note counts with grouped status summaries
status: done
reason: `freshness notes: 4` still forced operators to open the full JSON or mentally count artifacts before they knew what was actually being aligned
done_when: release-readiness summarizes notes and warnings by freshness status plus affected artifact labels, with cohort-aligned cases rendered as `aligned_to_vN=...`
outcome: `scripts/run_release_readiness.py` now groups freshness details into compact summaries such as `same_signature_newer=...` and `aligned_to_v144=...`

2. Surface grouped freshness notes in text-mode success summaries
status: done
reason: improving only the JSON compact summary would leave the `--format text` operator path behind
done_when: successful text-mode explain summaries can keep `stack_ref`, `signatures`, grouped freshness details, and `refresh_hotspots` together when present
outcome: `select_text_details()` now allows a fourth high-priority detail when freshness or hotspot signals are present, and includes `freshness notes:` in the selection priority list

3. Add regression coverage for grouped freshness summaries
status: done
reason: this formatting logic is easy to silently regress back to plain counts during future compaction passes
done_when: tests assert exact grouped note/warning strings and confirm text-mode detail selection preserves both grouped freshness notes and refresh hotspots
outcome: `tests/test_stack_operator_flow.py` now locks the grouped freshness summary contract

## Round 22 Checklist

1. Reuse grouped freshness formatting in raw explain output
status: done
reason: `release-readiness` had moved to grouped freshness summaries, but raw `clone_ops.py explain latest-stack` still rendered old-style note/warning bullet lists
done_when: `render_stack_summary_text()` emits grouped `freshness_warnings:` / `freshness_notes:` lines using the same status labels as release-readiness
outcome: `scripts/stack_discovery.py` now owns `summarize_freshness_report()`, and both raw explain text and release-readiness consume the same formatter

2. Remove duplicate raw explain printing
status: done
reason: `run_explain_latest_stack()` printed the rendered summary once through `emit_stack_summary(..., explain=True)` and again with an explicit `print(...)`, doubling the operator output
done_when: `clone_ops.py explain latest-stack` prints a single explain body while still honoring `--summary-json`
outcome: `scripts/clone_ops.py` now writes the summary JSON without stderr explain side effects and prints the human-readable explain exactly once

3. Add regression coverage for raw explain freshness output
status: done
reason: without direct tests, raw explain formatting could drift independently from release-readiness again
done_when: tests verify `render_stack_summary_text()` emits grouped freshness lines and `clone_ops.py explain latest-stack --stack-summary ...` prints one explain body with grouped freshness notes
outcome: `tests/test_stack_discovery.py` and `tests/test_stack_operator_flow.py` now lock the raw explain behavior

## Round 23 Checklist

1. Compress raw explain candidate rejection summaries
status: done
reason: after freshness cleanup, successful raw explain output still spent vertical space on `candidate_rejections:` followed by five zero-value lines
done_when: raw explain renders candidate rejection counts as one grouped nonzero line and suppresses the section entirely when all rejection counts are zero
outcome: `scripts/stack_discovery.py` now exposes `summarize_rejection_counts()`, and `render_stack_summary_text()` only emits `candidate_rejections:` when that summary is non-empty

2. Reuse the shared rejection formatter in release-readiness
status: done
reason: keeping raw explain and release-readiness on separate rejection formatting code paths would recreate the same drift we just removed for freshness
done_when: release-readiness builds `rejections:` with the same shared rejection formatter used by raw explain
outcome: `scripts/run_release_readiness.py` now imports and reuses `summarize_rejection_counts()`

3. Add regression coverage for zero-noise raw explain output
status: done
reason: successful explain paths are easy to re-noise during future refactors
done_when: tests verify grouped nonzero rejection rendering and confirm `clone_ops.py explain latest-stack` omits `candidate_rejections:` when supplied only zero counts
outcome: `tests/test_stack_discovery.py` and `tests/test_stack_operator_flow.py` now lock the compact rejection-summary behavior

## Round 24 Checklist

1. Group raw rejected-candidate details by reason
status: done
reason: even after compressing `candidate_rejections`, raw explain could still spill several bullet lines per artifact class when candidate reports existed
done_when: `*_rejected_candidates` render as one line per artifact class, grouped by rejection reason and annotated with only a few representative candidate names
outcome: `scripts/stack_discovery.py` now exposes `summarize_rejected_candidate_reports()` and `render_stack_summary_text()` uses it instead of bullet expansion

2. Keep raw explain examples compact but still actionable
status: done
reason: operators need enough artifact names to spot the affected versions, but not the full rejection ledger inline
done_when: grouped rejection lines cap both the number of distinct reasons and the number of sample names per reason, with overflow noted as `+N`
outcome: raw explain now shows summaries like `validator failed x2 (v131,v130); missing ... x1 (v129)` instead of three separate bullets

3. Add regression coverage for grouped rejected-candidate details
status: done
reason: this is another place where later cleanup could easily regress back to verbose per-item bullet lists
done_when: tests assert grouped rejection lines in `render_stack_summary_text()` and in `clone_ops.py explain latest-stack --stack-summary ...` output
outcome: `tests/test_stack_discovery.py` and `tests/test_stack_operator_flow.py` now lock the grouped rejected-candidate detail format

## Round 25 Checklist

1. Fold repo-doc drift validation into release-readiness
status: done
reason: `validate_repo_docs.py` had become a required manual preflight, but `release-readiness` still only gated tests and stack/operator checks, leaving a drift path where docs could silently regress while the aggregate release gate stayed green
done_when: `scripts/run_release_readiness.py` runs repo-doc validation as its own first-class step and emits a compact operator summary for it
outcome: `release-readiness` now starts with `validate_repo_docs`, and its compact summary reports per-doc issue counts instead of raw validator JSON

2. Add a command-level failure quick table and maintainer first-15-minutes doc
status: done
reason: the repo had good deep docs, but operators still had to synthesize the first few commands and common failure recovery commands across multiple files
done_when: failure guidance includes copyable commands for the highest-frequency failures, and a new maintainer doc explains the first 15 minutes of onboarding
outcome: `references/failure_path_guide.md` now has direct command tables, and `references/new_maintainer_first_15_minutes.md` provides the maintainer onboarding fast path

3. Link and validate the new maintainer doc across the doc system
status: done
reason: adding a new support doc without wiring it into README/index/current-flow validators would create another drift island
done_when: README, current flow, capability index, release checklist, and repo-doc validator all know about the new maintainer doc
outcome: the new maintainer entry is now linked from the main indexes and enforced by `scripts/validate_repo_docs.py`, with regression coverage in validator and operator-flow tests

## Round 26 Checklist

1. Add a doc router for fast first-document selection
status: done
reason: after adding several support docs, readers still had to infer which file to open first from README and capability index, which increased navigation friction
done_when: the repo contains one question-driven document router that points users, workflow builders, and maintainers at the right first doc in under 30 seconds
outcome: `references/doc_router.md` now provides a question-based router plus three shortest reading paths

2. Extend repo-doc validation from existence checks to navigation and order guards
status: done
reason: doc drift was no longer just “missing links”; the larger risk became support docs existing but not being wired into the top-level navigation or the release-readiness order silently drifting
done_when: `validate_repo_docs.py` enforces the new doc router links, checks operator playbook coverage, and flags release-readiness order mismatches in the flow docs
outcome: the validator now covers `doc_router.md`, operator playbook presence requirements, and ordered release-readiness sequences for current-flow and new-maintainer docs

3. Add regression coverage for doc-router and order validation
status: done
reason: navigation and order checks are easy to weaken accidentally during later doc edits because they do not affect the runtime scripts directly
done_when: tests fail if the new router is not linked or if the maintainer/operator sequence is reordered incorrectly in fixtures
outcome: `tests/test_stack_validators.py` now covers both the new router/order validation paths and the extended doc contract

## Round 27 Checklist

1. Introduce a canonical operator command contract
status: done
reason: operator command syntax was repeated across README, playbook, onboarding, and checklist docs, so simple CLI changes still risked multi-file drift
done_when: one dedicated doc owns the exact operator command surface and lighter docs can point to it instead of repeating every full command
outcome: `references/operator_command_contract.md` now acts as the operator command single source of truth

2. Rewire navigation docs to point at the command contract
status: done
reason: adding a canonical command doc only helps if readers can reach it from the places where they currently look for operator instructions
done_when: README, doc router, current flow, capability index, operator playbook, maintainer onboarding, and release checklist all link to the command contract
outcome: the navigation layer now routes command lookups to `operator_command_contract.md`, and README no longer duplicates the full stack-entry command list

3. Extend doc validation and summaries for the command contract
status: done
reason: a new single-source doc becomes a new drift risk unless repo-doc validation and release summaries explicitly account for it
done_when: `validate_repo_docs.py` requires the command contract and its links, and `release-readiness` repo-doc summaries surface any contract drift
outcome: command-contract coverage is now enforced in repo-doc validation and visible in compact release summaries

## Round 28 Checklist

1. Generate the README operator quick-command block from the JSON source
status: done
reason: after introducing `operator_command_contract.md`, the remaining hand-maintained command syntax in README was still a last-mile drift island
done_when: the README operator quick-command block is marker-bounded and rendered directly from `references/operator_commands.json`
outcome: `README.md` now uses a generated `operator-command-quickstart` block owned by `scripts/render_operator_command_docs.py`

2. Extend repo-doc validation and release summaries to include README render drift
status: done
reason: once README becomes a generated surface, drift detection must treat it like the contract and summary docs instead of leaving it as an uncounted manual page
done_when: `validate_repo_docs.py` flags README operator render mismatch, and `release-readiness` includes that mismatch in `operator_render=...`
outcome: README render consistency is now enforced in `validate_repo_docs.py` and counted by `scripts/run_release_readiness.py`

3. Add regression coverage for README operator render drift
status: done
reason: generated README sections are easy to accidentally hand-edit unless both the renderer `--check` path and validator fixture tests fail loudly
done_when: tests fail if README drifts from the JSON source while `contract` and `summary` still match
outcome: `tests/test_stack_validators.py` and `tests/test_stack_operator_flow.py` now lock the README render contract and the aggregate operator-render count

## Round 29 Checklist

1. Generate the README operator coverage list from the JSON source
status: done
reason: after quickstart generation landed, the remaining README `其中覆盖` command-name list was still hand-maintained and could drift from the contract doc
done_when: README command coverage names are marker-bounded and rendered from `references/operator_commands.json`
outcome: README now renders both the operator quickstart block and the coverage-name block from the same JSON source

2. Extend the operator command source with short command surfaces
status: done
reason: README coverage needs concise command names like `doctor latest-stack`, not full shell lines, so the source needed a lightweight human-facing command surface field
done_when: operator command entries can provide a short display surface while contract and summary docs keep using the full shell command
outcome: `references/operator_commands.json` now includes `surface` values for operator command names used in README coverage rendering

3. Add regression coverage for README coverage-block drift
status: done
reason: once README owns two generated command sections, tests should prove drift is detected even when only the short coverage list is hand-edited
done_when: renderer `--check` and repo-doc validation both fail on a mutated README coverage entry
outcome: `tests/test_stack_validators.py` now mutates the README coverage block and confirms both drift paths fail as expected

## Round 30 Checklist

1. Generate operator playbook core command sections from the JSON source
status: done
reason: `operator_playbook.md` still hand-maintained the daily-path and release-readiness command examples, so command syntax could drift there even after README generation was fixed
done_when: the playbook daily-path and release command blocks are marker-bounded and rendered from `references/operator_commands.json`
outcome: `operator_playbook.md` now renders its core command examples from the same JSON source as README, contract, and summary

2. Generate new-maintainer command path sections from the JSON source
status: done
reason: `new_maintainer_first_15_minutes.md` is a high-traffic operator entrypoint, so its preflight and first-run command sequence should not depend on hand-edited prose
done_when: the new-maintainer preflight and operator-path command sections are marker-bounded and rendered from `references/operator_commands.json`
outcome: `new_maintainer_first_15_minutes.md` now renders both onboarding command sections from the shared operator command source

3. Extend drift validation, release summaries, and tests for the new generated docs
status: done
reason: once playbook and new-maintainer docs become generated surfaces, repo-doc validation and `operator_render=` aggregation need to count their drift too
done_when: validator/report/test coverage fails when playbook or new-maintainer generated command blocks drift from the JSON source
outcome: `validate_repo_docs.py`, `run_release_readiness.py`, `tests/test_stack_validators.py`, and `tests/test_stack_operator_flow.py` now enforce the expanded generated-doc contract

## Round 31 Checklist

1. Generate current-system-flow shortest command examples from the shared command source
status: done
reason: `current_system_flow.md` still hand-maintained the 10-command quickstart ladder, so everyday entry examples could drift from the real CLI surface
done_when: the `最短命令示例` block is marker-bounded and rendered from `references/operator_commands.json`
outcome: `current_system_flow.md` now renders its shortest command examples from the shared command source

2. Generate release-readiness checklist command items from the shared command source
status: done
reason: `RELEASE_READINESS_CHECKLIST.md` contained the highest-consequence manual command list, so release gating still depended on hand-edited CLI strings
done_when: the metadata preflight command and validation-command checklist block are marker-bounded and rendered from `references/operator_commands.json`
outcome: `RELEASE_READINESS_CHECKLIST.md` now renders its command checklist entries from the shared source

3. Extend validation and summaries for the new generated command docs
status: done
reason: once `current_system_flow.md` and `RELEASE_READINESS_CHECKLIST.md` become generated surfaces, repo-doc validation and `operator_render=` must count their drift too
done_when: validator/report/test coverage fails when either generated block drifts or loses its markers
outcome: `render_operator_command_docs.py`, `validate_repo_docs.py`, `run_release_readiness.py`, `tests/test_stack_validators.py`, and `tests/test_stack_operator_flow.py` now cover both new generated docs

## Round 32 Checklist

1. Generate the current-system-flow operator chain from the shared command source
status: done
reason: `current_system_flow.md` still hand-maintained the 8-step operator chain, so the most important maintainer path still duplicated command syntax outside the shared source
done_when: section 9 `Operator 侧流程` is marker-bounded and rendered from `references/operator_commands.json`
outcome: the operator chain in `current_system_flow.md` now renders from the shared operator command source

2. Extend the current-flow command source with operator-chain descriptions
status: done
reason: the flow doc needs explanatory step text plus exact shell commands, so the shared source needed a dedicated operator-chain item list rather than only bare command ids
done_when: `references/operator_commands.json` contains structured operator-chain items for current-system-flow rendering
outcome: `current_flow.operator_chain_items` now defines the canonical step descriptions and command bindings for the operator chain

3. Add validation and regression coverage for the generated operator chain
status: done
reason: once section 9 becomes generated, both missing markers and hand edits in that chain should fail loudly instead of silently drifting
done_when: repo-doc validation requires the new markers and tests fail if the generated operator chain is edited by hand
outcome: `validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated operator-chain block in `current_system_flow.md`

## Round 33 Checklist

1. Generate capability-index operator entrypoints from the shared command source
status: done
reason: `capability_index.md` still hand-maintained the operator entry script list, so the maintainer map duplicated canonical operator surfaces outside the shared source
done_when: the capability-index operator entry list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `capability_index.md` now renders its operator entry script list from the shared operator source

2. Generate the capability-index operator capability bullets from the shared command source
status: done
reason: the first set of operator capability bullets in `capability_index.md` mixed exact command semantics with maintainership notes, which made drift likely whenever CLI behavior changed
done_when: the operator capability bullets that describe `doctor` / `validate` / `release-readiness` semantics are marker-bounded and rendered from `references/operator_commands.json`
outcome: `capability_index.md` now renders its command-semantic operator bullets from the shared operator source

3. Extend validation and release summaries for capability-index render drift
status: done
reason: once capability-index becomes a generated command surface, repo-doc validation and `operator_render=` should count it just like README, playbook, and flow docs
done_when: validator/report/test coverage fails when the generated capability-index operator blocks drift from the shared source
outcome: `render_operator_command_docs.py`, `validate_repo_docs.py`, `run_release_readiness.py`, `tests/test_stack_validators.py`, and `tests/test_stack_operator_flow.py` now include capability-index render drift

## Round 34 Checklist

1. Generate the current-system-flow operator route text and mermaid chain from the shared source
status: done
reason: section 2 `Operator 检查链路` still duplicated the operator order in both arrow text and mermaid, even after section 9 had been generated
done_when: the operator route text and mermaid block are marker-bounded and rendered from `references/operator_commands.json`
outcome: `current_system_flow.md` now renders both the operator route overview and the detailed operator chain from the shared source

2. Reuse the same operator-chain source for route and detailed flow rendering
status: done
reason: keeping separate route-order and detailed-step sources would just recreate drift one layer deeper inside the same document
done_when: one `current_flow.operator_chain_items` source drives both the route overview block and the section 9 detailed chain
outcome: `render_operator_command_docs.py` now derives both current-flow operator blocks from the same structured operator-chain items

3. Extend validation coverage for the generated operator route block
status: done
reason: once the route text and mermaid become generated, validator and tests should fail on edits there just like they do for the other generated command blocks
done_when: repo-doc validation requires the new route markers and current-flow drift tests fail when the route block is hand-edited
outcome: `validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated operator route block in `current_system_flow.md`

## Round 35 Checklist

1. Generate the doc-router question table from the shared source
status: done
reason: `references/doc_router.md` still duplicated operator and maintainer navigation rows by hand, so command-adjacent doc routing could drift separately from the operator doc source
done_when: the `按问题找文档` table becomes marker-bounded and renders from `references/operator_commands.json`
outcome: `references/doc_router.md` now renders its question-routing table from the shared source via `scripts/render_operator_command_docs.py`

2. Generate the maintainer reading path in doc-router from the shared source
status: done
reason: the maintainer “先看哪几份”路径 is another ordered navigation list that should stay aligned with the operator entry docs without hand-maintaining two copies
done_when: the maintainer reading path is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/doc_router.md` now renders the maintainer reading path from the same shared source as the operator docs

3. Count doc-router render drift in validation and release-readiness
status: done
reason: once doc-router becomes generated, drift there should fail the same validation and release summary surfaces as README, playbook, current flow, and maintainer docs
done_when: `validate_repo_docs.py`, `run_release_readiness.py`, and regression tests all treat doc-router render mismatch as part of `operator_render`
outcome: validator/reporting code and tests now enforce `doc_router_render_mismatch`, and release-readiness summary counts it inside `operator_render=`

## Round 36 Checklist

1. Generate failure-guide release-readiness retry commands from the shared source
status: done
reason: `references/failure_path_guide.md` still hand-maintained the release-readiness retry command table even though those command variants already lived in the operator command source
done_when: the `validate release-readiness` retry table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the release-readiness retry table from the shared operator source

2. Generate failure-guide latest-stack diagnosis commands from the shared source
status: done
reason: the latest-stack diagnosis section duplicated `explain latest-stack` and `doctor latest-stack --explain` syntax in another high-traffic troubleshooting doc
done_when: the latest-stack diagnosis command table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the latest-stack diagnosis commands from the same shared source

3. Treat failure-guide drift as part of operator doc render validation
status: done
reason: once failure-guide command tables become generated, edits there should break the same render validation and release-readiness operator summary surfaces as the other operator docs
done_when: validator output, release-readiness `operator_render`, and regression tests all include `failure_guide_render_mismatch`
outcome: `scripts/validate_repo_docs.py`, `scripts/run_release_readiness.py`, `tests/test_stack_validators.py`, and `tests/test_stack_operator_flow.py` now enforce failure-guide render drift

## Round 37 Checklist

1. Generate the remaining doc-router reading paths from the shared source
status: done
reason: `references/doc_router.md` still hand-maintained the ordinary-user path, workflow path, and single-read recommendations, even after question routing and maintainer path had moved to the shared source
done_when: those three navigation blocks are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/doc_router.md` now renders all high-frequency reading paths from the shared navigation source

2. Generate the new-maintainer map-reading order from the shared source
status: done
reason: the first 0-5 minute reading sequence in `references/new_maintainer_first_15_minutes.md` is ordered navigation and should stay aligned with the doc-router / operator entry docs without manual duplication
done_when: the opening reading order is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/new_maintainer_first_15_minutes.md` now renders its opening map-reading sequence from the shared source

3. Extend validation and regression coverage for the new navigation blocks
status: done
reason: once these reading paths become generated, marker presence and render drift should fail just like the other generated operator/navigation blocks
done_when: validator required patterns include the new markers, and regression tests fail when the new generated navigation blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the new doc-router and new-maintainer generated blocks

## Round 38 Checklist

1. Generate the operator-playbook refresh entry block from the shared source
status: done
reason: the `Refresh 入口` section in `references/operator_playbook.md` still hand-maintained three canonical refresh commands even though they belong to the same shared operator/workflow command surface
done_when: the refresh entry block is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/operator_playbook.md` now renders its refresh entry commands from the shared source

2. Add the workflow runtime refresh command to the shared command source
status: done
reason: the playbook refresh section referenced `refresh_workflow_runtime_bundle.py`, but that command had not yet been modeled in `references/operator_commands.json`
done_when: runtime refresh has a canonical shared command entry that can be reused by generated docs
outcome: `references/operator_commands.json` now includes `workflow_runtime_refresh` and uses it in the playbook refresh block

3. Extend validation and regression coverage for the generated refresh block
status: done
reason: once the refresh section becomes generated, marker presence and render drift there should fail the same repo-doc checks as the other generated playbook blocks
done_when: validator required patterns include the new refresh markers and tests fail on manual edits inside the generated refresh block
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated playbook refresh block

## Round 39 Checklist

1. Generate the workflow-blocker refresh table in failure-guide from the shared source
status: done
reason: the workflow blocker section in `references/failure_path_guide.md` still hand-maintained the bundle/pipeline refresh commands even though both were already modeled in the shared operator/workflow command source
done_when: the workflow blocker command table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the workflow blocker refresh table from the shared source

2. Generate the workflow-blueprint diagnosis table in failure-guide from the shared source
status: done
reason: the blueprint failure section duplicated both `validate workflow-blueprint` and pipeline refresh syntax, and needed a shared-source version that keeps the guide generic instead of hardcoding the release sample path
done_when: the blueprint diagnosis table is marker-bounded and rendered from `references/operator_commands.json` using a generic blueprint validation command surface
outcome: `references/operator_commands.json` now includes `blueprint_validate_generic`, and `references/failure_path_guide.md` renders the blueprint diagnosis table from shared data

3. Extend failure-guide validation coverage for the generated workflow tables
status: done
reason: once the workflow tables become generated, edits there should trigger the same failure-guide render drift checks as the release/operator tables
done_when: validator required patterns include the new workflow markers, and tests fail when those generated workflow tables are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated workflow tables in `failure_path_guide.md`

## Round 40 Checklist

1. Generate the failure-guide quick-reference table from the shared source
status: done
reason: section 4 “常用失败命令速查” still hand-maintained a mixed navigation-and-command table that duplicated failure symptoms, inspection targets, and canonical commands already represented elsewhere in the workflow/operator docs
done_when: the quick-reference table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the entire quick-reference table from shared data

2. Model quick-reference rows as structured failure-guide data
status: done
reason: only extracting the command column would still leave the problem and inspection columns hand-maintained, recreating drift inside the same table
done_when: the shared source stores `problem`, `inspect`, and `command_id` for each quick-reference row, with generic blueprint validation kept separate from the release sample path
outcome: `references/operator_commands.json` now contains structured `quick_reference_rows`, and the renderer composes the whole table from that data

3. Extend validation and regression coverage for the generated quick-reference table
status: done
reason: once the quick-reference table becomes generated, edits there should fail the same failure-guide render drift checks as the other generated troubleshooting blocks
done_when: validator required patterns include the new quick-reference markers, and tests fail when the generated table is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated quick-reference block

## Round 41 Checklist

1. Generate the current-system-flow entry selection table from the shared source
status: done
reason: section 6 “常见入口选择” still hand-maintained a high-traffic script routing table even after the shortest command examples and operator chains had moved to the shared source
done_when: the entry selection table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders its section 6 entry selection table from shared data

2. Add runtime refresh to the current-flow entry model and shortest examples
status: done
reason: section 6 previously covered bundle refresh and pipeline refresh but omitted the runtime refresh path, even though the repo already had `refresh_workflow_runtime_bundle.py` and section 8 treated the runtime manifest as a refresh anchor
done_when: the shared current-flow data includes a runtime refresh entry row and a shortest command example for `refresh_workflow_runtime_bundle.py`
outcome: current-flow docs now expose runtime refresh consistently in both the entry selection table and the shortest example list

3. Extend validation and regression coverage for the generated current-flow entry table
status: done
reason: once the entry selection table becomes generated, marker presence and render drift there should fail the same repo-doc checks as the other generated current-flow blocks
done_when: validator required patterns include the new entry-choice markers and tests fail when the generated current-flow entry block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated current-flow entry table

## Round 42 Checklist

1. Generate the workflow/runtime file quick-reference rows in current-system-flow from the shared source
status: done
reason: section 8 “关键文件速查” still hand-maintained the most drift-prone workflow/runtime continuation rows, even though those files are tightly coupled to the same refresh/run entrypoints already modeled elsewhere
done_when: the workflow/runtime subset of section 8 is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders its workflow/runtime quick-reference rows from shared data while leaving the surrounding persona and sample context intact

2. Model workflow/runtime quick-reference rows as structured current-flow data
status: done
reason: only sharing the command names would still leave file names, locations, provenance, and next-step semantics duplicated in the doc
done_when: the shared source stores `file`, `location`, `writer`, `meaning`, and `next_step` for the workflow/runtime continuation rows
outcome: `references/operator_commands.json` now contains structured `workflow_file_rows` for section 8

3. Extend validation and regression coverage for the generated workflow/runtime file block
status: done
reason: once these quick-reference rows become generated, edits there should fail the same current-flow render-drift checks as the other generated blocks
done_when: validator required patterns include the new section 8 markers, and tests fail when the generated workflow/runtime file block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated section 8 workflow/runtime block

## Round 43 Checklist

1. Generate the workflow pipeline resume bullets in current-system-flow from the shared source
status: done
reason: section 7 “### B. Workflow pipeline” still hand-maintained the refresh/runtime handoff bullets even though both commands were already modeled in `references/operator_commands.json`
done_when: the pipeline resume bullets are marker-bounded and rendered from the shared operator/workflow source
outcome: `references/current_system_flow.md` now renders the workflow pipeline “怎么续跑” block from shared data

2. Generate the workflow runtime resume bullets in current-system-flow from the shared source
status: done
reason: section 7 “### C. Workflow runtime” still hand-maintained the runtime refresh/single-turn/until-stop continuation commands, creating another drift-prone command list in a high-traffic doc
done_when: the runtime resume bullets are marker-bounded and rendered from the shared operator/workflow source
outcome: `references/current_system_flow.md` now renders the workflow runtime “怎么续跑” block from shared data

3. Extend validation and regression coverage for the generated section 7 resume blocks
status: done
reason: once the new section 7 continuation blocks become generated, marker presence and render drift there should fail the same repo-doc and current-flow checks as the other shared-source sections
done_when: validator required patterns include the new current-flow resume markers, and tests fail when the generated pipeline/runtime resume blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both generated section 7 resume blocks; verification stayed green through render check, repo-doc validation, `72` tests, and release-readiness with `operator_render=0`

## Round 44 Checklist

1. Generate the persona bundle resume bullets in current-system-flow from the shared source
status: done
reason: section 7 “### A. 人格层 bundle” still hand-maintained the bundle refresh and run-until-final continuation commands even though both were already canonical operator/workflow command entries
done_when: the persona resume bullets are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders the persona bundle “怎么续跑” block from shared data

2. Consolidate current-flow resume rendering behind a shared helper
status: done
reason: persona, pipeline, and runtime resume blocks all used the same described-bullet rendering pattern, so keeping separate near-identical helpers would grow maintenance cost each time section 7 expands
done_when: the current-flow resume renderer has one shared helper that powers persona/pipeline/runtime blocks
outcome: `scripts/render_operator_command_docs.py` now uses a common `render_current_flow_described_block(...)` path for section 7 generated resume blocks

3. Extend validation and regression coverage for the generated persona resume block
status: done
reason: once the persona resume block becomes generated, marker presence and render drift there should fail the same current-flow checks as the other section 7 generated blocks
done_when: validator required patterns include the persona resume markers, and tests fail when the generated persona resume block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the persona resume block; verification stayed green through render check, repo-doc validation, `73` tests, and release-readiness with `operator_render=0`

## Round 45 Checklist

1. Generate the persona file quick-reference table in current-system-flow from the shared source
status: done
reason: section 8 “关键文件速查” still hand-maintained the entire persona-layer file table even though those rows are structured provenance/path/next-step data and drift just as easily as the workflow/runtime rows
done_when: the persona file table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders the persona-layer file quick-reference table from shared data

2. Generalize current-flow file-row rendering so persona/workflow tables share one path
status: done
reason: once section 8 contains multiple generated file tables, keeping a workflow-only renderer would duplicate the same table logic for every additional block
done_when: a shared current-flow file-row renderer powers both persona and workflow table blocks
outcome: `scripts/render_operator_command_docs.py` now uses one reusable file-table render path for section 8 generated blocks

3. Extend validation and regression coverage for the generated persona file table
status: done
reason: once the persona file table becomes generated, marker presence and hand edits there should fail the same current-flow drift checks as the existing workflow/runtime table
done_when: validator required patterns include the persona file markers, and tests fail when the generated persona file table is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the persona file table; verification stayed green through render check, repo-doc validation, `74` tests, and release-readiness with `operator_render=0`

## Round 46 Checklist

1. Generate the operator/sample file quick-reference table in current-system-flow from the shared source
status: done
reason: section 8 still had one hand-maintained operator/sample file table row, which prevented the whole file-quick-reference area from living on the same shared-source path
done_when: the operator/sample file table is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders the operator/sample file quick-reference table from shared data

2. Reuse the section 8 generic file-table renderer for operator/sample rows
status: done
reason: once operator/sample rows joined persona/workflow rows, section 8 needed to prove the shared file-table renderer could scale beyond the first two blocks without duplicating logic again
done_when: the generic current-flow file-table renderer drives persona, workflow, and operator/sample table blocks
outcome: `scripts/render_operator_command_docs.py` now reuses the same table renderer across all generated section 8 file tables

3. Extend validation and regression coverage for the generated operator/sample file table
status: done
reason: once the operator/sample table becomes generated, marker presence and hand edits there should fail the same current-flow drift checks as the other section 8 tables
done_when: validator required patterns include the operator file markers, and tests fail when the generated operator/sample table is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the operator/sample file table; verification stayed green through render check, repo-doc validation, `75` tests, and release-readiness with `operator_render=0`

## Round 47 Checklist

1. Generate the operator/release resume bullets in current-system-flow from the shared source
status: done
reason: section 7 “### D. Operator / release” still hand-maintained the final resume block, leaving section 7 partially outside the shared-source command model even after persona/pipeline/runtime resumes had been centralized
done_when: the operator/release resume bullets are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders the operator/release “怎么续跑” block from shared data

2. Add generic operator/release continuation command surfaces to the shared source
status: done
reason: this doc section intentionally used high-level continuation surfaces like `doctor / validate / explain` rather than a single concrete shell command, so the shared source needed dedicated generic operator/release entries instead of reusing a sample-path-specific command
done_when: `references/operator_commands.json` contains separate generic entries for partial operator checks and release-readiness continuation
outcome: the shared operator command source now models both `doctor / validate / explain` and `validate release-readiness` as reusable generic continuation surfaces for docs

3. Extend validation and regression coverage for the generated operator/release resume block
status: done
reason: once the operator/release resume block becomes generated, marker presence and hand edits there should fail the same current-flow render-drift checks as the other section 7 blocks
done_when: validator required patterns include the operator resume markers, and tests fail when the generated operator/release resume block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the operator/release resume block; verification stayed green through render check, repo-doc validation, `76` tests, and release-readiness with `operator_render=0`

## Round 48 Checklist

1. Generate the section 7 stop-point lists in current-system-flow from the shared source
status: done
reason: even after all section 7 resume paths were centralized, the persona/pipeline/runtime/operator “常见停点” lists were still hand-maintained state summaries in the repo’s highest-traffic system map
done_when: all four section 7 stop-point lists are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/current_system_flow.md` now renders every section 7 stop-point list from shared data

2. Add a reusable current-flow literal-block renderer for non-command status bullets
status: done
reason: section 7 stop points are structured prose bullets rather than command invocations, so they needed a shared render path distinct from the described-command renderer while still using the same marker-bounded generation model
done_when: current-flow stop-point blocks render through one shared literal/text bullet helper
outcome: `scripts/render_operator_command_docs.py` now uses a reusable literal-block renderer for the generated section 7 stop-point blocks

3. Extend validation and regression coverage for the generated section 7 stop-point blocks
status: done
reason: once the stop-point lists become generated, missing markers and hand edits there should fail the same current-flow drift checks as the section 7 resume blocks and section 8 tables
done_when: validator required patterns include the four stop-point markers, and tests fail when the generated stop-point blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated section 7 stop-point blocks; verification stayed green through render check, repo-doc validation, `78` tests, and release-readiness with `operator_render=0`

## Round 49 Checklist

1. Generate the runtime continuation commands in failure-guide from the shared source
status: done
reason: the `runtime 停在人工介入` section in `references/failure_path_guide.md` still hand-maintained the exact continuation commands even though the repo already modeled the same runtime turn/until-stop command surfaces centrally
done_when: the runtime continuation commands are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders its runtime continuation block from shared data

2. Reuse existing workflow runtime command surfaces inside failure-guide
status: done
reason: this troubleshooting path should not fork a second ad hoc runtime command syntax when the canonical runtime turn/continuous-run commands are already defined in the operator/workflow source
done_when: failure-guide runtime recovery references the shared `workflow_turn_run` and `workflow_until_stop` command entries
outcome: the failure-guide runtime recovery path now reuses the canonical runtime command surfaces instead of hardcoding them in prose

3. Extend validation and regression coverage for the generated failure-guide runtime block
status: done
reason: once the runtime continuation block becomes generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the workflow-blocker, blueprint, release, latest-stack, and quick-reference blocks
done_when: validator required patterns include the runtime command markers, and tests fail when the generated runtime block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the generated failure-guide runtime block; verification stayed green through render check, repo-doc validation, `79` tests, and release-readiness with `operator_render=0`

## Round 50 Checklist

1. Generate the personal-empty recovery command in failure-guide from the shared source
status: done
reason: the `personal_interview.md` empty-state section still hardcoded the bundle refresh command in prose even though that continuation path was already canonical elsewhere in the shared command source
done_when: the personal-empty recovery command is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the personal-empty recovery command from shared data

2. Generate the stage-confirmation recovery command in failure-guide from the shared source
status: done
reason: the `stage_confirmation.md` unfinished-state section still hand-maintained the pipeline refresh hint in prose, creating another one-off copy of an already canonical workflow recovery command
done_when: the stage-confirmation recovery command is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the stage-confirmation recovery command from shared data

3. Extend validation and regression coverage for the new failure-guide recovery blocks
status: done
reason: once these two recovery hints become generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the other generated troubleshooting blocks
done_when: validator required patterns include the personal-empty and stage-confirmation command markers, and tests fail when those generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both new failure-guide recovery blocks; verification stayed green through render check, repo-doc validation, `81` tests, and release-readiness with `operator_render=0`

## Round 51 Checklist

1. Generate the NEXT_INTERVIEW_UPDATE recovery command in failure-guide from the shared source
status: done
reason: the `NEXT_INTERVIEW_UPDATE.md` troubleshooting section still ended with a prose-only “refresh working bundle” hint even though that recovery command was already canonical and reused by adjacent personal-layer failure paths
done_when: the NEXT_INTERVIEW_UPDATE recovery command is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the NEXT_INTERVIEW_UPDATE recovery command from shared data

2. Generate the eval-report-draft recovery command in failure-guide from the shared source
status: done
reason: the `eval_report.md` draft troubleshooting section still hand-maintained the bundle refresh action in prose, creating another copy of the same canonical personal-layer recovery command
done_when: the eval-report-draft recovery command is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the eval-report-draft recovery command from shared data

3. Extend validation and regression coverage for the new personal-layer failure-guide blocks
status: done
reason: once these personal-layer recovery hints become generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the runtime, workflow-blocker, blueprint, release, latest-stack, and quick-reference blocks
done_when: validator required patterns include the NEXT_INTERVIEW_UPDATE and eval-draft command markers, and tests fail when those generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both new personal-layer failure-guide blocks; verification stayed green through render check, repo-doc validation, `83` tests, and release-readiness with `operator_render=0`

## Round 52 Checklist

1. Generate the workflow-blocker next-step bullets in failure-guide from the shared source
status: done
reason: the `target_work_unit` blocker section still hardcoded a prose bullet naming `refresh_workflow_blueprint_pipeline.py` and `refresh_working_clone_bundle.py`, duplicating the same recovery choices already listed again in the generated command table below
done_when: the workflow-blocker next-step bullet list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the workflow-blocker next-step list from shared data and avoids command duplication in prose

2. Generate the stage-confirmation next-step bullets in failure-guide from the shared source
status: done
reason: the `stage_confirmation.md` unfinished-state section still hand-maintained its structured next-step bullet list in prose even after the actual recovery command had been centralized
done_when: the stage-confirmation next-step bullet list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the stage-confirmation next-step list from shared data

3. Extend validation and regression coverage for the new failure-guide next-step text blocks
status: done
reason: once these next-step lists become generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the command blocks already do
done_when: validator required patterns include the workflow-blocker-next-steps and stage-confirmation-next-steps markers, and tests fail when those generated text blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both new failure-guide next-step text blocks; verification stayed green through render check, repo-doc validation, `85` tests, and release-readiness with `operator_render=0`

## Round 53 Checklist

1. Generate the blueprint inspect list in failure-guide from the shared source
status: done
reason: the `workflow_blueprint.md` failure section still embedded the blueprint validation command directly inside its “先看” list even though the exact command already appeared again in the generated command table below
done_when: the blueprint inspect list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the blueprint inspect list from shared data and removes the inline command duplication

2. Generate the latest-stack inspect list in failure-guide from the shared source
status: done
reason: the `doctor latest-stack / validate latest-stack` failure section still embedded the explain command directly in its “先看” list even though that command was already modeled and rendered again in the generated latest-stack command block
done_when: the latest-stack inspect list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the latest-stack inspect list from shared data and keeps the actual explain command only in the generated command block

3. Extend validation and regression coverage for the new failure-guide inspect blocks
status: done
reason: once these inspect lists become generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the other generated troubleshooting blocks
done_when: validator required patterns include the blueprint-inspect and latest-stack-inspect markers, and tests fail when those generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both new failure-guide inspect blocks; verification stayed green through render check, repo-doc validation, `87` tests, and release-readiness with `operator_render=0`

## Round 54 Checklist

1. Generate the release-readiness inspect list in failure-guide from the shared source
status: done
reason: the `validate release-readiness` troubleshooting section still hand-maintained the exact artifact checklist to inspect first, even though that recovery surface belongs with the rest of the shared failure-guide model
done_when: the release-readiness inspect list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the release-readiness inspect list from shared data

2. Generate the release-readiness next-step order in failure-guide from the shared source
status: done
reason: the numbered follow-up sequence after a release-readiness failure still lived as prose-only instructions, leaving one of the most order-sensitive troubleshooting paths outside the render/validation loop
done_when: the release-readiness next-step sequence is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the release-readiness ordered recovery path from shared data

3. Generate the latest-stack next-step list in failure-guide from the shared source
status: done
reason: the `doctor latest-stack / validate latest-stack` troubleshooting section still kept its decision bullets hand-written even after its inspect list and command table had already been centralized
done_when: the latest-stack next-step list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the latest-stack decision bullets from shared data

4. Extend validation and regression coverage for the new release/latest failure-guide text blocks
status: done
reason: once these remaining troubleshooting lists become generated, missing markers and hand edits there should fail the same render-drift checks as the other failure-guide blocks
done_when: validator required patterns include the release-inspect, release-next-steps, and latest-stack-next-steps markers, and tests fail when those generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce all three new failure-guide blocks; verification stayed green through render check, repo-doc validation, `90` tests, and release-readiness with `operator_render=0`

## Round 55 Checklist

1. Generate the remaining personal-layer inspect and next-step lists in failure-guide from the shared source
status: done
reason: the `personal_interview.md` empty-state, `NEXT_INTERVIEW_UPDATE.md`, and `eval_report.md` troubleshooting sections still kept their `先看 / 下一步` bullets hand-written even after their recovery commands had already been centralized
done_when: those personal-layer inspect and next-step lists are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the personal-empty, next-interview, and eval-draft inspect/next-step lists from shared data

2. Generate the remaining workflow-layer inspect, reason, and next-step lists in failure-guide from the shared source
status: done
reason: the `target_work_unit` blocker, `stage_confirmation.md`, `workflow_blueprint.md`, and runtime troubleshooting sections still contained structured prose lists that were ideal candidates for the same render/validation path
done_when: the workflow-blocker inspect list, stage-confirmation inspect list, blueprint reasons list, blueprint next-step list, runtime inspect list, and runtime next-step list are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders those remaining workflow-layer troubleshooting lists from shared data

3. Extend validation and regression coverage for the new failure-guide generated blocks
status: done
reason: once the remaining structured troubleshooting prose becomes generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the older generated sections
done_when: validator required patterns include all newly added failure-guide markers, and tests fail when the new inspect/next-step/reason blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the new blocks; verification stayed green through render check, repo-doc validation, `92` tests, and release-readiness with `operator_render=0`

## Round 56 Checklist

1. Generate the final reading-order list in failure-guide from the shared source
status: done
reason: the last remaining structured list in `failure_path_guide.md` was the “只想快速定位最近失败”建议顺序 section, which still duplicated explicit doc links and ordering logic outside the shared render source
done_when: the reading-order list is marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/failure_path_guide.md` now renders the final reading-order list from shared data

2. Extend validation and regression coverage for the generated reading-order block
status: done
reason: once the last structured list becomes generated, missing markers and hand edits there should fail the same failure-guide render-drift checks as the rest of the document
done_when: validator required patterns include the reading-order markers, and tests fail when the generated reading-order block is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the reading-order block; verification stayed green through render check, repo-doc validation, `93` tests, and release-readiness with `operator_render=0`

## Round 57 Checklist

1. Generate the remaining structured bullets in new-maintainer from the shared source
status: done
reason: `new_maintainer_first_15_minutes.md` still hand-maintained its map-goals list, operator confirmation checklist, failure-handling bullets, and final “15 分钟后你应该已经知道” summary even though these are stable structured guidance blocks
done_when: those remaining structured bullets are marker-bounded and rendered from `references/operator_commands.json`
outcome: `references/new_maintainer_first_15_minutes.md` now renders its remaining structured guidance blocks from shared data

2. Extend validation and regression coverage for the new new-maintainer generated blocks
status: done
reason: once the remaining new-maintainer bullet lists become generated, missing markers and hand edits there should fail the same render-drift checks as the earlier map/preflight/operator-path blocks
done_when: validator required patterns include the new marker pairs, and tests fail when the new generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the new new-maintainer blocks; verification stayed green through render check, repo-doc validation, `95` tests, and release-readiness with `operator_render=0`

## Round 58 Checklist

1. Generate the shared release/latest-stack behavior notes into operator_playbook from one shared source
status: done
reason: `operator_playbook.md` still hand-maintained a long block of release/latest-stack semantics that was highly drift-prone and partially duplicated in `capability_index.md`
done_when: the shared release/latest-stack behavior notes are marker-bounded in `operator_playbook.md` and rendered from `references/operator_commands.json`
outcome: `references/operator_playbook.md` now renders the long release/latest-stack behavior block from shared data

2. Reuse the same shared release/latest-stack behavior notes in capability_index
status: done
reason: `capability_index.md` had a near-duplicate “最近增强” list describing the same operator semantics, so the two docs needed a single truth for those overlapping bullets
done_when: the overlapping recent-release behavior bullets in `capability_index.md` are marker-bounded and rendered from the same shared array used by `operator_playbook.md`
outcome: `references/capability_index.md` now reuses the same shared release/latest-stack behavior lines as `references/operator_playbook.md`

3. Extend validation and regression coverage for the new playbook/capability shared blocks
status: done
reason: once the new shared behavior blocks become generated, marker loss or hand edits there should fail the same render-drift checks as the rest of the generated docs
done_when: validator required patterns include the new playbook/capability markers, and tests fail when those generated blocks are hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce both blocks; verification stayed green through render check, repo-doc validation, `97` tests, and release-readiness with `operator_render=0`

## Round 59 Checklist

1. Generate the operator handoff checklist block in RELEASE_READINESS_CHECKLIST from the structured source
status: done
reason: the long “Operator Handoff” acceptance checklist in `RELEASE_READINESS_CHECKLIST.md` was still a large hand-maintained structured block and one of the last obvious drift surfaces in the release docs
done_when: the operator handoff checklist items are marker-bounded and rendered from `references/operator_commands.json`
outcome: `RELEASE_READINESS_CHECKLIST.md` now renders its operator handoff checklist from shared data

2. Extend validation and regression coverage for the generated release checklist handoff block
status: done
reason: once the handoff checklist becomes generated, marker loss or hand edits there should fail the same release-checklist render-drift checks as the metadata and validation command blocks
done_when: validator required patterns include the handoff markers, and tests fail when the generated handoff checklist is hand-edited
outcome: `scripts/validate_repo_docs.py` and `tests/test_stack_validators.py` now enforce the handoff block; verification stayed green through render check, repo-doc validation, `98` tests, and release-readiness with `operator_render=0`

## Round 60 Checklist

1. Centralize repeated document paths in the operator doc source
status: done
reason: `references/operator_commands.json` still repeated the same doc paths across `new_maintainer`, `doc_router`, and `failure_guide`, so even the shared source had started accumulating path-level drift risk
done_when: repeated doc paths resolve through one shared `doc_refs` map while existing render output stays unchanged
outcome: `references/operator_commands.json` now defines `doc_refs`, and the renderer resolves shared doc aliases across onboarding, router, and failure-guide sections

2. Centralize repeated inspect file literals in the operator doc source
status: done
reason: the same inspect targets such as `workflow_interview.md`, `stage_confirmation.md`, and `eval_report.md` were duplicated between `current_flow` file tables and `failure_guide` troubleshooting lists
done_when: repeated inspect targets resolve through one shared `inspect_refs` map without changing generated docs
outcome: `references/operator_commands.json` now defines `inspect_refs`, and both `current_flow` and `failure_guide` reuse those shared inspect aliases

3. Add regression coverage for broken doc/inspect aliases
status: done
reason: once alias indirection exists in the shared source, future edits need fast failures when a `doc_ref` or `inspect_ref` key drifts or is misspelled
done_when: tests fail with explicit errors when `operator_commands.json` contains an unknown `doc_ref` or `inspect_ref`
outcome: `tests/test_stack_validators.py` now covers both invalid alias cases; verification stayed green through render check, repo-doc validation, `100` tests, and release-readiness with `operator_render=0`

## Round 61 Checklist

1. Add one shared block-application helper to the operator doc renderer
status: done
reason: `scripts/render_operator_command_docs.py` still repeated long chains of `replace_marked_block(...)` calls, making each new generated block more expensive to wire in and easier to misorder
done_when: the renderer applies multi-block updates through one shared helper instead of ad hoc nested replacement chains
outcome: `scripts/render_operator_command_docs.py` now exposes `apply_render_blocks()` and uses it for generated doc updates

2. Convert the large generated-doc renderers to declarative block plans
status: done
reason: the highest-churn renderers (`README`, `operator_playbook`, `new_maintainer`, `release_checklist`, `current_flow`, `capability_index`, `doc_router`, `failure_guide`) carried the most repetitive replacement boilerplate
done_when: those renderers describe their generated sections as ordered block plans while preserving identical output
outcome: the major renderer entrypoints now use ordered block lists instead of long imperative replacement ladders

3. Re-verify that the renderer refactor is output-preserving
status: done
reason: this round is pure maintainability work, so the only acceptable outcome is identical generated docs and green validation
done_when: render check, repo-doc validation, validator tests, and release-readiness all stay green after the refactor
outcome: verification stayed green through `render_operator_command_docs.py`, `--check`, `validate_repo_docs.py`, `64` validator tests, and release-readiness with `operator_render=0`
