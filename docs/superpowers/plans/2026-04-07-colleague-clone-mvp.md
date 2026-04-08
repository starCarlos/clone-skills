# Colleague Clone MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first working vertical slice for `colleague-clone`, covering routing, skill skeleton, bundle initialization, and source normalization for local text-like files.

**Architecture:** Keep the MVP schema-first and file-based. Route clone intent at the root, add a dedicated `colleague-clone` skill with its own scripts, and implement a minimal bundle pipeline that writes `sources/`, `normalized/`, and `meta.json` without introducing live connectors or workflow runtime integration.

**Tech Stack:** Markdown skills, Python 3 standard library, `unittest`

---

### Task 1: Route And Skeleton

**Files:**
- Modify: `SKILL.md`
- Create: `colleague-clone/SKILL.md`
- Create: `colleague-clone/references/design.md`
- Create: `colleague-clone/references/schemas.md`

- [ ] Add `colleague-clone` to the root router and fast decision rules.
- [ ] Create the new skill entrypoint and reference docs.
- [ ] Keep the skill boundary narrow: local materials, persona/work split, draft-first flow.
- [ ] Commit.

### Task 2: Bundle Init

**Files:**
- Create: `colleague-clone/scripts/colleague_clone_common.py`
- Create: `colleague-clone/scripts/init_colleague_intake.py`

- [ ] Implement slug generation, JSON/JSONL helpers, and intake YAML rendering helpers.
- [ ] Implement bundle initialization for `sources/`, `normalized/`, `analysis/`, and `versions/`.
- [ ] Write `meta.json`, `sources/intake_request.yaml`, and `sources/manifest.jsonl`.
- [ ] Commit.

### Task 3: Normalize Local Sources

**Files:**
- Modify: `colleague-clone/scripts/colleague_clone_common.py`
- Create: `colleague-clone/scripts/normalize_colleague_sources.py`

- [ ] Support local markdown, text, and pasted-text style sources from the manifest.
- [ ] Normalize each source into a standard record with title, text, confidence, and privacy scope.
- [ ] Rewrite the manifest with normalization status and output paths.
- [ ] Update `meta.json` state after normalization.
- [ ] Commit.

### Task 4: Tests

**Files:**
- Create: `colleague-clone/tests/test_init_and_normalize.py`

- [ ] Add a CLI test for bundle initialization.
- [ ] Add a CLI test for local markdown/text normalization.
- [ ] Run: `python3 -m unittest discover -s colleague-clone/tests -v`
- [ ] Commit.

### Task 5: Verification

**Files:**
- Modify: `COLLEAGUE_CLONE_CHECKLIST.md`

- [ ] Update the checklist to reflect the completed MVP slice.
- [ ] Run the tests again and confirm green output.
- [ ] Commit the implementation batch.
