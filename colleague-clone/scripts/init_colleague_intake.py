from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_intake_request_yaml,
    ensure_bundle_dirs,
    parse_field_mapping,
    resolve_source_type,
    slugify,
    utc_now_iso,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a colleague-clone bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Target bundle directory.")
    parser.add_argument("--name", required=True, help="Display name of the target colleague.")
    parser.add_argument("--slug", default="", help="Optional explicit slug.")
    parser.add_argument("--relationship", default="colleague", help="Relationship to the target.")
    parser.add_argument("--org-context", default="", help="Optional organization context.")
    parser.add_argument("--role-summary", default="", help="Optional one-line role summary.")
    parser.add_argument("--subjective-impression", default="", help="Optional free-form impression.")
    parser.add_argument("--personality-tag", action="append", default=[], help="Repeatable personality tag.")
    parser.add_argument("--culture-tag", action="append", default=[], help="Repeatable culture tag.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Repeatable source file path. Source type is inferred from extension.",
    )
    parser.add_argument(
        "--source-kind",
        action="append",
        default=[],
        help="Optional source kind override aligned with each --source. Allowed: markdown, text, pdf_document, image_file, json_export, email_eml, email_mbox, workspace_export.",
    )
    parser.add_argument(
        "--field-map",
        action="append",
        default=[],
        help='Optional JSON field mapping aligned with each --source, for example \'{"platform":"wechat","text":"payload.text"}\'.',
    )
    parser.add_argument(
        "--pasted-text",
        action="append",
        default=[],
        help="Repeatable pasted text payload. Stored into the bundle as a local source artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    slug = args.slug or slugify(args.name)
    ensure_bundle_dirs(bundle_dir)

    timestamp = utc_now_iso()
    manifest_items: list[dict] = []
    intake_sources: list[dict] = []
    source_summaries: list[dict] = []
    source_counter = 0
    if args.source_kind and len(args.source_kind) != len(args.source):
        raise SystemExit("--source-kind must be omitted or provided once for each --source")
    if args.field_map and len(args.field_map) != len(args.source):
        raise SystemExit("--field-map must be omitted or provided once for each --source")

    for index, raw_path in enumerate(args.source):
        source_counter += 1
        path = Path(raw_path).expanduser().resolve()
        explicit_kind = args.source_kind[index] if args.source_kind else ""
        field_mapping = parse_field_mapping(args.field_map[index]) if args.field_map else {}
        source_type, detection_mode = resolve_source_type(path, explicit_kind)
        source_id = f"src_{source_counter:03d}"
        manifest_item = {
            "source_id": source_id,
            "source_type": source_type,
            "path": str(path),
            "origin": "cli",
            "trust_level": "direct",
            "imported_at": timestamp,
            "parse_status": "pending",
            "detection_mode": detection_mode,
        }
        if field_mapping:
            manifest_item["field_mapping"] = field_mapping
        manifest_items.append(manifest_item)
        intake_sources.append(
            {
                "source_type": source_type,
                "path": str(path),
                "trust_level": "direct",
            }
        )
        summary = {
            "source_id": source_id,
            "path": str(path),
            "source_type": source_type,
            "detection_mode": detection_mode,
        }
        if field_mapping:
            summary["field_mapping"] = field_mapping
        source_summaries.append(summary)

    for pasted_text in args.pasted_text:
        source_counter += 1
        source_id = f"src_{source_counter:03d}"
        pasted_path = bundle_dir / "sources" / "pasted" / f"{source_id}.txt"
        pasted_path.write_text(pasted_text.strip() + "\n", encoding="utf-8")
        manifest_items.append(
            {
                "source_id": source_id,
                "source_type": "pasted_text",
                "path": str(pasted_path),
                "origin": "cli",
                "trust_level": "direct",
                "imported_at": timestamp,
                "parse_status": "pending",
                "detection_mode": "generated",
            }
        )
        intake_sources.append(
            {
                "source_type": "pasted_text",
                "path": str(pasted_path),
                "trust_level": "direct",
            }
        )
        source_summaries.append(
            {
                "source_id": source_id,
                "path": str(pasted_path),
                "source_type": "pasted_text",
                "detection_mode": "generated",
            }
        )

    intake_yaml = build_intake_request_yaml(
        name=args.name,
        slug=slug,
        relationship=args.relationship,
        org_context=args.org_context,
        role_summary=args.role_summary,
        subjective_impression=args.subjective_impression,
        personality_tags=args.personality_tag,
        culture_tags=args.culture_tag,
        sources=intake_sources,
    )
    (bundle_dir / "sources" / "intake_request.yaml").write_text(intake_yaml, encoding="utf-8")
    write_jsonl(bundle_dir / "sources" / "manifest.jsonl", manifest_items)

    state = "sources_pending" if manifest_items else "intake_started"
    write_json(
        bundle_dir / "meta.json",
        {
            "name": args.name,
            "slug": slug,
            "relationship": args.relationship,
            "state": state,
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "slug": slug,
                "state": state,
                "source_count": len(manifest_items),
                "sources": source_summaries,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
