#!/usr/bin/env python3
"""Validate top-level repo docs for drift against current scripts and file maps."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from render_operator_command_docs import render_capability_index as render_capability_index_doc
    from render_operator_command_docs import render_current_flow as render_current_system_flow
    from render_operator_command_docs import render_doc_router as render_operator_doc_router
    from render_operator_command_docs import render_failure_guide as render_operator_failure_guide
    from render_operator_command_docs import load_source as load_operator_source
    from render_operator_command_docs import render_contract as render_operator_contract
    from render_operator_command_docs import render_new_maintainer as render_operator_new_maintainer
    from render_operator_command_docs import render_operator_playbook as render_playbook
    from render_operator_command_docs import render_release_checklist as render_release_readiness_checklist
    from render_operator_command_docs import render_readme as render_operator_readme
    from render_operator_command_docs import render_summary as render_operator_summary
    from validator_utils import emit_report
except ModuleNotFoundError:
    from scripts.render_operator_command_docs import render_capability_index as render_capability_index_doc
    from scripts.render_operator_command_docs import render_current_flow as render_current_system_flow
    from scripts.render_operator_command_docs import render_doc_router as render_operator_doc_router
    from scripts.render_operator_command_docs import render_failure_guide as render_operator_failure_guide
    from scripts.render_operator_command_docs import load_source as load_operator_source
    from scripts.render_operator_command_docs import render_contract as render_operator_contract
    from scripts.render_operator_command_docs import render_new_maintainer as render_operator_new_maintainer
    from scripts.render_operator_command_docs import render_operator_playbook as render_playbook
    from scripts.render_operator_command_docs import render_release_checklist as render_release_readiness_checklist
    from scripts.render_operator_command_docs import render_readme as render_operator_readme
    from scripts.render_operator_command_docs import render_summary as render_operator_summary
    from scripts.validator_utils import emit_report


REQUIRED_DOCS = [
    "README.md",
    "RELEASE_READINESS_CHECKLIST.md",
    "references/current_system_flow.md",
    "references/capability_index.md",
    "references/operator_playbook.md",
    "references/operator_command_contract.md",
    "references/operator_command_summary.md",
    "references/failure_path_guide.md",
    "references/glossary.md",
    "references/example_index.md",
    "references/doc_router.md",
    "references/new_maintainer_first_15_minutes.md",
    "references/operator_commands.json",
]

RELEASE_CHECKLIST_REQUIRED_PATTERNS = [
    "<!-- BEGIN GENERATED: release-checklist-metadata-commands -->",
    "<!-- END GENERATED: release-checklist-metadata-commands -->",
    "<!-- BEGIN GENERATED: release-checklist-validation-commands -->",
    "<!-- END GENERATED: release-checklist-validation-commands -->",
    "<!-- BEGIN GENERATED: release-checklist-handoff-items -->",
    "<!-- END GENERATED: release-checklist-handoff-items -->",
    "validate release-readiness",
    "validate workflow-blueprint",
    "tests.test_stack_discovery",
    "doctor sample-stack",
    "doctor current-stack",
    "doctor latest-stack --explain",
    "validate latest-stack",
    "explain latest-stack",
]

README_REQUIRED_PATTERNS = [
    "## 三种典型使用场景",
    "| 你现在要的是什么 | 先看哪段 | 主产物 |",
    "<!-- BEGIN GENERATED: operator-command-quickstart -->",
    "<!-- END GENERATED: operator-command-quickstart -->",
    "<!-- BEGIN GENERATED: operator-command-coverage -->",
    "<!-- END GENERATED: operator-command-coverage -->",
    "doctor sample-stack",
    "doctor current-stack",
    "doctor latest-stack",
    "validate latest-stack",
    "explain latest-stack",
    "diff stack",
    "validate release-readiness",
    "references/current_system_flow.md",
    "references/capability_index.md",
    "operator_command_summary.md",
    "operator_command_contract.md",
    "doc_router.md",
    "new_maintainer_first_15_minutes.md",
]

CURRENT_FLOW_REQUIRED_PATTERNS = [
    "## 6. 常见入口选择",
    "<!-- BEGIN GENERATED: current-flow-entry-choices -->",
    "<!-- END GENERATED: current-flow-entry-choices -->",
    "<!-- BEGIN GENERATED: current-flow-operator-route -->",
    "<!-- END GENERATED: current-flow-operator-route -->",
    "### 最短命令示例",
    "<!-- BEGIN GENERATED: current-flow-short-examples -->",
    "<!-- END GENERATED: current-flow-short-examples -->",
    "<!-- BEGIN GENERATED: current-flow-operator-chain -->",
    "<!-- END GENERATED: current-flow-operator-chain -->",
    "## 7. 各层停点与续跑点",
    "<!-- BEGIN GENERATED: current-flow-persona-stops -->",
    "<!-- END GENERATED: current-flow-persona-stops -->",
    "<!-- BEGIN GENERATED: current-flow-pipeline-stops -->",
    "<!-- END GENERATED: current-flow-pipeline-stops -->",
    "<!-- BEGIN GENERATED: current-flow-runtime-stops -->",
    "<!-- END GENERATED: current-flow-runtime-stops -->",
    "<!-- BEGIN GENERATED: current-flow-operator-stops -->",
    "<!-- END GENERATED: current-flow-operator-stops -->",
    "<!-- BEGIN GENERATED: current-flow-persona-resume -->",
    "<!-- END GENERATED: current-flow-persona-resume -->",
    "<!-- BEGIN GENERATED: current-flow-pipeline-resume -->",
    "<!-- END GENERATED: current-flow-pipeline-resume -->",
    "<!-- BEGIN GENERATED: current-flow-runtime-resume -->",
    "<!-- END GENERATED: current-flow-runtime-resume -->",
    "<!-- BEGIN GENERATED: current-flow-operator-resume -->",
    "<!-- END GENERATED: current-flow-operator-resume -->",
    "## 8. 关键文件速查",
    "<!-- BEGIN GENERATED: current-flow-persona-files -->",
    "<!-- END GENERATED: current-flow-persona-files -->",
    "<!-- BEGIN GENERATED: current-flow-workflow-files -->",
    "<!-- END GENERATED: current-flow-workflow-files -->",
    "<!-- BEGIN GENERATED: current-flow-operator-files -->",
    "<!-- END GENERATED: current-flow-operator-files -->",
    "failure_path_guide.md",
    "glossary.md",
    "example_index.md",
    "operator_command_summary.md",
    "operator_command_contract.md",
    "doc_router.md",
    "new_maintainer_first_15_minutes.md",
    "refresh_workflow_runtime_bundle.py",
    "workflow_runtime_manifest.json",
    "workflow_task_state.yaml",
]

CAPABILITY_INDEX_REQUIRED_PATTERNS = [
    "<!-- BEGIN GENERATED: capability-index-operator-entry -->",
    "<!-- END GENERATED: capability-index-operator-entry -->",
    "<!-- BEGIN GENERATED: capability-index-operator-capabilities -->",
    "<!-- END GENERATED: capability-index-operator-capabilities -->",
    "<!-- BEGIN GENERATED: capability-index-recent-release-behavior -->",
    "<!-- END GENERATED: capability-index-recent-release-behavior -->",
    "references/current_system_flow.md",
    "references/operator_command_summary.md",
    "references/operator_command_contract.md",
    "references/failure_path_guide.md",
    "references/glossary.md",
    "references/example_index.md",
    "references/doc_router.md",
    "references/new_maintainer_first_15_minutes.md",
]

OPERATOR_PLAYBOOK_REQUIRED_PATTERNS = [
    "## Release Readiness",
    "<!-- BEGIN GENERATED: operator-playbook-daily-path -->",
    "<!-- END GENERATED: operator-playbook-daily-path -->",
    "<!-- BEGIN GENERATED: operator-playbook-release-core -->",
    "<!-- END GENERATED: operator-playbook-release-core -->",
    "<!-- BEGIN GENERATED: operator-playbook-release-behavior -->",
    "<!-- END GENERATED: operator-playbook-release-behavior -->",
    "<!-- BEGIN GENERATED: operator-playbook-release-variants -->",
    "<!-- END GENERATED: operator-playbook-release-variants -->",
    "<!-- BEGIN GENERATED: operator-playbook-refresh-entry -->",
    "<!-- END GENERATED: operator-playbook-refresh-entry -->",
    "operator_command_summary.md",
    "operator_command_contract.md",
    "validate_repo_docs.py --format json",
    "validate release-readiness",
    "refresh_working_clone_bundle.py",
    "refresh_workflow_blueprint_pipeline.py",
    "refresh_workflow_runtime_bundle.py",
    "new_maintainer_first_15_minutes.md",
]

OPERATOR_COMMAND_CONTRACT_REQUIRED_PATTERNS = [
    "## Canonical Commands",
    "## Daily Stack Commands",
    "## Release Commands",
    "Generated from references/operator_commands.json",
    "validate_repo_docs.py --format json",
    "rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack",
    "doctor sample-stack",
    "doctor current-stack",
    "doctor latest-stack --explain",
    "validate latest-stack",
    "explain latest-stack",
    "diff stack",
    "validate release-readiness",
]

OPERATOR_COMMAND_SUMMARY_REQUIRED_PATTERNS = [
    "## 最常用的 4 条命令",
    "## 常见 Stack 级入口",
    "Generated from references/operator_commands.json",
    "operator_commands.json",
    "operator_command_contract.md",
    "operator_playbook.md",
    "new_maintainer_first_15_minutes.md",
]

FAILURE_GUIDE_REQUIRED_PATTERNS = [
    "## 1. 人格层常见失败点",
    "## 2. Workflow 常见失败点",
    "## 3. Release / Operator 常见失败点",
    "## 4. 常用失败命令速查",
    "<!-- BEGIN GENERATED: failure-guide-personal-empty-inspect -->",
    "<!-- END GENERATED: failure-guide-personal-empty-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-personal-empty-next-steps -->",
    "<!-- END GENERATED: failure-guide-personal-empty-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-next-interview-inspect -->",
    "<!-- END GENERATED: failure-guide-next-interview-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-next-interview-next-steps -->",
    "<!-- END GENERATED: failure-guide-next-interview-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-eval-draft-inspect -->",
    "<!-- END GENERATED: failure-guide-eval-draft-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-eval-draft-next-steps -->",
    "<!-- END GENERATED: failure-guide-eval-draft-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-release-inspect -->",
    "<!-- END GENERATED: failure-guide-release-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-release-next-steps -->",
    "<!-- END GENERATED: failure-guide-release-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-inspect -->",
    "<!-- END GENERATED: failure-guide-workflow-blocker-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-commands -->",
    "<!-- END GENERATED: failure-guide-workflow-blocker-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-blueprint-reasons -->",
    "<!-- END GENERATED: failure-guide-blueprint-reasons -->",
    "<!-- BEGIN GENERATED: failure-guide-blueprint-next-steps -->",
    "<!-- END GENERATED: failure-guide-blueprint-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-blueprint-commands -->",
    "<!-- END GENERATED: failure-guide-blueprint-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-personal-empty-commands -->",
    "<!-- END GENERATED: failure-guide-personal-empty-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-inspect -->",
    "<!-- END GENERATED: failure-guide-stage-confirmation-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-next-steps -->",
    "<!-- END GENERATED: failure-guide-workflow-blocker-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-next-interview-commands -->",
    "<!-- END GENERATED: failure-guide-next-interview-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-eval-draft-commands -->",
    "<!-- END GENERATED: failure-guide-eval-draft-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-next-steps -->",
    "<!-- END GENERATED: failure-guide-stage-confirmation-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-blueprint-inspect -->",
    "<!-- END GENERATED: failure-guide-blueprint-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-commands -->",
    "<!-- END GENERATED: failure-guide-stage-confirmation-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-runtime-inspect -->",
    "<!-- END GENERATED: failure-guide-runtime-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-runtime-next-steps -->",
    "<!-- END GENERATED: failure-guide-runtime-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-runtime-commands -->",
    "<!-- END GENERATED: failure-guide-runtime-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-quick-reference -->",
    "<!-- END GENERATED: failure-guide-quick-reference -->",
    "<!-- BEGIN GENERATED: failure-guide-reading-order -->",
    "<!-- END GENERATED: failure-guide-reading-order -->",
    "<!-- BEGIN GENERATED: failure-guide-release-commands -->",
    "<!-- END GENERATED: failure-guide-release-commands -->",
    "<!-- BEGIN GENERATED: failure-guide-latest-stack-inspect -->",
    "<!-- END GENERATED: failure-guide-latest-stack-inspect -->",
    "<!-- BEGIN GENERATED: failure-guide-latest-stack-next-steps -->",
    "<!-- END GENERATED: failure-guide-latest-stack-next-steps -->",
    "<!-- BEGIN GENERATED: failure-guide-latest-stack-commands -->",
    "<!-- END GENERATED: failure-guide-latest-stack-commands -->",
    "release-logs/",
    "workflow_interview.md",
    "eval_report.md",
    "refresh_working_clone_bundle.py",
    "refresh_workflow_blueprint_pipeline.py",
    "validate release-readiness",
    "validate workflow-blueprint",
    "doctor latest-stack --explain",
    "explain latest-stack",
]

GLOSSARY_REQUIRED_TERMS = [
    "`persona-only`",
    "`persona-plus-workflow`",
    "`working bundle`",
    "`workflow blueprint pipeline`",
    "`workflow runtime bundle`",
    "`personal clone skill`",
    "`workflow clone skill`",
    "`target_work_unit`",
    "`coherent stack`",
    "`stack_ref`",
    "`sample-stack`",
    "`current-stack`",
    "`latest-stack`",
    "`release-readiness`",
]

EXAMPLE_INDEX_REQUIRED_PATTERNS = [
    "examples/ai_engineer",
    "interview_filled.md",
    "workflow_interview_filled.md",
    "mind_profile.md",
    "system_prompt.md",
    "eval_report.md",
    "workflow_blueprint.md",
    "personal_clone_skill_SKILL.md",
    "workflow_clone_skill_SKILL.md",
]

DOC_ROUTER_REQUIRED_PATTERNS = [
    "## 按问题找文档",
    "<!-- BEGIN GENERATED: doc-router-question-table -->",
    "<!-- END GENERATED: doc-router-question-table -->",
    "## 3 条最短阅读路径",
    "<!-- BEGIN GENERATED: doc-router-user-value-path -->",
    "<!-- END GENERATED: doc-router-user-value-path -->",
    "<!-- BEGIN GENERATED: doc-router-workflow-path -->",
    "<!-- END GENERATED: doc-router-workflow-path -->",
    "<!-- BEGIN GENERATED: doc-router-maintainer-reading-path -->",
    "<!-- END GENERATED: doc-router-maintainer-reading-path -->",
    "## 如果你只愿意先读一份",
    "<!-- BEGIN GENERATED: doc-router-single-read -->",
    "<!-- END GENERATED: doc-router-single-read -->",
    "current_system_flow.md",
    "failure_path_guide.md",
    "glossary.md",
    "example_index.md",
    "operator_command_summary.md",
    "operator_playbook.md",
    "operator_command_contract.md",
    "new_maintainer_first_15_minutes.md",
    "RELEASE_READINESS_CHECKLIST.md",
]

NEW_MAINTAINER_REQUIRED_PATTERNS = [
    "## 0-5 分钟：先建立地图",
    "<!-- BEGIN GENERATED: new-maintainer-map-reading -->",
    "<!-- END GENERATED: new-maintainer-map-reading -->",
    "<!-- BEGIN GENERATED: new-maintainer-map-goals -->",
    "<!-- END GENERATED: new-maintainer-map-goals -->",
    "## 5-10 分钟：先确认仓库是绿的",
    "## 10-15 分钟：跑一遍 operator 主链路",
    "<!-- BEGIN GENERATED: new-maintainer-preflight -->",
    "<!-- END GENERATED: new-maintainer-preflight -->",
    "<!-- BEGIN GENERATED: new-maintainer-operator-path -->",
    "<!-- END GENERATED: new-maintainer-operator-path -->",
    "<!-- BEGIN GENERATED: new-maintainer-confirm -->",
    "<!-- END GENERATED: new-maintainer-confirm -->",
    "<!-- BEGIN GENERATED: new-maintainer-failure-steps -->",
    "<!-- END GENERATED: new-maintainer-failure-steps -->",
    "<!-- BEGIN GENERATED: new-maintainer-after-15 -->",
    "<!-- END GENERATED: new-maintainer-after-15 -->",
    "doc_router.md",
    "operator_command_summary.md",
    "operator_command_contract.md",
    "validate_repo_docs.py --format json",
    "rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack",
    "doctor latest-stack --explain",
    "validate release-readiness",
    "current_system_flow.md",
    "failure_path_guide.md",
]

EXAMPLE_FILES = [
    "interview_filled.md",
    "workflow_interview_filled.md",
    "mind_profile.md",
    "system_prompt.md",
    "eval_report.md",
    "research_digest.md",
    "workflow_blueprint.md",
    "personal_clone_skill_SKILL.md",
    "workflow_clone_skill_SKILL.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate top-level repo docs for drift.")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def missing_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if pattern not in text]


def extract_script_refs(text: str) -> list[str]:
    return sorted(set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.py", text)))


def find_pattern_order_issues(text: str, patterns: list[str], label: str) -> list[str]:
    issues: list[str] = []
    positions: list[tuple[str, int]] = []
    for pattern in patterns:
        idx = text.find(pattern)
        if idx < 0:
            issues.append(f"{label}: missing {pattern}")
        else:
            positions.append((pattern, idx))
    for idx in range(1, len(positions)):
        current_pattern, current_pos = positions[idx]
        previous_pattern, previous_pos = positions[idx - 1]
        if current_pos < previous_pos:
            issues.append(f"{label}: {current_pattern} appears before {previous_pattern}")
    return issues


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parent.parent

    docs: dict[str, Path] = {path: repo_root / path for path in REQUIRED_DOCS}
    missing_docs = [path for path, full_path in docs.items() if not full_path.exists()]
    texts = {
        path: full_path.read_text(encoding="utf-8") if full_path.exists() else ""
        for path, full_path in docs.items()
    }

    release_checklist_missing = missing_patterns(texts["RELEASE_READINESS_CHECKLIST.md"], RELEASE_CHECKLIST_REQUIRED_PATTERNS)
    readme_missing = missing_patterns(texts["README.md"], README_REQUIRED_PATTERNS)
    current_flow_missing = missing_patterns(texts["references/current_system_flow.md"], CURRENT_FLOW_REQUIRED_PATTERNS)
    capability_missing = missing_patterns(texts["references/capability_index.md"], CAPABILITY_INDEX_REQUIRED_PATTERNS)
    operator_playbook_missing = missing_patterns(
        texts["references/operator_playbook.md"], OPERATOR_PLAYBOOK_REQUIRED_PATTERNS
    )
    operator_command_contract_missing = missing_patterns(
        texts["references/operator_command_contract.md"], OPERATOR_COMMAND_CONTRACT_REQUIRED_PATTERNS
    )
    operator_command_summary_missing = missing_patterns(
        texts["references/operator_command_summary.md"], OPERATOR_COMMAND_SUMMARY_REQUIRED_PATTERNS
    )
    failure_guide_missing = missing_patterns(texts["references/failure_path_guide.md"], FAILURE_GUIDE_REQUIRED_PATTERNS)
    glossary_missing = missing_patterns(texts["references/glossary.md"], GLOSSARY_REQUIRED_TERMS)
    example_index_missing = missing_patterns(texts["references/example_index.md"], EXAMPLE_INDEX_REQUIRED_PATTERNS)
    doc_router_missing = missing_patterns(texts["references/doc_router.md"], DOC_ROUTER_REQUIRED_PATTERNS)
    new_maintainer_missing = missing_patterns(
        texts["references/new_maintainer_first_15_minutes.md"], NEW_MAINTAINER_REQUIRED_PATTERNS
    )
    release_order_issues = find_pattern_order_issues(
        texts["references/current_system_flow.md"],
        [
            "validate_repo_docs",
            "rebuild_sample_stack",
            "doctor sample-stack",
            "doctor current-stack",
            "doctor latest-stack --explain",
            "validate latest-stack",
            "explain latest-stack",
            "validate release-readiness",
        ],
        "current_system_flow operator chain",
    ) + find_pattern_order_issues(
        texts["references/new_maintainer_first_15_minutes.md"],
        [
            "validate_repo_docs.py --format json",
            "rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack",
            "doctor sample-stack",
            "doctor latest-stack --explain",
            "validate release-readiness",
        ],
        "new_maintainer operator path",
    )

    operator_source = load_operator_source(repo_root / "references" / "operator_commands.json")
    operator_contract_render_mismatch = (
        texts["references/operator_command_contract.md"] != render_operator_contract(operator_source)
    )
    operator_summary_render_mismatch = (
        texts["references/operator_command_summary.md"] != render_operator_summary(operator_source)
    )
    try:
        capability_index_render_mismatch = (
            texts["references/capability_index.md"]
            != render_capability_index_doc(operator_source, texts["references/capability_index.md"])
        )
    except SystemExit:
        capability_index_render_mismatch = True
    try:
        release_checklist_render_mismatch = (
            texts["RELEASE_READINESS_CHECKLIST.md"]
            != render_release_readiness_checklist(operator_source, texts["RELEASE_READINESS_CHECKLIST.md"])
        )
    except SystemExit:
        release_checklist_render_mismatch = True
    try:
        current_flow_render_mismatch = (
            texts["references/current_system_flow.md"]
            != render_current_system_flow(operator_source, texts["references/current_system_flow.md"])
        )
    except SystemExit:
        current_flow_render_mismatch = True
    try:
        operator_playbook_render_mismatch = (
            texts["references/operator_playbook.md"]
            != render_playbook(operator_source, texts["references/operator_playbook.md"])
        )
    except SystemExit:
        operator_playbook_render_mismatch = True
    try:
        new_maintainer_operator_render_mismatch = (
            texts["references/new_maintainer_first_15_minutes.md"]
            != render_operator_new_maintainer(operator_source, texts["references/new_maintainer_first_15_minutes.md"])
        )
    except SystemExit:
        new_maintainer_operator_render_mismatch = True
    try:
        operator_readme_render_mismatch = texts["README.md"] != render_operator_readme(operator_source, texts["README.md"])
    except SystemExit:
        operator_readme_render_mismatch = True
    try:
        doc_router_render_mismatch = (
            texts["references/doc_router.md"] != render_operator_doc_router(operator_source, texts["references/doc_router.md"])
        )
    except SystemExit:
        doc_router_render_mismatch = True
    try:
        failure_guide_render_mismatch = (
            texts["references/failure_path_guide.md"]
            != render_operator_failure_guide(operator_source, texts["references/failure_path_guide.md"])
        )
    except SystemExit:
        failure_guide_render_mismatch = True

    script_refs = sorted(
        set(
            extract_script_refs(texts["README.md"])
            + extract_script_refs(texts["RELEASE_READINESS_CHECKLIST.md"])
            + extract_script_refs(texts["references/current_system_flow.md"])
            + extract_script_refs(texts["references/capability_index.md"])
            + extract_script_refs(texts["references/operator_playbook.md"])
            + extract_script_refs(texts["references/operator_command_contract.md"])
            + extract_script_refs(texts["references/failure_path_guide.md"])
            + extract_script_refs(texts["references/doc_router.md"])
            + extract_script_refs(texts["references/new_maintainer_first_15_minutes.md"])
        )
    )
    missing_script_refs = [ref for ref in script_refs if not (repo_root / ref).exists()]

    example_root = repo_root / "examples" / "ai_engineer"
    missing_example_files = [name for name in EXAMPLE_FILES if not (example_root / name).exists()]

    report = {
        "docs_exist": not missing_docs,
        "missing_docs": missing_docs,
        "release_checklist_missing_patterns": release_checklist_missing,
        "readme_missing_patterns": readme_missing,
        "current_flow_missing_patterns": current_flow_missing,
        "capability_index_missing_patterns": capability_missing,
        "operator_playbook_missing_patterns": operator_playbook_missing,
        "operator_command_contract_missing_patterns": operator_command_contract_missing,
        "operator_command_summary_missing_patterns": operator_command_summary_missing,
        "failure_guide_missing_patterns": failure_guide_missing,
        "glossary_missing_terms": glossary_missing,
        "example_index_missing_patterns": example_index_missing,
        "doc_router_missing_patterns": doc_router_missing,
        "new_maintainer_missing_patterns": new_maintainer_missing,
        "release_readiness_order_issues": release_order_issues,
        "capability_index_render_mismatch": capability_index_render_mismatch,
        "release_checklist_render_mismatch": release_checklist_render_mismatch,
        "current_flow_render_mismatch": current_flow_render_mismatch,
        "readme_operator_render_mismatch": operator_readme_render_mismatch,
        "operator_playbook_render_mismatch": operator_playbook_render_mismatch,
        "new_maintainer_operator_render_mismatch": new_maintainer_operator_render_mismatch,
        "doc_router_render_mismatch": doc_router_render_mismatch,
        "failure_guide_render_mismatch": failure_guide_render_mismatch,
        "operator_command_contract_render_mismatch": operator_contract_render_mismatch,
        "operator_command_summary_render_mismatch": operator_summary_render_mismatch,
        "missing_script_refs": missing_script_refs,
        "missing_example_files": missing_example_files,
    }
    report["ok"] = bool(
        report["docs_exist"]
        and not release_checklist_missing
        and not readme_missing
        and not current_flow_missing
        and not capability_missing
        and not operator_playbook_missing
        and not operator_command_contract_missing
        and not operator_command_summary_missing
        and not failure_guide_missing
        and not glossary_missing
        and not example_index_missing
        and not doc_router_missing
        and not new_maintainer_missing
        and not release_order_issues
        and not capability_index_render_mismatch
        and not release_checklist_render_mismatch
        and not current_flow_render_mismatch
        and not operator_readme_render_mismatch
        and not operator_playbook_render_mismatch
        and not new_maintainer_operator_render_mismatch
        and not doc_router_render_mismatch
        and not failure_guide_render_mismatch
        and not operator_contract_render_mismatch
        and not operator_summary_render_mismatch
        and not missing_script_refs
        and not missing_example_files
    )
    emit_report(report, as_json=args.format == "json")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
