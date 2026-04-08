from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_release_compare_report,
    load_json,
    load_previous_release_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare a finalized colleague-clone release against the previous release package.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to compare.")
    parser.add_argument("--previous-release-manifest", default="", help="Optional explicit previous release_manifest.json path.")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    current_manifest_path = bundle_dir / "release_manifest.json"
    if not current_manifest_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "bundle_dir": str(bundle_dir),
                    "issue": "current release manifest does not exist",
                },
                ensure_ascii=False,
            )
        )
        return 1

    current_manifest = load_json(current_manifest_path)
    if args.previous_release_manifest:
        previous_manifest_path = Path(args.previous_release_manifest).expanduser().resolve()
        previous_manifest = load_json(previous_manifest_path) if previous_manifest_path.exists() else {}
        previous_manifest_path_str = str(previous_manifest_path) if previous_manifest_path.exists() else ""
    else:
        previous_manifest, previous_manifest_path_str = load_previous_release_manifest(bundle_dir)

    report = {
        "ok": True,
        "bundle_dir": str(bundle_dir),
        "current_release_manifest": str(current_manifest_path),
        "compare": build_release_compare_report(
            current_manifest,
            previous_manifest,
            current_manifest_path=str(current_manifest_path),
            previous_manifest_path=previous_manifest_path_str,
        ),
    }

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False))
    else:
        compare = report["compare"]
        print(f"ok: {report['ok']}")
        print(f"headline: {compare['headline']}")
        print(f"has_previous: {compare['has_previous']}")
        print(f"changed: {compare['changed']}")
        if compare["previous_manifest_path"]:
            print(f"previous_manifest_path: {compare['previous_manifest_path']}")
        if compare["changed_sections"]:
            print("changed_sections:")
            for item in compare["changed_sections"]:
                print(f"- {item}")
        if compare["items"]:
            print("items:")
            for item in compare["items"]:
                print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
