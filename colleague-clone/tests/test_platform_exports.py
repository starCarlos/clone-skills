from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "colleague-clone" / "tests" / "fixtures"
INIT_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "init_colleague_intake.py"
NORMALIZE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "normalize_colleague_sources.py"
BOOTSTRAP_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "bootstrap_colleague_clone.py"
VALIDATE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "validate_colleague_skill.py"
INSPECT_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "inspect_colleague_sources.py"


class ColleagueClonePlatformExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="colleague-clone-platform-tests-")
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cmd(self, script: Path, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["python3", str(script), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def write_minimal_pdf(self, path: Path, text: str) -> None:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        objects = [
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        ]
        stream = f"BT\n/F1 14 Tf\n36 96 Td\n({escaped}) Tj\nET\n"
        objects.append(f"4 0 obj\n<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}endstream\nendobj\n")
        objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        pdf = "%PDF-1.4\n"
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf.encode("utf-8")))
            pdf += obj
        xref_offset = len(pdf.encode("utf-8"))
        pdf += f"xref\n0 {len(offsets)}\n"
        pdf += "0000000000 65535 f \n"
        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n"
        pdf += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        path.write_bytes(pdf.encode("utf-8"))

    def write_minimal_image(self, path: Path, text: str) -> None:
        image = Image.new("RGB", (320, 120), "white")
        draw = ImageDraw.Draw(image)
        draw.text((12, 40), text, fill="black")
        image.save(path)

    def test_slack_directory_normalizes_with_resolved_user_and_channel(self) -> None:
        source_dir = self.root / "slack-export"
        bundle_dir = self.root / "slack-bundle"
        shutil.copytree(FIXTURES_DIR / "slack_export", source_dir)

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Slack User",
            "--source",
            str(source_dir),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)
        init_report = json.loads(init_proc.stdout)
        self.assertEqual(init_report["sources"][0]["detection_mode"], "auto")

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        normalize_report = json.loads(normalize_proc.stdout)
        self.assertEqual(normalize_report["detected_platforms"]["slack"], 1)

        manifest = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest[0]["source_type"], "workspace_export")
        self.assertEqual(manifest[0]["detected_platform"], "slack")

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["source_type"], "slack_export")
        self.assertEqual(records[0]["speaker"], "Alice Example")
        self.assertEqual(records[0]["channel"], "review-room")
        self.assertTrue(records[0]["timestamp"].endswith("Z"))

    def test_slack_zip_normalizes_like_directory_export(self) -> None:
        bundle_dir = self.root / "slack-zip-bundle"
        zip_path = self.root / "slack-export.zip"

        with zipfile.ZipFile(zip_path, "w") as archive:
            for fixture in sorted((FIXTURES_DIR / "slack_export").rglob("*")):
                if fixture.is_file():
                    archive.write(fixture, fixture.relative_to(FIXTURES_DIR / "slack_export"))

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Slack Zip User",
            "--source",
            str(zip_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["source_type"], "slack_export")
        self.assertEqual(records[1]["speaker"], "Alice Example")

    def test_source_kind_override_marks_detection_mode_explicit(self) -> None:
        bundle_dir = self.root / "override-bundle"
        source_path = FIXTURES_DIR / "feishu_export" / "messages.json"

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Override User",
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)
        init_report = json.loads(init_proc.stdout)
        self.assertEqual(init_report["sources"][0]["source_type"], "workspace_export")
        self.assertEqual(init_report["sources"][0]["detection_mode"], "explicit")

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        normalize_report = json.loads(normalize_proc.stdout)
        self.assertEqual(normalize_report["detected_platforms"]["feishu"], 1)

    def test_feishu_json_export_detects_nested_sender_and_content(self) -> None:
        bundle_dir = self.root / "feishu-json-bundle"
        source_path = FIXTURES_DIR / "feishu_export" / "messages.json"

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Feishu Json User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["source_type"], "feishu_export")
        self.assertEqual(records[0]["speaker"], "Bob Reviewer")
        self.assertEqual(records[0]["channel"], "Search API Review")
        self.assertIn("结论前置", records[0]["text"])

    def test_feishu_directory_normalizes_as_workspace_export(self) -> None:
        bundle_dir = self.root / "feishu-dir-bundle"
        source_dir = self.root / "feishu-export-dir"
        shutil.copytree(FIXTURES_DIR / "feishu_directory", source_dir)

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Feishu Dir User",
            "--source",
            str(source_dir),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        manifest = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest[0]["detected_platform"], "feishu")

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_type"], "feishu_export")
        self.assertEqual(records[0]["speaker"], "Carol Lead")
        self.assertEqual(records[0]["channel"], "Architecture Sync")

    def test_dingtalk_json_export_detects_sender_channel_and_text(self) -> None:
        bundle_dir = self.root / "dingtalk-bundle"
        source_path = FIXTURES_DIR / "dingtalk_export" / "messages.json"

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "DingTalk User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        normalize_report = json.loads(normalize_proc.stdout)
        self.assertEqual(normalize_report["detected_platforms"]["dingtalk"], 1)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["source_type"], "dingtalk_export")
        self.assertEqual(records[0]["speaker"], "Dora Ops")
        self.assertEqual(records[0]["channel"], "Search API Incident")
        self.assertIn("先止血", records[0]["text"])

    def test_wechat_json_export_detects_sender_channel_and_text(self) -> None:
        bundle_dir = self.root / "wechat-bundle"
        source_path = FIXTURES_DIR / "wechat_export" / "messages.json"

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "WeChat User",
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        normalize_report = json.loads(normalize_proc.stdout)
        self.assertEqual(normalize_report["detected_platforms"]["wechat"], 1)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["source_type"], "wechat_export")
        self.assertEqual(records[0]["speaker"], "Wendy Reviewer")
        self.assertEqual(records[0]["channel"], "Search API WeChat Review")
        self.assertIn("先看 impact", records[0]["text"])

    def test_pdf_document_normalizes_into_doc_records(self) -> None:
        bundle_dir = self.root / "pdf-bundle"
        source_path = self.root / "review-handoff.pdf"
        self.write_minimal_pdf(source_path, "Review checklist and rollback plan.")

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Pdf User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "docs" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_type"], "pdf_document")
        self.assertEqual(records[0]["content_type"], "document_page")
        self.assertIn("rollback plan", records[0]["text"])

    def test_image_file_normalizes_into_image_records_with_metadata(self) -> None:
        bundle_dir = self.root / "image-bundle"
        source_path = self.root / "rollback-review-checklist.png"
        self.write_minimal_image(source_path, "rollback first")

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Image User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "images" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_type"], "image_file")
        self.assertEqual(records[0]["content_type"], "image_source")
        self.assertIn("rollback-review-checklist", records[0]["text"])
        self.assertIn("width", records[0]["image_metadata"])
        self.assertEqual(records[0]["image_analysis"]["ocr_status"], "unavailable")

    def test_image_file_normalizes_with_mock_ocr_provider(self) -> None:
        bundle_dir = self.root / "image-ocr-bundle"
        source_path = self.root / "error-code-screenshot.png"
        self.write_minimal_image(source_path, "error code")

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Image OCR User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
            extra_env={
                "COLLEAGUE_CLONE_IMAGE_OCR_PROVIDER": "mock",
                "COLLEAGUE_CLONE_IMAGE_OCR_TEXT": "error code checklist",
            },
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        record = json.loads((bundle_dir / "normalized" / "images" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["image_analysis"]["ocr_provider"], "mock")
        self.assertEqual(record["image_analysis"]["ocr_status"], "success")
        self.assertEqual(record["image_analysis"]["ocr_text"], "error code checklist")
        self.assertEqual(record["text"], "error code checklist\n")

    def test_image_file_normalizes_with_mock_ocr_empty_result(self) -> None:
        bundle_dir = self.root / "image-ocr-empty-bundle"
        source_path = self.root / "blank-screenshot.png"
        self.write_minimal_image(source_path, "")

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Image Empty OCR User",
            "--source",
            str(source_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
            extra_env={
                "COLLEAGUE_CLONE_IMAGE_OCR_PROVIDER": "mock",
                "COLLEAGUE_CLONE_IMAGE_OCR_TEXT": "",
            },
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        record = json.loads((bundle_dir / "normalized" / "images" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["image_analysis"]["ocr_provider"], "mock")
        self.assertEqual(record["image_analysis"]["ocr_status"], "empty")
        self.assertIn("OCR status: no text extracted.", record["text"])

    def test_require_final_reports_placeholder_markers(self) -> None:
        bundle_dir = self.root / "final-gate-bundle"
        source_path = self.root / "handoff.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Final Gate",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "CR重点：幂等、事务、N+1、错误码。",
                    "先写风险，再给方案。",
                    "紧急事故先止血，必要时回滚。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Final Gate User",
            "--source",
            str(source_path),
            "--pasted-text",
            "结论前置，列表化回复。",
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        meta["state"] = "final_confirmed"
        (bundle_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (bundle_dir / "persona.md").write_text("No persona summary available.\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["final_placeholders"])

    def test_inspect_reports_slack_directory_diagnostics_without_bundle_mutation(self) -> None:
        source_dir = self.root / "inspect-slack"
        shutil.copytree(FIXTURES_DIR / "slack_export", source_dir)

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_dir),
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["source_count"], 1)
        self.assertEqual(report["sources"][0]["detected_platform"], "slack")
        self.assertEqual(report["sources"][0]["record_count"], 2)
        self.assertEqual(report["sources"][0]["speaker_count"], 1)
        self.assertEqual(report["sources"][0]["channel_count"], 1)
        self.assertEqual(report["sources"][0]["detection_mode"], "auto")
        self.assertTrue(report["sources"][0]["timestamp_range"]["earliest"].endswith("Z"))
        self.assertFalse(any(path.name == "meta.json" for path in source_dir.rglob("meta.json")))

    def test_inspect_reports_feishu_json_diagnostics_with_explicit_override(self) -> None:
        source_path = FIXTURES_DIR / "feishu_export" / "messages.json"

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["source_count"], 1)
        self.assertEqual(report["sources"][0]["source_type"], "workspace_export")
        self.assertEqual(report["sources"][0]["detection_mode"], "explicit")
        self.assertEqual(report["sources"][0]["detected_platform"], "feishu")
        self.assertEqual(report["sources"][0]["platform_detection_mode"], "message_signals")
        self.assertGreaterEqual(report["sources"][0]["field_coverage"]["speaker"], 1.0)
        self.assertTrue(report["sources"][0]["platform_detection_reasons"])
        self.assertEqual(report["sources"][0]["record_count"], 2)
        self.assertIn("Bob Reviewer", report["sources"][0]["sample_speakers"])

    def test_inspect_reports_wechat_json_diagnostics_with_explicit_override(self) -> None:
        source_path = FIXTURES_DIR / "wechat_export" / "messages.json"

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["source_count"], 1)
        self.assertEqual(report["sources"][0]["source_type"], "workspace_export")
        self.assertEqual(report["sources"][0]["detected_platform"], "wechat")
        self.assertEqual(report["sources"][0]["platform_detection_mode"], "message_signals")
        self.assertEqual(report["sources"][0]["field_coverage"]["channel"], 1.0)
        self.assertEqual(report["sources"][0]["record_count"], 2)
        self.assertIn("Wendy Reviewer", report["sources"][0]["sample_speakers"])
        self.assertIn("Search API WeChat Review", report["sources"][0]["sample_channels"])

    def test_inspect_accepts_field_mapping_for_nonstandard_platform_export(self) -> None:
        source_path = self.root / "mapped-wechat.json"
        source_path.write_text(
            json.dumps(
                {
                    "payload": {
                        "entries": [
                            {
                                "actor": "Mapped Reviewer",
                                "roomName": "Mapped Review Room",
                                "sentAt": "2026-04-07T11:00:00Z",
                                "body": {"text": "先看 impact，再给方案。"},
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        field_mapping = json.dumps(
            {
                "platform": "wechat",
                "items": "payload.entries",
                "speaker": "actor",
                "channel": "roomName",
                "timestamp": "sentAt",
                "text": "body.text",
            },
            ensure_ascii=False,
        )

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
            "--field-map",
            field_mapping,
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["detected_platform"], "wechat")
        self.assertEqual(report["sources"][0]["platform_detection_mode"], "platform_hint")
        self.assertEqual(report["sources"][0]["field_mapping"]["items"], "payload.entries")
        self.assertEqual(report["sources"][0]["field_coverage"]["channel"], 1.0)
        self.assertFalse(report["sources"][0]["missing_fields"])

    def test_inspect_reports_generic_fallback_for_unknown_json_export(self) -> None:
        source_path = self.root / "unknown-export.json"
        source_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "headline": "Status update",
                            "body": {"plain_text": "只同步结论，不像任何平台导出。"},
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["detected_platform"], "generic")
        self.assertEqual(report["sources"][0]["platform_detection_mode"], "generic_fallback")
        self.assertIn("generic JSON parsing", report["sources"][0]["platform_detection_reasons"][0])
        self.assertEqual(report["sources"][0]["field_coverage"]["speaker"], 0.0)
        self.assertEqual(report["sources"][0]["field_coverage"]["channel"], 1.0)

    def test_inspect_marks_empty_json_export_as_risky(self) -> None:
        source_path = self.root / "empty.json"
        source_path.write_text("[]\n", encoding="utf-8")

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["record_count"], 0)
        self.assertEqual(report["sources"][0]["risk_level"], "risky")

    def test_inspect_reports_image_ocr_warning_when_ocr_is_unavailable(self) -> None:
        source_path = self.root / "search-api-risk-note.png"
        self.write_minimal_image(source_path, "risk first")

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["source_type"], "image_file")
        self.assertEqual(report["sources"][0]["risk_level"], "warning")
        self.assertIn("image OCR is unavailable in current environment", report["sources"][0]["risks"])

    def test_inspect_reports_image_ocr_empty_warning(self) -> None:
        source_path = self.root / "blank-risk-note.png"
        self.write_minimal_image(source_path, "")

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
            extra_env={
                "COLLEAGUE_CLONE_IMAGE_OCR_PROVIDER": "mock",
                "COLLEAGUE_CLONE_IMAGE_OCR_TEXT": "",
            },
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["source_type"], "image_file")
        self.assertEqual(report["sources"][0]["risk_level"], "warning")
        self.assertIn("image OCR found no text", report["sources"][0]["risks"])

    def test_inspect_marks_private_sensitive_source_as_risky(self) -> None:
        source_path = self.root / "private-notes.txt"
        source_path.write_text(
            "\n".join(
                [
                    "孩子这周发烧，需要去医院。",
                    "家里房贷压力比较大。",
                    "老婆希望这周请假。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        inspect_proc = self.run_cmd(
            INSPECT_SCRIPT,
            "--source",
            str(source_path),
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        report = json.loads(inspect_proc.stdout)
        self.assertEqual(report["sources"][0]["privacy_counts"]["private_sensitive"], 1)
        self.assertEqual(report["sources"][0]["risk_level"], "risky")
        self.assertIn("private-sensitive content dominates this source", report["sources"][0]["risks"])


if __name__ == "__main__":
    unittest.main()
