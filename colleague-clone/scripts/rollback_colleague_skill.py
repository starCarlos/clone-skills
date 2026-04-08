from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from colleague_clone_common import load_json, load_jsonl, utc_now_iso, write_jsonl
from update_colleague_skill import append_version_history, snapshot_bundle


RESTORE_TARGETS = [
    "meta.json",
    "persona.md",
    "work.md",
    "SKILL.md",
    "evidence_index.jsonl",
    "release_manifest.json",
    "runtime_package.json",
    "runtime_smoke.json",
    "runtime_release_health.json",
    "runtime_prompt_eval.json",
    "analysis",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollback a colleague-clone bundle to a previous snapshot.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to rollback.")
    parser.add_argument("--version", required=True, help="Snapshot version to restore, such as v1.")
    return parser.parse_args()


def restore_snapshot(bundle_dir: Path, snapshot_dir: Path) -> None:
    for relative in RESTORE_TARGETS:
        source = snapshot_dir / relative
        if not source.exists():
            continue
        target = bundle_dir / relative
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    versions_dir = bundle_dir / "versions"
    target_snapshot = versions_dir / args.version
    if not target_snapshot.exists():
        raise SystemExit(f"snapshot not found: {target_snapshot}")

    backup_snapshot = snapshot_bundle(bundle_dir)
    restore_snapshot(bundle_dir, target_snapshot)

    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    meta["updated_at"] = utc_now_iso()
    meta["rollback"] = {
        "restored_version": args.version,
        "backup_snapshot": str(backup_snapshot),
        "rolled_back_at": utc_now_iso(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    append_version_history(
        bundle_dir,
        {
            "updated_at": utc_now_iso(),
            "rollback_to": args.version,
            "backup_snapshot": str(backup_snapshot),
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "restored_version": args.version,
                "backup_snapshot": str(backup_snapshot),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
