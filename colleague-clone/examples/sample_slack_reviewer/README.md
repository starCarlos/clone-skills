# Sample Slack Reviewer

这是一个基于 Slack 风格导出目录生成的完整示例 bundle，用来演示平台导入后的 `colleague-clone` 产物长什么样。

## 场景

- 目标人物：Slack Reviewer
- 关系：`mentor`
- 材料来源：
  - 一份 Slack-style export directory
  - 一段 pasted text

## 目录

- [sources/intake_request.yaml](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/sources/intake_request.yaml)
- [sources/manifest.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/sources/manifest.jsonl)
- [normalized/messages/src_001.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/normalized/messages/src_001.jsonl)
- [normalized/pasted/src_002.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/normalized/pasted/src_002.jsonl)
- [analysis/persona_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/analysis/persona_profile.json)
- [analysis/work_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/analysis/work_profile.json)
- [persona.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/persona.md)
- [work.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/work.md)
- [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/SKILL.md)
- [meta.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/meta.json)
- [evidence_index.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/evidence_index.jsonl)

## 对应命令

这份示例大致对应：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/sample_slack_reviewer \
  --name "Slack Reviewer" \
  --relationship mentor \
  --source /path/to/slack-export \
  --pasted-text "评审时先讲 impact，再讲实现细节。"
```
