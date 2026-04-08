# Sample DingTalk Reviewer

这是一个基于钉钉消息导出 JSON 生成的完整示例 bundle，用来演示 DingTalk-style export 导入后的 `colleague-clone` 产物长什么样。

## 场景

- 目标人物：DingTalk Reviewer
- 关系：`predecessor`
- 材料来源：
  - 一份 DingTalk-style export JSON
  - 三段 pasted text

## 目录

- [sources/intake_request.yaml](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/sources/intake_request.yaml)
- [sources/manifest.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/sources/manifest.jsonl)
- [normalized/messages/src_001.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/normalized/messages/src_001.jsonl)
- [normalized/pasted/src_002.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/normalized/pasted/src_002.jsonl)
- [normalized/pasted/src_003.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/normalized/pasted/src_003.jsonl)
- [normalized/pasted/src_004.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/normalized/pasted/src_004.jsonl)
- [analysis/persona_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/analysis/persona_profile.json)
- [analysis/work_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/analysis/work_profile.json)
- [persona.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/persona.md)
- [work.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/work.md)
- [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/SKILL.md)
- [meta.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/meta.json)
- [evidence_index.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/evidence_index.jsonl)

## 对应命令

这份示例大致对应：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/sample_dingtalk_reviewer \
  --name "DingTalk Reviewer" \
  --relationship predecessor \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --pasted-text "先确认 owner，再同步相关方。" \
  --pasted-text "CR 重点看错误码统一和回滚预案。" \
  --pasted-text "结论前置，列表化同步风险。"
```
