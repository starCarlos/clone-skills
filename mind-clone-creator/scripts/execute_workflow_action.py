#!/usr/bin/env python3
"""Execute or materialize the current workflow action plan."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from profession_adapter_runtime import resolve_profession_adapter


REPO_KEYWORDS = ("代码仓库", "repo", "repository", "git")
DOC_KEYWORDS = ("文档", "im", "聊天", "会议")
TASK_KEYWORDS = ("任务系统", "task")
TEST_KEYWORDS = ("测试", "评估")
NOTEBOOK_KEYWORDS = ("notebook", "脚本")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("action plan must be a JSON object")
    return data


def run_command(command: list[str], workdir: Path, timeout: int = 10) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "command": command, "error": str(exc)}
    return {
        "status": "executed" if proc.returncode == 0 else "failed",
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def summarize_output(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    kept = lines[:max_lines]
    suffix = "" if len(lines) <= max_lines else f"\n... ({len(lines) - max_lines} more lines)"
    return "\n".join(kept) + suffix


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_rg_files(patterns: list[str], workdir: Path, timeout: int = 10) -> dict[str, Any]:
    if not command_exists("rg"):
        return {"status": "error", "stdout": "", "stderr": "rg not installed", "command": ["rg"]}
    command = ["rg", "--files"]
    for pattern in patterns:
        command.extend(["-g", pattern])
    return run_command(command, workdir, timeout=timeout)


def compact_lines(text: str, limit: int = 20) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[:limit]


def ensure_command_list(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    commands: list[list[str]] = []
    for item in value:
        if isinstance(item, list) and item:
            commands.append([str(part) for part in item if str(part).strip()])
    return commands


def detect_repo_profile(workdir: Path, profession: str = "") -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "detect_repo_execution_profile.py"
    with tempfile.TemporaryDirectory(prefix="repo-profile-") as tmpdir:
        output = Path(tmpdir) / "repo_profile.json"
        command = ["python3", str(script), "--workspace", str(workdir), "--output", str(output)]
        if profession.strip():
            command.extend(["--profession", profession])
        proc = subprocess.run(
            command,
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not output.exists():
            return {"repo_type": ["unknown"], "evidence": [], "test_command_candidates": [], "run_command_candidates": []}
        with output.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {"repo_type": ["unknown"], "evidence": [], "test_command_candidates": [], "run_command_candidates": []}


def bullet_lines(items: list[Any], default: str) -> str:
    clean = [str(item).strip() for item in items if str(item).strip()]
    if not clean:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in clean)


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_template(path: Path, values: dict[str, str]) -> str:
    return load_template(path).format(**values)


def safe_filename(text: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in text.strip().lower())
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    return sanitized.strip("-") or "artifact"


def build_template_values(action_plan: dict[str, Any]) -> dict[str, str]:
    next_execution = action_plan.get("next_execution", [])
    next_lines = []
    if isinstance(next_execution, list):
        for item in next_execution:
            if isinstance(item, dict):
                step = item.get("step", "")
                action = item.get("action", "")
                next_lines.append(f"- {step}. {action}".strip())
    return {
        "current_stage": str(action_plan.get("current_stage", "")).strip() or "未命名阶段",
        "task_title": str(action_plan.get("current_stage", "")).strip() or "workflow-task",
        "objective": str(action_plan.get("objective", "")).strip() or "暂无",
        "read_items": bullet_lines(action_plan.get("read", []), "暂无"),
        "produce_items": bullet_lines(action_plan.get("produce", []), "暂无"),
        "required_inputs": bullet_lines(action_plan.get("required_inputs", []), "暂无"),
        "expected_outputs": bullet_lines(action_plan.get("expected_outputs", []), "暂无"),
        "next_execution": "\n".join(next_lines) if next_lines else "- 暂无",
        "save_target": str(action_plan.get("save", "")).strip() or "未指定",
    }


def match_tool_override(tool_name: str, adapter: dict[str, Any]) -> dict[str, Any]:
    execution_overrides = adapter.get("execution_overrides", {}) if isinstance(adapter, dict) else {}
    tool_preferences = execution_overrides.get("tool_preferences", {}) if isinstance(execution_overrides, dict) else {}
    if not isinstance(tool_preferences, dict):
        return {}
    for key, value in tool_preferences.items():
        if key in tool_name or tool_name in key:
            return value if isinstance(value, dict) else {}
    return {}


def match_artifact_template(tool_name: str, adapter: dict[str, Any], default_template: str) -> str:
    execution_overrides = adapter.get("execution_overrides", {}) if isinstance(adapter, dict) else {}
    templates = execution_overrides.get("artifact_templates", {}) if isinstance(execution_overrides, dict) else {}
    if not isinstance(templates, dict):
        return default_template
    for key, value in templates.items():
        if key in tool_name or tool_name in key:
            return str(value).strip() or default_template
    return default_template


def materialize_markdown_artifact(
    tool_name: str,
    action_plan: dict[str, Any],
    workspace: Path,
    artifact_dir: Path,
    template_name: str,
) -> dict[str, Any]:
    template_path = workspace / "templates" / template_name
    if not template_path.exists():
        return plan_manual({"tool_name": tool_name}, f"模板不存在：{template_name}", action_plan)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    suffix = "note" if "clarification" in template_name else "task-card"
    filename = f"{safe_filename(str(action_plan.get('current_stage', 'stage')))}-{suffix}.md"
    output_path = artifact_dir / filename
    output_path.write_text(render_template(template_path, build_template_values(action_plan)), encoding="utf-8")
    return {
        "tool_name": tool_name,
        "mode": "file_artifact",
        "status": "executed",
        "artifact_path": str(output_path),
        "reason": "已生成本地 Markdown artifact，作为文档/任务系统的文件化替代",
    }


def trim_repo_artifacts(artifacts: dict[str, Any], preferred_keys: list[str]) -> dict[str, Any]:
    if not preferred_keys:
        return artifacts
    trimmed = {}
    for key in preferred_keys:
        if key in artifacts:
            trimmed[key] = artifacts[key]
    for key, value in artifacts.items():
        if key not in trimmed:
            trimmed[key] = value
    return trimmed


def contains_keyword(name: str, keywords: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def plan_manual(tool: dict[str, Any], reason: str, action_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool.get("tool_name", ""),
        "mode": "manual",
        "status": "pending_manual",
        "reason": reason,
        "expected_input": tool.get("expected_input", ""),
        "expected_output": tool.get("expected_output", ""),
        "suggested_action": {
            "read": action_plan.get("read", []),
            "produce": action_plan.get("produce", []),
            "save": action_plan.get("save", ""),
        },
    }


def execute_tool(
    tool: dict[str, Any],
    action_plan: dict[str, Any],
    workdir: Path,
    artifact_dir: Path,
    adapter: dict[str, Any],
    profession: str,
    execute_safe: bool,
) -> dict[str, Any]:
    tool_name = str(tool.get("tool_name", "")).strip()
    if not tool_name:
        return plan_manual(tool, "未命名工具，无法执行", action_plan)
    tool_override = match_tool_override(tool_name, adapter)

    if contains_keyword(tool_name, DOC_KEYWORDS):
        if not execute_safe:
            return plan_manual(tool, "文档/聊天类工具需要人工或外部系统接入", action_plan)
        return materialize_markdown_artifact(
            tool_name,
            action_plan,
            workdir,
            artifact_dir,
            match_artifact_template(tool_name, adapter, "workflow_clarification_note_template.md"),
        )

    if contains_keyword(tool_name, TASK_KEYWORDS):
        if not execute_safe:
            return plan_manual(tool, "任务系统未接入 API，先输出人工执行项", action_plan)
        return materialize_markdown_artifact(
            tool_name,
            action_plan,
            workdir,
            artifact_dir,
            match_artifact_template(tool_name, adapter, "workflow_task_card_template.md"),
        )

    if contains_keyword(tool_name, REPO_KEYWORDS):
        if not execute_safe:
            return {
                "tool_name": tool_name,
                "mode": "safe_command_preview",
                "status": "planned",
                "commands": [
                    ["git", "status", "--short"],
                    ["git", "branch", "--show-current"],
                ],
                "reason": "未开启 --execute-safe，仅输出安全命令预览",
            }
        git_dir = run_command(["git", "rev-parse", "--is-inside-work-tree"], workdir)
        if git_dir.get("status") != "executed" or "true" not in git_dir.get("stdout", ""):
            return plan_manual(tool, "当前目录不是 git 仓库，无法执行仓库检查", action_plan)
        status = run_command(["git", "status", "--short"], workdir)
        branch = run_command(["git", "branch", "--show-current"], workdir)
        diff_stat = run_command(["git", "diff", "--stat"], workdir)
        tracked_files = run_rg_files(["*.py", "*.md", "*.yaml", "*.yml"], workdir)
        repo_profile = detect_repo_profile(workdir, profession)
        artifacts = {
            "git_status": summarize_output(status.get("stdout", "")),
            "git_branch": summarize_output(branch.get("stdout", "")),
            "git_diff_stat": summarize_output(diff_stat.get("stdout", "")),
            "file_candidates": compact_lines(tracked_files.get("stdout", "")),
            "repo_profile": repo_profile,
        }
        preferred_artifacts = tool_override.get("prefer_collect_artifacts", []) if isinstance(tool_override.get("prefer_collect_artifacts", []), list) else []
        return {
            "tool_name": tool_name,
            "mode": "safe_execute",
            "status": "executed",
            "artifacts": trim_repo_artifacts(artifacts, preferred_artifacts),
            "commands": [
                status.get("command", []),
                branch.get("command", []),
                diff_stat.get("command", []),
                tracked_files.get("command", []),
            ],
        }

    if contains_keyword(tool_name, TEST_KEYWORDS):
        if not execute_safe:
            repo_profile = detect_repo_profile(workdir, profession)
            return {
                "tool_name": tool_name,
                "mode": "safe_command_preview",
                "status": "planned",
                "commands": ensure_command_list(repo_profile.get("test_command_candidates", [])) or [["pytest", "--collect-only", "-q"]],
                "reason": "未开启 --execute-safe，仅输出测试收集命令预览",
            }
        repo_profile = detect_repo_profile(workdir, profession)
        test_files = run_rg_files(["*test*.py", "test_*.py", "*_test.py"], workdir)
        test_candidates = ensure_command_list(repo_profile.get("test_command_candidates", []))
        attempted_commands: list[dict[str, Any]] = []
        last_result = None
        for candidate in test_candidates:
            if shutil.which(candidate[0]) is not None:
                result = run_command(candidate, workdir, timeout=20)
                last_result = result
                attempted_commands.append(
                    {
                        "command": result.get("command", []),
                        "status": result.get("status", ""),
                        "returncode": result.get("returncode"),
                    }
                )
                if result.get("status") == "executed":
                    return {
                        "tool_name": tool_name,
                        "mode": "safe_execute",
                        "status": result.get("status", ""),
                        "artifacts": {
                            "attempted_commands": attempted_commands,
                            "test_command_output": summarize_output(result.get("stdout", "") or result.get("stderr", "")),
                            "test_file_candidates": compact_lines(test_files.get("stdout", "")),
                            "repo_profile": repo_profile,
                        },
                        "commands": [item["command"] for item in attempted_commands] + [test_files.get("command", [])],
                    }
                if not tool_override.get("retry_fallback_candidates", False):
                    break
            else:
                attempted_commands.append(
                    {
                        "command": candidate,
                        "status": "missing_binary",
                    }
                )
        if attempted_commands and last_result is not None:
            return {
                "tool_name": tool_name,
                "mode": "safe_execute",
                "status": last_result.get("status", ""),
                "artifacts": {
                    "attempted_commands": attempted_commands,
                    "test_command_output": summarize_output(last_result.get("stdout", "") or last_result.get("stderr", "")),
                    "test_file_candidates": compact_lines(test_files.get("stdout", "")),
                    "repo_profile": repo_profile,
                },
                "commands": [item["command"] for item in attempted_commands if isinstance(item.get("command"), list)] + [test_files.get("command", [])],
            }
        if test_files.get("status") == "executed" and test_files.get("stdout", "").strip():
            return {
                "tool_name": tool_name,
                "mode": "safe_discovery",
                "status": "executed",
                "artifacts": {
                    "attempted_commands": attempted_commands,
                    "test_file_candidates": compact_lines(test_files.get("stdout", "")),
                    "repo_profile": repo_profile,
                },
                "reason": "已发现测试文件，但环境中没有可直接执行的候选测试命令",
                "commands": [item["command"] for item in attempted_commands if isinstance(item.get("command"), list)] + [test_files.get("command", [])],
            }
        return {
            **plan_manual(tool, "环境里没有可执行的候选测试命令", action_plan),
            "artifacts": {
                "attempted_commands": attempted_commands,
                "test_file_candidates": compact_lines(test_files.get("stdout", "")),
                "repo_profile": repo_profile,
            },
        }

    if contains_keyword(tool_name, NOTEBOOK_KEYWORDS):
        if not execute_safe:
            return {
                "tool_name": tool_name,
                "mode": "safe_command_preview",
                "status": "planned",
                "commands": [["rg", "--files", "-g", "*.ipynb", "-g", "*.py"]],
                "reason": "未开启 --execute-safe，仅输出脚本发现命令预览",
            }
        notebooks = run_rg_files(["*.ipynb"], workdir)
        scripts = run_rg_files(["*.py"], workdir)
        return {
            "tool_name": tool_name,
            "mode": "safe_discovery",
            "status": "executed",
            "artifacts": {
                "notebook_candidates": compact_lines(notebooks.get("stdout", "")),
                "script_candidates": compact_lines(scripts.get("stdout", "")),
            },
            "reason": "已发现候选脚本/Notebook，但执行仍需要更具体路径与参数",
            "commands": [notebooks.get("command", []), scripts.get("command", [])],
        }

    return plan_manual(tool, "暂无该工具的自动执行适配器", action_plan)


def dedupe_execution_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    for item in items:
        artifact_path = str(item.get("artifact_path", "")).strip()
        if artifact_path:
            if artifact_path in seen_artifacts:
                continue
            seen_artifacts.add(artifact_path)
        deduped.append(item)
    return deduped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute workflow action plan with safe local adapters.")
    parser.add_argument("--action-plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts")
    parser.add_argument("--profession", default="")
    parser.add_argument("--execute-safe", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    action_plan = load_json(Path(args.action_plan))
    workdir = Path(args.workspace).resolve()
    if not workdir.exists():
        raise SystemExit(f"workspace not found: {workdir}")
    artifact_dir = (workdir / args.artifact_dir).resolve()
    plan_profession = str(action_plan.get("profession", "")).strip()
    recommendation_query = "；".join(
        item
        for item in [
            action_plan.get("current_stage", ""),
            action_plan.get("objective", ""),
            "、".join(action_plan.get("read", [])) if isinstance(action_plan.get("read", []), list) else "",
            "、".join(action_plan.get("produce", [])) if isinstance(action_plan.get("produce", []), list) else "",
        ]
        if isinstance(item, str) and item.strip()
    )
    resolved = resolve_profession_adapter(
        workdir,
        args.profession.strip() or plan_profession,
        fallback_query=recommendation_query,
        allow_recommendation=True,
        auto_apply_recommendation=not bool(args.profession.strip() or plan_profession),
    )
    profession = str(resolved.get("profession", "")).strip()
    adapter = resolved.get("adapter", {}) if isinstance(resolved.get("adapter", {}), dict) else {}

    tool_plan = action_plan.get("tool_plan", [])
    if not isinstance(tool_plan, list):
        tool_plan = []

    execution_items = [
        execute_tool(
            tool if isinstance(tool, dict) else {},
            action_plan,
            workdir,
            artifact_dir,
            adapter,
            profession,
            args.execute_safe,
        )
        for tool in tool_plan
    ]
    execution_items = dedupe_execution_items([item for item in execution_items if isinstance(item, dict)])

    result = {
        "current_stage": action_plan.get("current_stage", ""),
        "objective": action_plan.get("objective", ""),
        "execution_mode": "safe_execute" if args.execute_safe else "plan_only",
        "artifact_dir": str(artifact_dir),
        "profession": profession,
        "profession_input": args.profession.strip() or plan_profession,
        "profession_resolution": resolved.get("resolution", {}),
        "adapter_recommendation": resolved.get("recommendation", {}),
        "required_inputs": action_plan.get("required_inputs", []),
        "expected_outputs": action_plan.get("expected_outputs", []),
        "execution_items": execution_items,
        "next_execution": action_plan.get("next_execution", []),
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
