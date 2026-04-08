# Sample Search API Predecessor

这是一个最小但完整的示例 bundle，演示 `colleague-clone` 当前本地能力的最终产物长什么样。

## 场景

- 目标人物：Search API 前任负责人
- 关系：`predecessor`
- 材料来源：
  - 一份 handoff markdown
  - 一段 pasted text

## 目录

- [sources/intake_request.yaml](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/sources/intake_request.yaml)
- [sources/manifest.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/sources/manifest.jsonl)
- [normalized/docs/src_001.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/normalized/docs/src_001.jsonl)
- [normalized/pasted/src_002.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/normalized/pasted/src_002.jsonl)
- [analysis/persona_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/analysis/persona_profile.json)
- [analysis/work_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/analysis/work_profile.json)
- [persona.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/persona.md)
- [work.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/work.md)
- [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/SKILL.md)
- [meta.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/meta.json)
- [evidence_index.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/evidence_index.jsonl)

## 对应命令

这份示例大致对应：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/sample_search_api_predecessor \
  --name "Search API 前任" \
  --relationship predecessor \
  --source /path/to/handoff.md \
  --pasted-text "结论前置，评审先看 impact。"
```
