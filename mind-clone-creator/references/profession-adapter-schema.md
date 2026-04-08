# Profession Adapter Schema

## Purpose

定义 `references/profession-adapters/*.json` 的稳定结构。

profession adapter 用来给 workflow clone runtime 增加职业相关偏置，影响两层：

- planning layer: 阶段级 `read / produce / preferred_tools` 偏置
- execution layer: 命令候选顺序、artifact 采集重点、Markdown artifact 模板选择

## Required Top-Level Fields

每个 adapter JSON 至少包含：

- `profession_aliases`: `string[]`

其中：

- 第一个 alias 应该是该职业的主显示名
- alias 匹配当前实现会先做规范化：转小写，并去掉空格、连字符、下划线等非字母数字分隔符
- 例如 `AI Engineer`、`ai-engineer`、`ai_engineer` 会落到同一个匹配 key
- 当前仍不是语义模糊匹配；只有规范化后完全相同才会命中

## Optional Top-Level Fields

- `preferred_repo_types`: `string[]`
- `preferred_test_commands`: `string[][]`
- `preferred_run_commands`: `string[][]`
- `notes`: `string[]`
- `stage_overrides`: `object`
- `execution_overrides`: `object`

## Stage Overrides

`stage_overrides` 的 key 是阶段名，value 结构如下：

```json
{
  "实现与验证": {
    "preferred_tools": ["代码仓库", "测试脚本"],
    "extra_read": ["失败样本", "评估日志"],
    "extra_produce": ["验证结论"],
    "notes": ["先确认验证口径"]
  }
}
```

字段均为可选：

- `preferred_tools`: `string[]`
- `extra_read`: `string[]`
- `extra_produce`: `string[]`
- `notes`: `string[]`

## Execution Overrides

`execution_overrides` 当前支持两个分组：

### `tool_preferences`

按工具名匹配执行偏置。key 一般是工具名或工具名片段。

```json
{
  "tool_preferences": {
    "测试脚本": {
      "prefer_mode": "safe_execute",
      "retry_fallback_candidates": true
    },
    "代码仓库": {
      "prefer_collect_artifacts": ["git_status", "git_diff_stat", "repo_profile"]
    }
  }
}
```

当前已用字段：

- `prefer_mode`: `string`
- `retry_fallback_candidates`: `boolean`
- `prefer_collect_artifacts`: `string[]`

### `artifact_templates`

给文档类工具指定 Markdown artifact 模板：

```json
{
  "artifact_templates": {
    "文档/IM": "workflow_clarification_note_template.md",
    "任务系统": "workflow_task_card_template.md"
  }
}
```

value 必须是 `templates/` 目录下存在的文件名。

## Example

```json
{
  "profession_aliases": ["AI Engineer", "AI工程师"],
  "preferred_test_commands": [
    ["uv", "run", "pytest", "--collect-only", "-q"],
    ["pytest", "--collect-only", "-q"]
  ],
  "notes": ["优先寻找评估脚本和测试命令"],
  "stage_overrides": {
    "实现与验证": {
      "preferred_tools": ["代码仓库", "测试脚本"],
      "extra_read": ["失败样本"],
      "extra_produce": ["验证结论"]
    }
  },
  "execution_overrides": {
    "tool_preferences": {
      "测试脚本": {
        "retry_fallback_candidates": true
      }
    },
    "artifact_templates": {
      "任务系统": "workflow_task_card_template.md"
    }
  }
}
```

## Validation Rule

新增或修改 adapter 后，优先运行：

```bash
python3 scripts/validate_profession_adapters.py --workspace . --output /tmp/profession_adapters_validation.json
```

如果只是查看当前有哪些 adapter，可运行：

```bash
python3 scripts/list_profession_adapters.py --workspace . --output /tmp/profession_adapters.json
```
