from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from colleague_clone_common import extract_title


SLACK_METADATA_FILES = {"users.json", "channels.json", "groups.json", "dms.json", "mpims.json"}
KNOWN_PLATFORMS = {"slack", "feishu", "dingtalk", "wechat", "generic"}
DEFAULT_FIELD_ALIASES = {
    "items": ["messages", "items", "message_list", "records", "list", "data.messages", "data.items", "result.messages"],
    "text": ["text", "content", "Content", "body", "message", "msg", "msgContent", "StrContent", "plain_text", "rich_text"],
    "speaker": ["speaker", "sender", "Sender", "author", "username", "senderName", "sender_name", "senderNick", "NickName", "nickname", "FromUserName"],
    "channel": [
        "channel",
        "channel_name",
        "channelName",
        "conversation_name",
        "conversationName",
        "conversationTitle",
        "chat_name",
        "chatName",
        "ChatName",
        "group_name",
        "room",
        "talker",
        "Talker",
    ],
    "timestamp": [
        "timestamp",
        "time",
        "ts",
        "thread_ts",
        "create_time",
        "createTime",
        "CreateTime",
        "msgCreateTime",
        "msgTime",
    ],
    "title": ["title", "subject"],
    "message_type": ["message_type", "msg_type", "MsgType", "Type", "type"],
    "top_level_channel": ["chatName", "ChatName", "talker", "Talker", "conversation_name", "conversationName", "conversationTitle"],
}
PLATFORM_SIGNAL_FIELDS = {
    "slack": ["ts", "thread_ts", "client_msg_id", "user", "text", "blocks", "attachments", "files"],
    "feishu": ["create_time", "createTime", "conversation_name", "conversationName", "chat_name", "chatName", "message_type", "sender"],
    "dingtalk": ["senderNick", "senderName", "conversationTitle", "msgCreateTime", "msgTime", "msgContent"],
    "wechat": ["StrContent", "CreateTime", "ChatName", "Talker", "Sender", "FromUserName", "NickName"],
}
EXPECTED_FIELDS_BY_PLATFORM = {
    "slack": ["text", "speaker", "channel", "timestamp"],
    "feishu": ["text", "speaker", "channel", "timestamp"],
    "dingtalk": ["text", "speaker", "channel", "timestamp"],
    "wechat": ["text", "speaker", "channel", "timestamp"],
    "generic": ["text", "timestamp"],
}


