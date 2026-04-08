# 人物 skill 验收清单

> 自动化验收脚本: `python3 scripts/validate_person_skill.py --skill-dir <path>`

## 合规

- [ ] 目标人物授权已确认（在世公众人物/非公众人物必须有明确授权）
- [ ] `registry/persons.json` 中合规字段已确认：`subject_type`、`authorization_status`、`source_legitimacy`
- [ ] `authorization_checked_at` 已填写，能说明本次人工确认发生在何时
- [ ] `python3 scripts/person.py show --person <slug> --explain-compliance` 不再显示阻断原因

## 最低可用（必须满足）

- [ ] 目录存在且命名清晰（如 `person-slug`） — *自动检查*
- [ ] `SKILL.md` 存在且含 `name`/`description` — *自动检查*
- [ ] `thinking_profile.md` 与 `system_prompt.md` 存在 — *自动检查*
- [ ] "核心信念"不少于 3 条 — *自动检查*
- [ ] "心智模型库"不少于 8 条 — *自动检查*
- [ ] "决策风格 / 价值排序 / 语言指纹"均有内容
- [ ] 含代表性"证据锚点"或来源说明 — *自动检查*
- [ ] `analysis/extractions.jsonl` 中有足够比例的 `evidence_anchors`，与根目录 `evidence_anchors.md` 一致 — *自动检查*
- [ ] 人物 skill 成品中不出现"未覆盖/无法判断/待补充" — *自动检查*
- [ ] System Prompt 包含能力圈边界与推理标注规则 — *自动检查*

## 评测门禁（建议默认执行）

- [ ] `evaluation_plan.md` 存在且可被 `evaluate_person_skill.py` 解析
- [ ] `evaluation_report.md` 已生成
- [ ] `evaluation_report.md` 已明确标注其为 artifact coverage，而非真人问答质量
- [ ] 自动评测结果不应长期停留在“固定分数/固定 0 命中”的失真状态

## 抽取覆盖（建议）

- [ ] 抽取结果中所有维度均已覆盖（缺失项需标注"未覆盖/无法判断"） — *自动统计*
- [ ] 抽取结果可追溯到原文来源

## 增强项（推荐）

- [ ] `kb/plain_text` 与 `kb/full_archive` 存在
- [ ] `kb/manifest.jsonl` 存在（语料清单）
- [ ] `analysis/extractions.jsonl` 存在
- [ ] `analysis/labels.jsonl` 存在（分类打标，由 `build_labels.py` 生成）
- [ ] `analysis/domain_config.json` 存在（领域配置）
- [ ] `analysis/corpus_summary.json` / `analysis/corpus_summary.md` 存在
- [ ] `meta/build_summary.json` 存在，且能反映语料规模、时间范围、合规状态
- [ ] 图谱产物（`graph/`）完整或可再生
- [ ] 论证链产物（`argument_chains.jsonl` / `argument_chains.md`）存在
- [ ] `theme_clusters.md` 或主题聚类摘要存在
- [ ] 更新流程说明清晰（或提供脚本）
- [ ] 测试/评估计划存在（`evaluation_plan.md` 或等价文档）
- [ ] 评估报告存在（`evaluation_report.md`，可由 `evaluate_person_skill.py` 自动生成；口径为 artifact coverage）
- [ ] 低质语料已清理（404/订阅墙/无关内容）

## 真实性与边界

- [ ] 明确区分"原文观点"与"推理延伸"
- [ ] 避免编造未表达过的观点
- [ ] 对高风险决策提示信息不足与风险
