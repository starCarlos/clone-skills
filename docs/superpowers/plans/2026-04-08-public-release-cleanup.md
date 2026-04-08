# Public Release Cleanup Checklist

**Goal:** Prepare `clone-skills` for a reasonable first public push by removing tracked local runtime artifacts, aligning public docs with the actual repository state, and verifying the resulting tree is clean.

## Scope

- [x] Create a protection commit before any destructive cleanup
- [x] Remove tracked local runtime and e2e artifacts from the public tree
- [x] Keep ignore rules aligned so these files do not come back
- [x] Update public-facing docs to match the cleaned repository state
- [x] Verify git status, tracked artifact search, and core repo checks
- [x] Decide whether current history is acceptable or whether a clean public-history export is still needed

## Notes

- Current risk is not code correctness. It is public packaging hygiene.
- `.codex-e2e-*`, `.e2e-logs`, sqlite files, session logs, and similar local artifacts should not be in the published repository.
- Current `main` is cleaner than before but still carries older private extraction history.
- The first public push should use the single-commit `public-main` branch instead of `main`.