def parse_json_export_fragments(
    imported_at: str,
    path: Path,
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_payload_fragments(payload, imported_at, fallback_channel=path.stem, field_mapping=field_mapping)


def parse_workspace_export_fragments(
    imported_at: str,
    path: Path,
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    if path.is_dir() and _looks_like_slack_directory(path):
        fragments, platform = _parse_slack_directory(imported_at, path)
        diagnostics = _build_workspace_structure_diagnostics(
            platform=platform,
            mode="slack_directory_metadata",
            reason="found Slack metadata files in the export directory",
            fragments=fragments,
            field_mapping=field_mapping,
        )
        return fragments, platform, diagnostics
    if path.is_file() and path.suffix.lower() == ".zip" and _looks_like_slack_zip(path):
        fragments, platform = _parse_slack_zip(imported_at, path)
        diagnostics = _build_workspace_structure_diagnostics(
            platform=platform,
            mode="slack_zip_metadata",
            reason="found Slack metadata files in the export zip",
            fragments=fragments,
            field_mapping=field_mapping,
        )
        return fragments, platform, diagnostics
    if path.is_file() and path.suffix.lower() == ".json":
        return parse_json_export_fragments(imported_at, path, field_mapping=field_mapping)
    if path.is_dir():
        return _parse_generic_directory(imported_at, path, field_mapping=field_mapping)
    if path.is_file() and path.suffix.lower() == ".zip":
        return _parse_generic_zip(imported_at, path, field_mapping=field_mapping)
    raise ValueError(f"unsupported workspace export path: {path}")


def parse_payload_fragments(
    payload: object,
    imported_at: str,
    *,
    fallback_channel: str = "",
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    resolved_mapping = field_mapping if isinstance(field_mapping, dict) else {}
    items = _extract_message_items(payload, resolved_mapping)
    platform, detection = _detect_platform(items, resolved_mapping)
    if platform == "slack":
        fragments = _parse_slack_items(items, imported_at, channel=fallback_channel, field_mapping=resolved_mapping)
    elif platform == "feishu":
        fragments = _parse_feishu_items(items, imported_at, fallback_channel=fallback_channel, field_mapping=resolved_mapping)
    elif platform == "dingtalk":
        fragments = _parse_dingtalk_items(items, imported_at, fallback_channel=fallback_channel, field_mapping=resolved_mapping)
    elif platform == "wechat":
        payload_channel = _pick_object_value(
            payload,
            _semantic_keys(resolved_mapping, "top_level_channel") + _semantic_keys(resolved_mapping, "channel"),
            default=fallback_channel,
        )
        fragments = _parse_wechat_items(items, imported_at, fallback_channel=payload_channel, field_mapping=resolved_mapping)
    else:
        fragments = _parse_generic_items(items, imported_at, fallback_channel=fallback_channel, field_mapping=resolved_mapping)
        platform = "generic"
    diagnostics = _build_fragment_diagnostics(platform, fragments, resolved_mapping, detection)
    return fragments, platform, diagnostics


def _parse_generic_directory(
    imported_at: str,
    path: Path,
    *,
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    fragments: list[dict] = []
    platform_counts: dict[str, int] = {}
    reasons: list[str] = []
    for json_path in sorted(path.rglob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        fallback_channel = json_path.parent.name if json_path.parent != path else json_path.stem
        partial, platform, diagnostics = parse_payload_fragments(
            payload,
            imported_at,
            fallback_channel=fallback_channel,
            field_mapping=field_mapping,
        )
        if partial:
            platform_counts[platform] = platform_counts.get(platform, 0) + len(partial)
            fragments.extend(partial)
        reasons.extend(diagnostics.get("platform_detection_reasons", [])[:1])
    dominant_platform = _dominant_platform(platform_counts)
    diagnostics = _build_aggregate_diagnostics(
        platform=dominant_platform,
        fragments=fragments,
        field_mapping=field_mapping,
        mode="directory_aggregate",
        reason=f"aggregated {sum(platform_counts.values()) or 0} extracted records from directory JSON files",
        counts=platform_counts,
        extra_reasons=reasons,
    )
    return fragments, dominant_platform, diagnostics


def _parse_generic_zip(
    imported_at: str,
    path: Path,
    *,
    field_mapping: dict | None = None,
) -> tuple[list[dict], str, dict]:
    fragments: list[dict] = []
    platform_counts: dict[str, int] = {}
    reasons: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith(".json") or name.endswith("/"):
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            member_path = Path(name)
            fallback_channel = member_path.parent.name or member_path.stem
            partial, platform, diagnostics = parse_payload_fragments(
                payload,
                imported_at,
                fallback_channel=fallback_channel,
                field_mapping=field_mapping,
            )
            if partial:
                platform_counts[platform] = platform_counts.get(platform, 0) + len(partial)
                fragments.extend(partial)
            reasons.extend(diagnostics.get("platform_detection_reasons", [])[:1])
    dominant_platform = _dominant_platform(platform_counts)
    diagnostics = _build_aggregate_diagnostics(
        platform=dominant_platform,
        fragments=fragments,
        field_mapping=field_mapping,
        mode="zip_aggregate",
        reason=f"aggregated {sum(platform_counts.values()) or 0} extracted records from zip JSON files",
        counts=platform_counts,
        extra_reasons=reasons,
    )
    return fragments, dominant_platform, diagnostics


def _parse_slack_directory(imported_at: str, path: Path) -> tuple[list[dict], str]:
    user_map = _load_slack_user_map_from_directory(path)
    fragments: list[dict] = []
    for json_path in sorted(path.rglob("*.json")):
        if json_path.name in SLACK_METADATA_FILES:
            continue
        if json_path.parent == path:
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        fragments.extend(_parse_slack_items(payload, imported_at, channel=json_path.parent.name, user_map=user_map))
    return fragments, "slack"


def _parse_slack_zip(imported_at: str, path: Path) -> tuple[list[dict], str]:
    fragments: list[dict] = []
    with zipfile.ZipFile(path) as archive:
        user_map = _load_slack_user_map_from_zip(archive)
        for name in sorted(archive.namelist()):
            member_path = Path(name)
            if member_path.name in SLACK_METADATA_FILES or name.endswith("/"):
                continue
            if member_path.suffix.lower() != ".json" or len(member_path.parts) < 2:
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            fragments.extend(_parse_slack_items(payload, imported_at, channel=member_path.parent.name, user_map=user_map))
    return fragments, "slack"


def _parse_slack_items(
    payload: object,
    imported_at: str,
    *,
    channel: str = "",
    user_map: dict[str, str] | None = None,
    field_mapping: dict | None = None,
) -> list[dict]:
    items = payload if isinstance(payload, list) else _extract_message_items(payload, field_mapping)
    fragments: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _extract_text(
            _pick_object_raw_value(item, _semantic_keys(field_mapping, "text"))
            or item.get("blocks")
            or item.get("attachments")
            or item.get("files")
            or ""
        )
        speaker = _pick_first(
            _resolve_slack_user(user_map or {}, _pick_object_raw_value(item, ["user"])),
            _pick_object_value(item, _semantic_keys(field_mapping, "speaker"), default=""),
            _stringify(item.get("bot_profile", {}).get("name")) if isinstance(item.get("bot_profile"), dict) else "",
            _pick_object_raw_value(item, ["user", "bot_id"]),
            default="unknown",
        )
        timestamp = _normalize_timestamp(_pick_object_raw_value(item, _semantic_keys(field_mapping, "timestamp")), imported_at)
        resolved_channel = _pick_object_value(item, _semantic_keys(field_mapping, "channel"), default=channel)
        title = extract_title(text) or _pick_first(_pick_object_value(item, _semantic_keys(field_mapping, "title")), resolved_channel, "Slack export", default="Slack export")
        if not text.strip():
            continue
        fragments.append(
            {
                "source_type": "slack_export",
                "content_type": "message",
                "timestamp": timestamp,
                "text": text,
                "title": title,
                "speaker": speaker,
                "channel": resolved_channel,
            }
        )
    return fragments


def _parse_feishu_items(
    payload: object,
    imported_at: str,
    *,
    fallback_channel: str = "",
    field_mapping: dict | None = None,
) -> list[dict]:
    items = payload if isinstance(payload, list) else _extract_message_items(payload, field_mapping)
    fragments: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _extract_text(_pick_object_raw_value(item, _semantic_keys(field_mapping, "text")) or item)
        channel = _pick_object_value(item, _semantic_keys(field_mapping, "channel"), default=fallback_channel)
        sender = _pick_object_raw_value(item, ["sender"])
        speaker = _pick_first(
            _sender_name(sender),
            _pick_object_value(item, _semantic_keys(field_mapping, "speaker"), default=""),
            default="unknown",
        )
        timestamp = _normalize_timestamp(_pick_object_raw_value(item, _semantic_keys(field_mapping, "timestamp")), imported_at)
        title = extract_title(text) or _pick_first(_pick_object_value(item, _semantic_keys(field_mapping, "title")), channel, fallback_channel, "Feishu export", default="Feishu export")
        if not text.strip():
            continue
        fragments.append(
            {
                "source_type": "feishu_export",
                "content_type": "message",
                "timestamp": timestamp,
                "text": text,
                "title": title,
                "speaker": speaker,
                "channel": channel,
            }
        )
    return fragments


def _parse_dingtalk_items(
    payload: object,
    imported_at: str,
    *,
    fallback_channel: str = "",
    field_mapping: dict | None = None,
) -> list[dict]:
    items = payload if isinstance(payload, list) else _extract_message_items(payload, field_mapping)
    fragments: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _extract_text(_pick_object_raw_value(item, _semantic_keys(field_mapping, "text")) or item)
        channel = _pick_object_value(item, _semantic_keys(field_mapping, "channel"), default=fallback_channel)
        speaker = _pick_object_value(item, _semantic_keys(field_mapping, "speaker"), default="unknown")
        timestamp = _normalize_timestamp(_pick_object_raw_value(item, _semantic_keys(field_mapping, "timestamp")), imported_at)
        title = extract_title(text) or _pick_first(_pick_object_value(item, _semantic_keys(field_mapping, "title")), channel, "DingTalk export", default="DingTalk export")
        if not text.strip():
            continue
        fragments.append(
            {
                "source_type": "dingtalk_export",
                "content_type": "message",
                "timestamp": timestamp,
                "text": text,
                "title": title,
                "speaker": speaker,
                "channel": channel,
            }
        )
    return fragments


def _parse_wechat_items(
    payload: object,
    imported_at: str,
    *,
    fallback_channel: str = "",
    field_mapping: dict | None = None,
) -> list[dict]:
    items = payload if isinstance(payload, list) else _extract_message_items(payload, field_mapping)
    fragments: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        message_type = _pick_object_value(item, _semantic_keys(field_mapping, "message_type"), default="text").lower()
        text = _extract_text(_pick_object_raw_value(item, _semantic_keys(field_mapping, "text")) or item)
        if message_type not in {"text", "1", "message"} and not text.strip():
            continue
        speaker = _pick_object_value(item, _semantic_keys(field_mapping, "speaker"), default="unknown")
        channel = _pick_object_value(item, _semantic_keys(field_mapping, "channel"), default=fallback_channel)
        timestamp = _normalize_timestamp(_pick_object_raw_value(item, _semantic_keys(field_mapping, "timestamp")), imported_at)
        title = extract_title(text) or _pick_first(_pick_object_value(item, _semantic_keys(field_mapping, "title")), channel, "WeChat export", default="WeChat export")
        if not text.strip():
            continue
        fragments.append(
            {
                "source_type": "wechat_export",
                "content_type": "message",
                "timestamp": timestamp,
                "text": text,
                "title": title,
                "speaker": speaker,
                "channel": channel,
            }
        )
    return fragments


def _parse_generic_items(
    payload: object,
    imported_at: str,
    *,
    fallback_channel: str = "",
    field_mapping: dict | None = None,
) -> list[dict]:
    items = payload if isinstance(payload, list) else _extract_message_items(payload, field_mapping)
    fragments: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            text = _extract_text(_pick_object_raw_value(item, _semantic_keys(field_mapping, "text")) or item)
            speaker = _pick_object_value(item, _semantic_keys(field_mapping, "speaker"), default="unknown")
            timestamp = _normalize_timestamp(_pick_object_raw_value(item, _semantic_keys(field_mapping, "timestamp")), imported_at)
            channel = _pick_object_value(item, _semantic_keys(field_mapping, "channel"), default=fallback_channel)
            title = _pick_first(_pick_object_value(item, _semantic_keys(field_mapping, "title")), extract_title(text), fallback_channel, "Message export", default="Message export")
        else:
            text = _extract_text(item)
            speaker = "unknown"
            timestamp = imported_at
            channel = fallback_channel
            title = extract_title(text) or _pick_first(fallback_channel, "Message export", default="Message export")
        if not text.strip():
            continue
        fragments.append(
            {
                "source_type": "json_export",
                "content_type": "message",
                "timestamp": timestamp,
                "text": text,
                "title": title,
                "speaker": speaker,
                "channel": channel,
            }
        )
    return fragments


def _extract_message_items(payload: object, field_mapping: dict | None = None) -> list[object]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return [payload]
    for key in _semantic_keys(field_mapping, "items"):
        value = _lookup_value(payload, key)
        if isinstance(value, list):
            return value
    for key in ("data", "result", "payload"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            nested_items = _extract_message_items(nested, field_mapping)
            if nested_items != [nested]:
                return nested_items
        elif isinstance(nested, list):
            return nested
    return [payload]


def _extract_text(value: object) -> str:
    fragments = _collect_text_fragments(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        if fragment not in seen:
            seen.add(fragment)
            deduped.append(fragment)
    return "\n".join(deduped).strip()


def _collect_text_fragments(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped[:1] in {"{", "["}:
            try:
                return _collect_text_fragments(json.loads(stripped))
            except json.JSONDecodeError:
                pass
        return [stripped]
    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_collect_text_fragments(item))
        return fragments
    if isinstance(value, dict):
        fragments: list[str] = []
        for key in DEFAULT_FIELD_ALIASES["text"] + ["title"]:
            if key in value:
                fragments.extend(_collect_text_fragments(value[key]))
        if fragments:
            return fragments
        for nested in value.values():
            fragments.extend(_collect_text_fragments(nested))
        return fragments
    return [str(value).strip()] if str(value).strip() else []


def _detect_platform(items: list[object], field_mapping: dict | None = None) -> tuple[str, dict]:
    resolved_mapping = field_mapping if isinstance(field_mapping, dict) else {}
    platform_hint = _stringify(resolved_mapping.get("platform")).lower()
    if platform_hint:
        if platform_hint not in KNOWN_PLATFORMS:
            raise ValueError(f"unsupported platform hint: {platform_hint}")
        return platform_hint, {
            "platform_detection_mode": "platform_hint",
            "platform_detection_reasons": [f"used explicit platform hint: {platform_hint}"],
            "platform_signal_scores": {name: 0 for name in sorted(KNOWN_PLATFORMS - {'generic'})},
        }

    scores = {"slack": 0, "feishu": 0, "dingtalk": 0, "wechat": 0}
    matched_keys: dict[str, set[str]] = {name: set() for name in scores}
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        for platform in scores:
            hits = _matching_signal_keys(item, PLATFORM_SIGNAL_FIELDS[platform], resolved_mapping)
            if hits:
                scores[platform] += len(hits)
                matched_keys[platform].update(hits)
    best = max(scores, key=scores.get)
    if scores[best]:
        reasons = [f"{best} matched keys: {', '.join(sorted(matched_keys[best]))}"]
        return best, {
            "platform_detection_mode": "message_signals",
            "platform_detection_reasons": reasons,
            "platform_signal_scores": scores,
        }
    if resolved_mapping:
        return "generic", {
            "platform_detection_mode": "mapped_generic_fallback",
            "platform_detection_reasons": ["used field mapping but no platform-specific signals matched; fell back to generic parsing"],
            "platform_signal_scores": scores,
        }
    return "generic", {
        "platform_detection_mode": "generic_fallback",
        "platform_detection_reasons": ["no platform-specific signals matched; used generic JSON parsing"],
        "platform_signal_scores": scores,
    }


def _matching_signal_keys(item: dict, base_keys: list[str], field_mapping: dict) -> list[str]:
    candidates = _dedupe(base_keys + _mapping_list(field_mapping.get("text")) + _mapping_list(field_mapping.get("speaker")) + _mapping_list(field_mapping.get("channel")) + _mapping_list(field_mapping.get("timestamp")) + _mapping_list(field_mapping.get("message_type")))
    hits: list[str] = []
    for key in candidates:
        if _value_present(_lookup_value(item, key)):
            hits.append(key)
    return hits


def _looks_like_slack_directory(path: Path) -> bool:
    return (path / "users.json").exists() or (path / "channels.json").exists()


def _looks_like_slack_zip(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        names = {Path(name).name for name in archive.namelist()}
    return bool(names & SLACK_METADATA_FILES)


def _build_workspace_structure_diagnostics(
    *,
    platform: str,
    mode: str,
    reason: str,
    fragments: list[dict],
    field_mapping: dict | None = None,
) -> dict:
    return _build_fragment_diagnostics(
        platform,
        fragments,
        field_mapping,
        {
            "platform_detection_mode": mode,
            "platform_detection_reasons": [reason],
            "platform_signal_scores": {name: 0 for name in sorted(KNOWN_PLATFORMS - {'generic'})},
        },
    )


def _build_aggregate_diagnostics(
    *,
    platform: str,
    fragments: list[dict],
    field_mapping: dict | None,
    mode: str,
    reason: str,
    counts: dict[str, int],
    extra_reasons: list[str],
) -> dict:
    diagnostics = _build_fragment_diagnostics(
        platform,
        fragments,
        field_mapping,
        {
            "platform_detection_mode": mode,
            "platform_detection_reasons": [reason] + [item for item in extra_reasons if item][:2],
            "platform_signal_scores": counts,
        },
    )
    return diagnostics


def _build_fragment_diagnostics(platform: str, fragments: list[dict], field_mapping: dict | None, detection: dict) -> dict:
    coverage = _field_coverage(fragments)
    missing_fields = [name for name in EXPECTED_FIELDS_BY_PLATFORM.get(platform, EXPECTED_FIELDS_BY_PLATFORM["generic"]) if coverage.get(name, 0.0) == 0.0]
    return {
        "platform_detection_mode": detection.get("platform_detection_mode", ""),
        "platform_detection_reasons": detection.get("platform_detection_reasons", []),
        "platform_signal_scores": detection.get("platform_signal_scores", {}),
        "field_mapping_keys": sorted(str(key) for key in (field_mapping or {}).keys()),
        "field_coverage": coverage,
        "missing_fields": missing_fields,
    }


def _field_coverage(fragments: list[dict]) -> dict[str, float]:
    if not fragments:
        return {
            "text": 0.0,
            "speaker": 0.0,
            "channel": 0.0,
            "timestamp": 0.0,
        }
    total = len(fragments)
    return {
        "text": round(sum(1 for item in fragments if _stringify(item.get("text"))) / total, 3),
        "speaker": round(sum(1 for item in fragments if _stringify(item.get("speaker")) not in {"", "unknown"}) / total, 3),
        "channel": round(sum(1 for item in fragments if _stringify(item.get("channel"))) / total, 3),
        "timestamp": round(sum(1 for item in fragments if _stringify(item.get("timestamp"))) / total, 3),
    }


def _load_slack_user_map_from_directory(path: Path) -> dict[str, str]:
    users_path = path / "users.json"
    if not users_path.exists():
        return {}
    return _build_slack_user_map(json.loads(users_path.read_text(encoding="utf-8")))


def _load_slack_user_map_from_zip(archive: zipfile.ZipFile) -> dict[str, str]:
    for name in archive.namelist():
        if Path(name).name == "users.json":
            return _build_slack_user_map(json.loads(archive.read(name).decode("utf-8")))
    return {}


def _build_slack_user_map(payload: object) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not isinstance(payload, list):
        return mapping
    for item in payload:
        if not isinstance(item, dict):
            continue
        user_id = _stringify(item.get("id"))
        profile = item.get("profile")
        display_name = ""
        if isinstance(profile, dict):
            display_name = _pick_first(profile.get("display_name"), profile.get("real_name"), default="")
        resolved = _pick_first(item.get("real_name"), display_name, item.get("name"), user_id, default="")
        if user_id and resolved:
            mapping[user_id] = resolved
    return mapping


def _resolve_slack_user(user_map: dict[str, str], user_id: object) -> str:
    key = _stringify(user_id)
    return user_map.get(key, key)


def _sender_name(sender: object) -> str:
    if not isinstance(sender, dict):
        return _stringify(sender)
    return _pick_first(
        sender.get("sender_name"),
        sender.get("name"),
        sender.get("display_name"),
        sender.get("id"),
        default="",
    )


def _semantic_keys(field_mapping: dict | None, semantic: str) -> list[str]:
    return _dedupe(_mapping_list((field_mapping or {}).get(semantic)) + DEFAULT_FIELD_ALIASES.get(semantic, []))


def _mapping_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _lookup_value(payload: object, field_path: str) -> object:
    if not field_path:
        return None
    current = payload
    for part in field_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return None
    return current


def _pick_object_raw_value(payload: object, field_paths: list[str]) -> object:
    for field_path in field_paths:
        value = _lookup_value(payload, field_path)
        if _value_present(value):
            return value
    return None


def _pick_object_value(payload: object, field_paths: list[str], *, default: str = "") -> str:
    return _stringify(_pick_object_raw_value(payload, field_paths)) or default


def _value_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _normalize_timestamp(value: object, imported_at: str) -> str:
    if value is None:
        return imported_at
    if isinstance(value, (int, float)):
        return _epoch_to_iso(float(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return imported_at
        try:
            return _epoch_to_iso(float(stripped))
        except ValueError:
            return stripped
    return str(value)


def _epoch_to_iso(value: float) -> str:
    seconds = value / 1000 if value > 10_000_000_000 else value
    return datetime.fromtimestamp(seconds, tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick_first(*values: object, default: str = "") -> str:
    for value in values:
        text = _stringify(value)
        if text:
            return text
    return default


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _dominant_platform(counts: dict[str, int]) -> str:
    if not counts:
        return "generic"
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]
