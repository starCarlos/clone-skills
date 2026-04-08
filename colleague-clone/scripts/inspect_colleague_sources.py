from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import parse_field_mapping, resolve_source_type, split_records_by_privacy, utc_now_iso
from normalize_colleague_sources import parse_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local colleague-clone sources before normalization.")
    parser.add_argument("--source", action="append", default=[], help="Repeatable local source path.")
    parser.add_argument(
        "--source-kind",
        action="append",
        default=[],
        help="Optional source kind override aligned with each --source.",
    )
    parser.add_argument(
        "--field-map",
        action="append",
        default=[],
        help='Optional JSON field mapping aligned with each --source, for example \'{"platform":"wechat","text":"payload.text"}\'.',
    )
    return parser.parse_args()


def summarize_records(records: list[dict]) -> dict:
    privacy_split = split_records_by_privacy(records)
    speakers = sorted({str(item.get("speaker", "")).strip() for item in records if str(item.get("speaker", "")).strip() and str(item.get("speaker", "")).strip() != "unknown"})
    channels = sorted({str(item.get("channel", "")).strip() for item in records if str(item.get("channel", "")).strip()})
    timestamps = sorted(str(item.get("timestamp", "")).strip() for item in records if str(item.get("timestamp", "")).strip())
    missing_speaker_count = sum(1 for item in records if str(item.get("speaker", "")).strip() in {"", "unknown"})
    missing_channel_count = sum(1 for item in records if not str(item.get("channel", "")).strip())
    tags = sorted({str(tag).strip() for item in records for tag in item.get("tags", []) if str(tag).strip()})
    return {
        "record_count": len(records),
        "speaker_count": len(speakers),
        "channel_count": len(channels),
        "sample_speakers": speakers[:5],
        "sample_channels": channels[:5],
        "timestamp_range": {
            "earliest": timestamps[0] if timestamps else "",
            "latest": timestamps[-1] if timestamps else "",
        },
        "missing_speaker_rate": round(missing_speaker_count / len(records), 3) if records else 0.0,
        "missing_channel_rate": round(missing_channel_count / len(records), 3) if records else 0.0,
        "sample_titles": [str(item.get("title", "")).strip() for item in records if str(item.get("title", "")).strip()][:5],
        "tags": tags,
        "privacy_counts": privacy_split["audit"]["counts"],
        "privacy_excluded_record_ids": privacy_split["audit"]["excluded_record_ids"],
    }


def build_risks(summary: dict, source_type: str, detected_platform: str) -> list[str]:
    risks: list[str] = []
    if summary["record_count"] == 0:
        risks.append("no records extracted")
    if summary["missing_speaker_rate"] >= 0.5 and source_type in {"json_export", "workspace_export"}:
        risks.append("speaker coverage is low")
    if summary["missing_channel_rate"] >= 0.5 and detected_platform in {"slack", "feishu", "dingtalk", "wechat"}:
        risks.append("channel coverage is low for a platform export")
    if not summary["timestamp_range"]["earliest"]:
        risks.append("timestamps are missing")
    if source_type == "pdf_document" and "pdf_no_text" in summary["tags"]:
        risks.append("pdf has pages without extractable text")
    if source_type == "image_file" and "image_ocr_unavailable" in summary["tags"]:
        risks.append("image OCR is unavailable in current environment")
    if source_type == "image_file" and "image_ocr_empty" in summary["tags"]:
        risks.append("image OCR found no text")
    if summary["privacy_counts"]["private_sensitive"] > 0 or summary["privacy_counts"]["work_adjacent"] > 0:
        risks.append("source contains private-sensitive content that will be excluded from default analysis")
    if summary["record_count"] and summary["privacy_counts"]["private_sensitive"] >= summary["record_count"] / 2:
        risks.append("private-sensitive content dominates this source")
    return risks


def summarize_risk_level(risks: list[str]) -> str:
    if not risks:
        return "safe"
    if len(risks) >= 2 or "no records extracted" in risks:
        return "risky"
    return "warning"


def inspect_one(raw_path: str, explicit_kind: str = "", raw_field_mapping: str = "") -> dict:
    path = Path(raw_path).expanduser().resolve()
    source_type, detection_mode = resolve_source_type(path, explicit_kind)
    field_mapping = parse_field_mapping(raw_field_mapping) if raw_field_mapping else {}
    item = {
        "source_id": "inspect_001",
        "source_type": source_type,
        "path": str(path),
        "imported_at": utc_now_iso(),
    }
    if field_mapping:
        item["field_mapping"] = field_mapping
    records, detected_platform, diagnostics = parse_source(item, path)
    summary = summarize_records(records)
    risks = build_risks(summary, source_type, detected_platform)
    risk_level = summarize_risk_level(risks)
    report = {
        "path": str(path),
        "source_type": source_type,
        "detection_mode": detection_mode,
        "detected_platform": detected_platform or "",
        **summary,
        "risks": risks,
        "risk_level": risk_level,
    }
    if field_mapping:
        report["field_mapping"] = field_mapping
    report.update(diagnostics)
    return report


def main() -> int:
    args = parse_args()
    if args.source_kind and len(args.source_kind) != len(args.source):
        raise SystemExit("--source-kind must be omitted or provided once for each --source")
    if args.field_map and len(args.field_map) != len(args.source):
        raise SystemExit("--field-map must be omitted or provided once for each --source")
    if not args.source:
        raise SystemExit("at least one --source is required")

    reports = []
    for index, raw_path in enumerate(args.source):
        explicit_kind = args.source_kind[index] if args.source_kind else ""
        raw_field_mapping = args.field_map[index] if args.field_map else ""
        reports.append(inspect_one(raw_path, explicit_kind, raw_field_mapping))

    print(
        json.dumps(
            {
                "ok": True,
                "source_count": len(reports),
                "sources": reports,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
