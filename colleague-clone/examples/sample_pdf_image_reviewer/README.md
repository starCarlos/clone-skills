# Sample PDF Image Reviewer

这是一个基于 PDF 交接文档和截图文件生成的完整示例 bundle，用来演示 `colleague-clone` 的文档类输入产物长什么样。

## 场景

- 目标人物：PDF Image Reviewer
- 关系：`mentor`
- 材料来源：
  - 一份 PDF handoff
  - 一张本地截图
  - 两段 pasted text

## 目录

- [sources/intake_request.yaml](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/sources/intake_request.yaml)
- [sources/manifest.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/sources/manifest.jsonl)
- [normalized/docs/src_001.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/normalized/docs/src_001.jsonl)
- [normalized/images/src_002.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/normalized/images/src_002.jsonl)
- [normalized/pasted/src_003.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/normalized/pasted/src_003.jsonl)
- [normalized/pasted/src_004.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/normalized/pasted/src_004.jsonl)
- [analysis/persona_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/analysis/persona_profile.json)
- [analysis/work_profile.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/analysis/work_profile.json)
- [persona.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/persona.md)
- [work.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/work.md)
- [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/SKILL.md)
- [meta.json](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/meta.json)
- [evidence_index.jsonl](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/evidence_index.jsonl)

## 对应命令

这份示例大致对应：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/sample_pdf_image_reviewer \
  --name "PDF Image Reviewer" \
  --relationship mentor \
  --source /path/to/review_handoff.pdf \
  --source /path/to/rollback-risk-screenshot.png \
  --pasted-text "先确认 owner，再同步相关方。" \
  --pasted-text "结论前置，列表化同步风险。"
```

如果当前环境没有 `pytesseract` 和 `tesseract`，截图会先以图片元信息记录进入 bundle，并在文本里明确标注 OCR 不可用。
