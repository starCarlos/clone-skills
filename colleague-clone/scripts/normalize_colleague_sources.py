from __future__ import annotations

import argparse
import importlib.util
import json
import mailbox
import os
import shutil
from email import policy
from email.parser import BytesParser
from pathlib import Path

from colleague_clone_platform_exports import parse_json_export_fragments, parse_workspace_export_fragments
from colleague_clone_common import (
    extract_title,
    load_json,
    load_jsonl,
    normalize_text,
    utc_now_iso,
    write_json,
    write_jsonl,
)


SUPPORTED_TYPES = {
    "markdown",
    "text",
    "pdf_document",
    "image_file",
    "pasted_text",
    "json_export",
    "email_eml",
    "email_mbox",
    "workspace_export",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize local colleague-clone source files.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory created by init_colleague_intake.py")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when any source fails.")
    return parser.parse_args()


def output_bucket_for(source_type: str) -> str:
    if source_type == "pasted_text":
        return "pasted"
    if source_type in {"json_export", "workspace_export"}:
        return "messages"
    if source_type == "image_file":
        return "images"
    if source_type in {"email_eml", "email_mbox"}:
        return "emails"
    return "docs"


def build_record(
    *,
    source_id: str,
    source_type: str,
    content_type: str,
    timestamp: str,
    text: str,
    title: str = "",
    speaker: str = "unknown",
    channel: str = "",
) -> dict:
    return {
        "record_id": "",
        "source_id": source_id,
        "source_type": source_type,
        "content_type": content_type,
        "speaker": speaker,
        "timestamp": timestamp,
        "channel": channel,
        "title": title,
        "text": normalize_text(text),
        "tags": [],
        "privacy_scope": "private_workspace",
        "confidence": 1.0,
    }


def parse_json_export(source_id: str, imported_at: str, path: Path, field_mapping: dict | None = None) -> tuple[list[dict], str, dict]:
    fragments, platform, diagnostics = parse_json_export_fragments(imported_at, path, field_mapping=field_mapping)
    records: list[dict] = []
    for index, fragment in enumerate(fragments, start=1):
        record = build_record(
            source_id=source_id,
            source_type=str(fragment.get("source_type") or "json_export"),
            content_type=str(fragment.get("content_type") or "message"),
            timestamp=str(fragment.get("timestamp") or imported_at),
            text=str(fragment.get("text") or ""),
            title=str(fragment.get("title") or ""),
            speaker=str(fragment.get("speaker") or "unknown"),
            channel=str(fragment.get("channel") or ""),
        )
        record["record_id"] = f"{source_id}_{index:03d}"
        records.append(record)
    return records, platform, diagnostics


def parse_eml(source_id: str, imported_at: str, path: Path) -> list[dict]:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    text_parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                text_parts.append(part.get_content())
    else:
        text_parts.append(message.get_content())
    text = "\n".join(part.strip() for part in text_parts if part and part.strip())
    record = build_record(
        source_id=source_id,
        source_type="email_eml",
        content_type="email",
        timestamp=str(message.get("Date") or imported_at),
        text=text or "(empty email body)",
        title=str(message.get("Subject") or path.stem),
        speaker=str(message.get("From") or "unknown"),
    )
    record["record_id"] = f"{source_id}_001"
    return [record]


def parse_mbox(source_id: str, imported_at: str, path: Path) -> list[dict]:
    box = mailbox.mbox(path)
    records: list[dict] = []
    for index, message in enumerate(box, start=1):
        payload = ""
        if message.is_multipart():
            parts = []
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        parts.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace"))
                    except Exception:
                        continue
            payload = "\n".join(part.strip() for part in parts if part.strip())
        else:
            raw_payload = message.get_payload(decode=True)
            if isinstance(raw_payload, bytes):
                payload = raw_payload.decode(message.get_content_charset() or "utf-8", errors="replace")
            else:
                payload = str(message.get_payload())
        record = build_record(
            source_id=source_id,
            source_type="email_mbox",
            content_type="email",
            timestamp=str(message.get("Date") or imported_at),
            text=payload or "(empty email body)",
            title=str(message.get("Subject") or f"{path.stem}-{index}"),
            speaker=str(message.get("From") or "unknown"),
        )
        record["record_id"] = f"{source_id}_{index:03d}"
        records.append(record)
    return records or [
        {
            **build_record(
                source_id=source_id,
                source_type="email_mbox",
                content_type="email",
                timestamp=imported_at,
                text="(empty mailbox)",
                title=path.stem,
            ),
            "record_id": f"{source_id}_001",
        }
    ]


