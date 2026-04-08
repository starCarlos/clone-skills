#!/usr/bin/env python3
"""Validate generated workflow_blueprint.md quality."""

from __future__ import annotations

import argparse

try:
    from workflow_blueprint_quality import analyze_blueprint, emit_report
except ModuleNotFoundError:
    from scripts.workflow_blueprint_quality import analyze_blueprint, emit_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate workflow_blueprint.md quality.")
    parser.add_argument("--input", required=True, help="Path to workflow_blueprint.md")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = analyze_blueprint(args.input)
    emit_report(report, as_json=args.format == "json")
    return 0 if report.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
