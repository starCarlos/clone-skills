# Sample Feishu Reviewer

这是一个基于飞书消息导出 JSON 生成的完整示例 bundle，用来演示平台 JSON 导入后的 `colleague-clone` 产物长什么样。

## 场景

- 目标人物：Feishu Reviewer
- 关系：`predecessor`
- 材料来源：
  - 一份 Feishu-style export JSON
  - 一段 pasted text

## 目录

- [sources/intake_request.yaml](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/sources/intake_request.yaml)
- [sources/manifest.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/sources/manifest.jsonl)
- [normalized/messages/src_001.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/normalized/messages/src_001.jsonl)
- [normalized/pasted/src_002.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/normalized/pasted/src_002.jsonl)
- [analysis/persona_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/analysis/persona_profile.json)
- [analysis/work_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/analysis/work_profile.json)
- [persona.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/persona.md)
- [work.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/work.md)
- [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/SKILL.md)
- [meta.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/meta.json)
- [evidence_index.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/evidence_index.jsonl)

## 对应命令

这份示例大致对应：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/sample_feishu_reviewer \
  --name "Feishu Reviewer" \
  --relationship predecessor \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --pasted-text "先确认 owner，再同步相关方。"
```