def parse_workspace_export(
    source_id: str,
    imported_at: str,
    path: Path,
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    fragments, platform, diagnostics = parse_workspace_export_fragments(imported_at, path, field_mapping=field_mapping)
    records: list[dict] = []
    for index, fragment in enumerate(fragments, start=1):
        record = build_record(
            source_id=source_id,
            source_type=str(fragment.get("source_type") or "workspace_export"),
            content_type=str(fragment.get("content_type") or "message"),
            timestamp=str(fragment.get("timestamp") or imported_at),
            text=str(fragment.get("text") or ""),
            title=str(fragment.get("title") or ""),
            speaker=str(fragment.get("speaker") or "unknown"),
            channel=str(fragment.get("channel") or ""),
        )
        record["record_id"] = f"{source_id}_{index:03d}"
        records.append(record)
    return records, platform, diagnostics


def parse_pdf(source_id: str, imported_at: str, path: Path) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    title = ""
    if reader.metadata and reader.metadata.title:
        title = str(reader.metadata.title).strip()

    records: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted_text = (page.extract_text() or "").strip()
        tags: list[str] = []
        content_type = "document_page"
        if not extracted_text:
            extracted_text = f"PDF page {index} from {path.name} had no extractable text."
            tags.append("pdf_no_text")
            content_type = "document_page_notice"
        record = build_record(
            source_id=source_id,
            source_type="pdf_document",
            content_type=content_type,
            timestamp=imported_at,
            text=extracted_text,
            title=title or f"{path.stem} page {index}",
        )
        record["record_id"] = f"{source_id}_{index:03d}"
        record["tags"] = tags
        record["page_number"] = index
        records.append(record)

    if records:
        return records

    record = build_record(
        source_id=source_id,
        source_type="pdf_document",
        content_type="document_notice",
        timestamp=imported_at,
        text=f"PDF source {path.name} had no readable pages.",
        title=title or path.stem,
    )
    record["record_id"] = f"{source_id}_001"
    record["tags"] = ["pdf_no_text"]
    return [record]


def detect_image_ocr_provider() -> str:
    forced = os.environ.get("COLLEAGUE_CLONE_IMAGE_OCR_PROVIDER", "").strip().lower()
    if forced in {"disabled", "none"}:
        return ""
    if forced == "mock":
        return "mock"
    if bool(importlib.util.find_spec("pytesseract")) and bool(shutil.which("tesseract")):
        return "tesseract"
    return ""


def extract_image_ocr_text(image_handle) -> dict:
    provider = detect_image_ocr_provider()
    if not provider:
        return {
            "provider": "",
            "status": "unavailable",
            "text": "",
        }
    if provider == "mock":
        text = os.environ.get("COLLEAGUE_CLONE_IMAGE_OCR_TEXT", "").strip()
        return {
            "provider": "mock",
            "status": "success" if text else "empty",
            "text": text,
        }

    import pytesseract

    text = pytesseract.image_to_string(image_handle).strip()
    return {
        "provider": "tesseract",
        "status": "success" if text else "empty",
        "text": text,
    }


def parse_image(source_id: str, imported_at: str, path: Path) -> list[dict]:
    from PIL import Image

    with Image.open(path) as image_handle:
        image_handle.load()
        width, height = image_handle.size
        image_format = str(image_handle.format or path.suffix.lstrip(".")).upper()
        image_mode = str(image_handle.mode or "")
        metadata_text = f"Image source: {path.name}"
        tags: list[str] = []
        ocr = extract_image_ocr_text(image_handle)
        text = metadata_text
        if ocr["status"] == "success":
            tags.append("image_ocr_extracted")
            text = ocr["text"]
        elif ocr["status"] == "empty":
            tags.append("image_ocr_empty")
            text = metadata_text + "\nOCR status: no text extracted."
        else:
            tags.append("image_ocr_unavailable")
            text = metadata_text + "\nOCR status: unavailable in current environment."

    record = build_record(
        source_id=source_id,
        source_type="image_file",
        content_type="image_source",
        timestamp=imported_at,
        text=text,
        title=path.stem,
    )
    record["record_id"] = f"{source_id}_001"
    record["tags"] = tags
    record["image_metadata"] = {
        "format": image_format,
        "width": width,
        "height": height,
        "mode": image_mode,
    }
    record["image_analysis"] = {
        "ocr_provider": ocr["provider"],
        "ocr_status": ocr["status"],
        "ocr_text": ocr["text"],
    }
    return [record]


def parse_source(item: dict, path: Path) -> tuple[list[dict], str, dict]:
    source_type = str(item.get("source_type", ""))
    source_id = str(item.get("source_id", ""))
    imported_at = str(item.get("imported_at") or utc_now_iso())
    field_mapping = item.get("field_mapping", {}) if isinstance(item.get("field_mapping", {}), dict) else {}
    if source_type in {"markdown", "text", "pasted_text"}:
        text = path.read_text(encoding="utf-8")
        record = build_record(
            source_id=source_id,
            source_type=source_type,
            content_type="note" if source_type == "pasted_text" else "document",
            timestamp=imported_at,
            text=text,
            title=extract_title(text),
        )
        record["record_id"] = f"{source_id}_001"
        return [record], "", {}
    if source_type == "json_export":
        return parse_json_export(source_id, imported_at, path, field_mapping=field_mapping)
    if source_type == "pdf_document":
        return parse_pdf(source_id, imported_at, path), "", {}
    if source_type == "image_file":
        return parse_image(source_id, imported_at, path), "", {}
    if source_type == "email_eml":
        return parse_eml(source_id, imported_at, path), "", {}
    if source_type == "email_mbox":
        return parse_mbox(source_id, imported_at, path), "", {}
    if source_type == "workspace_export":
        return parse_workspace_export(source_id, imported_at, path, field_mapping=field_mapping)
    raise ValueError(f"unsupported source_type: {source_type}")


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    manifest_path = bundle_dir / "sources" / "manifest.jsonl"

    meta = load_json(meta_path)
    manifest = load_jsonl(manifest_path)

    normalized_count = 0
    errors: list[str] = []
    updated_manifest: list[dict] = []
    source_breakdown: dict[str, int] = {}
    detected_platforms: dict[str, int] = {}

    for item in manifest:
        item = dict(item)
        source_type = item.get("source_type", "")
        source_id = item.get("source_id", "")
        path = Path(item.get("path", ""))

        if source_type not in SUPPORTED_TYPES:
            item["parse_status"] = "unsupported"
            item["error"] = f"unsupported source_type: {source_type}"
            errors.append(f"{source_id}: unsupported source_type {source_type}")
            updated_manifest.append(item)
            continue

        if not path.exists():
            item["parse_status"] = "missing"
            item["error"] = f"missing file: {path}"
            errors.append(f"{source_id}: missing file")
            updated_manifest.append(item)
            continue

        try:
            records, detected_platform, diagnostics = parse_source(item, path)
        except Exception as exc:
            item["parse_status"] = "error"
            item["error"] = str(exc)
            errors.append(f"{source_id}: {exc}")
            updated_manifest.append(item)
            continue

        if not records:
            item["parse_status"] = "empty"
            item["error"] = "no records extracted"
            errors.append(f"{source_id}: no records extracted")
            updated_manifest.append(item)
            continue

        output_dir = bundle_dir / "normalized" / output_bucket_for(source_type)
        output_path = output_dir / f"{source_id}.jsonl"
        write_jsonl(output_path, records)

        item["parse_status"] = "normalized"
        item["normalized_path"] = str(output_path)
        item["normalized_at"] = utc_now_iso()
        if detected_platform:
            item["detected_platform"] = detected_platform
            detected_platforms[detected_platform] = detected_platforms.get(detected_platform, 0) + 1
        for key in (
            "platform_detection_mode",
            "platform_detection_reasons",
            "platform_signal_scores",
            "field_mapping_keys",
            "field_coverage",
            "missing_fields",
        ):
            value = diagnostics.get(key)
            if value not in (None, "", [], {}):
                item[key] = diagnostics[key]
        source_breakdown[str(source_type)] = source_breakdown.get(str(source_type), 0) + 1
        updated_manifest.append(item)
        normalized_count += 1

    write_jsonl(manifest_path, updated_manifest)
    meta["state"] = "sources_normalized" if normalized_count > 0 else meta.get("state", "sources_pending")
    meta["updated_at"] = utc_now_iso()
    write_json(meta_path, meta)

    summary = {
        "ok": not errors,
        "bundle_dir": str(bundle_dir),
        "normalized_count": normalized_count,
        "error_count": len(errors),
        "errors": errors,
        "state": meta["state"],
        "source_breakdown": source_breakdown,
        "detected_platforms": detected_platforms,
        "normalized_sources": [
            {
                "source_id": item.get("source_id", ""),
                "source_type": item.get("source_type", ""),
                "detected_platform": item.get("detected_platform", ""),
                "normalized_path": item.get("normalized_path", ""),
                "platform_detection_mode": item.get("platform_detection_mode", ""),
                "missing_fields": item.get("missing_fields", []),
            }
            for item in updated_manifest
            if item.get("parse_status") == "normalized"
        ],
    }
    write_json(bundle_dir / "normalized" / "collection_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
