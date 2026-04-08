from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "colleague-clone" / "examples"
BOOTSTRAP_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "bootstrap_colleague_clone.py"
VALIDATE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "validate_colleague_skill.py"

EXAMPLE_SPECS = {
    "sample_search_api_predecessor": {
        "name": "Search API 前任",
        "relationship": "predecessor",
        "sources": [
            "colleague-clone/tests/fixtures/local_docs/search_api_handoff.md",
        ],
        "pasted_text": [
            "结论前置，评审先看 impact。",
        ],
    },
    "sample_slack_reviewer": {
        "name": "Slack Reviewer",
        "relationship": "mentor",
        "sources": [
            "colleague-clone/tests/fixtures/slack_export",
        ],
        "pasted_text": [
            "评审时先讲 impact，再讲实现细节。",
        ],
    },
    "sample_feishu_reviewer": {
        "name": "Feishu Reviewer",
        "relationship": "predecessor",
        "sources": [
            "colleague-clone/tests/fixtures/feishu_export/messages.json",
        ],
        "source_kinds": [
            "workspace_export",
        ],
        "pasted_text": [
            "先确认 owner，再同步相关方。",
        ],
    },
    "sample_dingtalk_reviewer": {
        "name": "DingTalk Reviewer",
        "relationship": "predecessor",
        "sources": [
            "colleague-clone/tests/fixtures/dingtalk_export/messages.json",
        ],
        "source_kinds": [
            "workspace_export",
        ],
        "pasted_text": [
            "先确认 owner，再同步相关方。",
            "CR 重点看错误码统一和回滚预案。",
            "结论前置，列表化同步风险。",
        ],
    },
    "sample_wechat_reviewer": {
        "name": "WeChat Reviewer",
        "relationship": "colleague",
        "sources": [
            "colleague-clone/tests/fixtures/wechat_export/messages.json",
        ],
        "source_kinds": [
            "workspace_export",
        ],
        "pasted_text": [
            "先确认 owner，再同步相关方。",
        ],
    },
    "sample_pdf_image_reviewer": {
        "name": "PDF Image Reviewer",
        "relationship": "mentor",
        "sources": [
            "colleague-clone/tests/fixtures/document_inputs/review_handoff.pdf",
            "colleague-clone/tests/fixtures/document_inputs/rollback-risk-screenshot.png",
        ],
        "pasted_text": [
            "先确认 owner，再同步相关方。",
            "结论前置，列表化同步风险。",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate colleague-clone example bundles from fixture inputs.")
    parser.add_argument(
        "--example",
        action="append",
        default=[],
        help="Optional example name. Repeat to generate a subset.",
    )
    parser.add_argument(
        "--output-root",
        default=str(EXAMPLES_DIR),
        help="Directory where example bundle directories will be generated.",
    )
    parser.add_argument("--validate", action="store_true", help="Run validate_colleague_skill.py after each generation.")
    parser.add_argument(
        "--check-readme-links",
        action="store_true",
        help="Check absolute markdown links inside repo example READMEs.",
    )
    return parser.parse_args()


def resolve_examples(selected: list[str]) -> list[str]:
    if not selected:
        return list(EXAMPLE_SPECS)
    unknown = [name for name in selected if name not in EXAMPLE_SPECS]
    if unknown:
        raise SystemExit(f"unknown examples: {', '.join(unknown)}")
    return selected


def run_json_command(command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"command failed: {' '.join(command)}")
    return json.loads(proc.stdout.strip() or '{"ok": true}')


def build_bootstrap_command(example_name: str, spec: dict, output_root: Path) -> list[str]:
    command = [
        sys.executable,
        str(BOOTSTRAP_SCRIPT),
        "--bundle-dir",
        str(output_root / example_name),
        "--name",
        spec["name"],
        "--relationship",
        spec["relationship"],
    ]
    for source in spec.get("sources", []):
        command.extend(["--source", str(REPO_ROOT / source)])
    for source_kind in spec.get("source_kinds", []):
        command.extend(["--source-kind", source_kind])
    for pasted_text in spec.get("pasted_text", []):
        command.extend(["--pasted-text", pasted_text])
    return command


def validate_bundle(bundle_dir: Path) -> dict:
    return run_json_command(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--bundle-dir",
            str(bundle_dir),
            "--format",
            "json",
        ]
    )


def check_repo_readme_links() -> list[dict]:
    failures: list[dict] = []
    pattern = re.compile(r"\[[^\]]+\]\((/[^)]+)\)")
    for readme_path in sorted(EXAMPLES_DIR.glob("*/README.md")):
        text = readme_path.read_text(encoding="utf-8")
        missing = [target for target in pattern.findall(text) if not Path(target).exists()]
        if missing:
            failures.append(
                {
                    "readme": str(readme_path),
                    "missing_targets": missing,
                }
            )
    return failures


def main() -> int:
    args = parse_args()
    example_names = resolve_examples(args.example)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    generated: list[dict] = []
    for example_name in example_names:
        spec = EXAMPLE_SPECS[example_name]
        bootstrap_report = run_json_command(build_bootstrap_command(example_name, spec, output_root))
        item = {
            "example": example_name,
            "bundle_dir": str(output_root / example_name),
            "bootstrap": bootstrap_report,
        }
        if args.validate:
            item["validate"] = validate_bundle(output_root / example_name)
        generated.append(item)

    readme_failures = check_repo_readme_links() if args.check_readme_links else []
    report = {
        "ok": not readme_failures and all(item.get("validate", {}).get("ok", True) for item in generated),
        "generated_count": len(generated),
        "generated": generated,
        "readme_failures": readme_failures,
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
