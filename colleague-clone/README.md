# colleague-clone

把同事、前任负责人、导师或搭档留下来的本地材料，整理成一个可更新、可回滚、可放行的 colleague skill。

## 适合什么场景

- 前任交接只留下了一堆文档、聊天导出和邮件
- 你想恢复某个同事的评审重点、表达风格和工作套路
- 你需要一个有证据来源、可持续修正的本地 skill

不适合：

- 克隆你自己
  这类需求走 `mind-clone-creator`
- 基于公开人物资料做顾问
  这类需求走 `mind-clone-advisor`

## 当前本地能力

已支持：

- Markdown / TXT
- PDF
- PNG / JPG / WebP / BMP / GIF 图片和截图
- pasted text
- generic JSON message export
- Slack-style export directory
- Slack-style export ZIP
- Feishu-style export JSON
- Feishu-style export directory
- DingTalk-style export JSON
- WeChat-compatible export JSON
- `.eml`
- `.mbox`
- draft 生成
- update 追加材料
- manual override
- rollback
- `draft -> final_confirmed`
- finalized bundle release package (`release_manifest.json`)
- finalized runtime consumer package (`runtime_package.json`)
- richer persona/work pattern extraction
- final gate with evidence balance checks
- field-level confidence and conflict detection
- bootstrap preflight diagnostics
- explicit conflict resolution with rebuild
- structured resolution audit trail
- privacy filtering for family, health, finance, and contact-detail content
- runtime refusal and redirection rules for private or out-of-scope questions

未支持：

- 飞书 / Slack / 钉钉 live connector
- 浏览器登录态抓取
- workflow runtime 对接
- 内置 OCR 依赖自动安装

## 最快用法

一条命令跑完整本地草稿链路：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/search-api-predecessor \
  --name "Search API 前任" \
  --relationship predecessor \
  --source /path/to/handoff.md \
  --source /path/to/review-notes.txt \
  --pasted-text "结论前置，评审先看 impact。"
```

如果想先做导入预检，再在高风险时直接停下：

```bash
python3 colleague-clone/scripts/bootstrap_colleague_clone.py \
  --bundle-dir /tmp/search-api-predecessor \
  --name "Search API 前任" \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --preflight \
  --stop-on-risky-preflight
```

生成后建议先看：

- `/tmp/search-api-predecessor/persona.md`
- `/tmp/search-api-predecessor/work.md`
- `/tmp/search-api-predecessor/SKILL.md`
- `/tmp/search-api-predecessor/evidence_index.jsonl`

## 常用命令

初始化 bundle：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/example-bundle \
  --name "Alice" \
  --source /path/to/handoff.md
```

如果自动识别不符合预期，可以显式指定 `source_kind`：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/example-bundle \
  --name "Alice" \
  --source /path/to/messages.json \
  --source-kind workspace_export
```

如果 JSON 字段名不是当前内置兼容格式，可以给单个 source 附带 `field_map`：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/example-bundle \
  --name "Alice" \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --field-map '{"platform":"wechat","items":"payload.entries","speaker":"actor","channel":"roomName","timestamp":"sentAt","text":"body.text"}'
```

规范化：

```bash
python3 colleague-clone/scripts/normalize_colleague_sources.py \
  --bundle-dir /tmp/example-bundle \
  --strict
```

导入前先做诊断：

```bash
python3 colleague-clone/scripts/inspect_colleague_sources.py \
  --source /path/to/slack-export \
  --source /path/to/messages.json \
  --source-kind workspace_export
```

如果是非标准导出，也可以在 inspect 阶段先带上同样的 mapping 看诊断是否符合预期：

```bash
python3 colleague-clone/scripts/inspect_colleague_sources.py \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --field-map '{"platform":"wechat","items":"payload.entries","speaker":"actor","channel":"roomName","timestamp":"sentAt","text":"body.text"}'
```

导入 Slack 导出目录或 ZIP：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/slack-bundle \
  --name "Slack Teammate" \
  --source /path/to/slack-export
```

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/slack-bundle \
  --name "Slack Teammate" \
  --source /path/to/slack-export.zip
```

导入飞书导出目录或消息 JSON：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/feishu-bundle \
  --name "Feishu Teammate" \
  --source /path/to/feishu-export \
  --source /path/to/messages.json
```

导入钉钉消息 JSON：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/dingtalk-bundle \
  --name "DingTalk Teammate" \
  --source /path/to/dingtalk-messages.json
```

导入微信导出 JSON：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/wechat-bundle \
  --name "WeChat Teammate" \
  --source /path/to/messages.json \
  --source-kind workspace_export
```

导入 PDF 或截图：

```bash
python3 colleague-clone/scripts/init_colleague_intake.py \
  --bundle-dir /tmp/doc-bundle \
  --name "Doc Reviewer" \
  --source /path/to/review-handoff.pdf \
  --source /path/to/rollback-risk-screenshot.png
```

分析：

```bash
python3 colleague-clone/scripts/analyze_colleague_persona.py --bundle-dir /tmp/example-bundle
python3 colleague-clone/scripts/analyze_colleague_work.py --bundle-dir /tmp/example-bundle
```

生成草稿：

```bash
python3 colleague-clone/scripts/build_colleague_skill.py --bundle-dir /tmp/example-bundle
```

校验草稿：

```bash
python3 colleague-clone/scripts/validate_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --format json
```

追加材料并重建：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --source /path/to/new-export.json \
  --rebuild
```

如果追加的是平台 JSON，但你希望按 workspace export 解析：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --rebuild
```

如果追加的是非标准平台 JSON，也可以一起附带 `field_map`：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --source /path/to/messages.json \
  --source-kind workspace_export \
  --field-map '{"platform":"wechat","items":"payload.entries","speaker":"actor","channel":"roomName","timestamp":"sentAt","text":"body.text"}' \
  --rebuild
```

如果 final gate 因冲突卡住，可以显式记录解决方案并重建：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --resolve-conflict-scope work \
  --resolve-conflict-field work.workflow_patterns \
  --resolve-conflict-note "Prefer risk-first planning over execution-first shortcuts" \
  --rebuild
```

重建后，分析 JSON 会保留：

- `conflicts`
- `resolved_conflicts`
- `resolution_history`

人工纠偏并重建：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --override-scope persona \
  --override-field persona.decision_patterns.disagreement_style \
  --override-value "always asks for impact first" \
  --override-reason "user correction" \
  --rebuild
```

如果 `update --rebuild` 引入了新的 runtime boundary drift，可以单独补一次人工确认：

```bash
python3 colleague-clone/scripts/update_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --ack-runtime-drift \
  --ack-note "Reviewed privacy-limited runtime shift for the new source." \
  --ack-by "qa-reviewer"
```

这次确认只会覆盖当前最新的 `last_drift_id`。如果之后又追加 source 并触发了新的 runtime drift，旧 ack 会自动失效，必须重新确认。

回滚：

```bash
python3 colleague-clone/scripts/rollback_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --version v1
```

升级为 final：

```bash
python3 colleague-clone/scripts/promote_colleague_skill.py \
  --bundle-dir /tmp/example-bundle
```

最终校验：

```bash
python3 colleague-clone/scripts/validate_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --require-final \
  --format json
```

`init` 输出会返回每个 source 的 `source_type`、`detection_mode`，以及可选的 `field_mapping`；`normalize` 输出会返回 `detected_platforms` 和 `normalized_sources`，方便快速确认导入识别结果。
`inspect_colleague_sources.py` 会在不创建 bundle 的前提下返回平台识别、platform detection mode、detection reasons、field coverage、record 数、speaker/channel 覆盖率、时间范围和风险提示。
PDF 会直接抽取页面文字；图片和截图会统一落成 `image_source` record，并在 `image_analysis` 里记录 `ocr_provider`、`ocr_status` 和 `ocr_text`。
默认 provider 是本地 `tesseract`；如果当前环境没有 `pytesseract` 和 `tesseract`，会明确标注 `OCR status: unavailable`，而不是静默失败。

当前 `persona/work` 分析会额外抽取这些稳定模式：

- question-first / context-first 决策方式
- owner-alignment 协作方式
- explicit boundary 边界习惯
- rollback-first / escalate-early 压力应对
- clarify -> align_owner -> risk_first -> plan -> checklist 工作序列
- conclusion-first / list / risk_callout 交付格式偏好

对外阅读时，当前更推荐按这四层理解生成结果：

- 职业职责
- 工作方法
- 沟通风格
- 边界约束

如果你更偏向“画像”语言，当前还可以直接按这三层来读：

- 职业画像
  - 聚合职责范围、工作序列、评审关注点
- 性格画像
  - 聚合 question-first、owner-aligned、boundary-conscious、rollback-first 这类工作互动倾向
- 家庭边界画像
  - 只表达“家庭/私生活属于禁止推断边界”，不做任何正向家庭建模

底层实现里仍保留 `persona/work` 两个分析文件和证据路径，主要是为了兼容已有验证、冲突解决和 example 结构。

隐私边界默认策略：

- 家庭关系
- 健康与就医
- 财务与账户
- 地址、电话、证件、联系方式

这些内容会被标记为 `private_sensitive` 或 `work_adjacent`，默认不进入最终分析证据；如果一份 source 里这类内容占比太高，`inspect` 和 final validation 会明确给出风险提示。

运行时边界默认策略：

- 生成的 `SKILL.md` 会把 clone 明确框定为 `bounded work proxy`，不是完整人格模拟
- draft skill 现在会额外写出 `Runtime Portraits`，把职业画像、工作语境内的性格画像、家庭边界画像直接整理成运行时摘要
- draft skill 会额外写出 `Runtime Boundaries`、`Known Unknowns` 和 `Refusal Pattern`
- 同时会生成结构化的 `analysis/runtime_contract.json` 和 `analysis/runtime_portraits.json`
- `runtime_contract.json` 负责保存 runtime 规则、拒答模板、重定向话题、caveat 分级和 final-ready 约束
- `runtime_portraits.json` 负责保存运行时画像和回答策略，例如默认模块、默认评审关注点、工作推进顺序、互动倾向和边界策略
- `validate` / `promote` 现在还会额外返回扁平的 `runtime_portraits_summary`，方便调用方直接取稳定字段
- `update --rebuild` 现在会返回 `runtime_portraits_drift`，说明这次 rebuild 改动了哪些默认模块、评审焦点、互动倾向或边界信号
- 如果画像 drift 影响到了边界策略、私密信号或 redirect topics，这些变化现在也会进入 runtime release review，而不再只看 contract drift
- 被问到家庭、健康、财务、联系方式、住址、证件，或任何超出工作范围的问题时，应该拒答并重定向回职责、工作方法、评审偏好、沟通风格或边界约束
- 如果证据不足、互相冲突，或某些内容因为隐私被过滤，运行时要直接说明，而不是补全猜测
- `Known Unknowns` 现在会先做优先级分层：`critical uncertainty`、`privacy-limited area`、`minor sparse signal`
- 默认只渲染真正影响回答安全的前两类；普通稀疏字段不会再整段倒进 `SKILL.md`

`Runtime Portraits` 的三层含义是：

- `Professional Portrait`
  - 供运行时快速抓职责模块、工作序列、评审关注点
- `Temperament Portrait`
  - 只表达工作互动中的倾向，不扩展成完整人格设定
- `Family Boundary Portrait`
  - 明确家庭/私生活问题应 `refuse_and_redirect`，并给出允许重定向的话题范围

`runtime_portraits.json` 里还会额外给出一层 `answer_strategy`：

- `default_modules`
- `default_review_focus`
- `workflow_sequence`
- `interaction_tendencies`
- `questioning_tendency`
- `disagreement_style`
- `delivery_preferences`
- `boundary_policy`
- `redirect_topics`

`runtime_portraits_summary` 现在是稳定消费接口，会同时保留三层画像块和扁平回答策略字段：

- `professional_portrait`
  - `summary`
  - `scope_modules`
  - `operating_sequence`
  - `review_focus_areas`
  - `confidence`
- `temperament_portrait`
  - `summary`
  - `tendency_tags`
  - `pressure_mode`
  - `questioning_tendency`
  - `disagreement_style`
  - `confidence`
- `family_boundary_portrait`
  - `summary`
  - `policy`
  - `allowed_scope`
  - `redirect_topics`
  - `refusal_say`
  - `confidence`

- `default_modules`
- `default_review_focus`
- `workflow_sequence`
- `interaction_tendencies`
- `delivery_preferences`
- `questioning_tendency`
- `disagreement_style`
- `boundary_policy`
- `private_signal_present`
- `redirect_topics`

`validate --require-final` 现在不只看 evidence 总数，也会检查：

- persona/work 两层是否都有证据
- 证据是否分布在足够多的字段上
- 是否仍有 placeholder 或明显空洞内容
- 是否存在未解决的分析冲突
- 关键字段是否仍处于低置信状态

即使不带 `--require-final`，draft validation 现在也会检查 runtime contract 是否和分析结果一致；如果 `SKILL.md` 漏掉了必须声明的关键不确定性或隐私限制，或者错误地把 minor sparse caveat 写进草稿，普通校验也会失败。
另外，draft validation 还会同时检查 `semantic_view`、`analysis/runtime_portraits.json` 和 `SKILL.md` 里的 `Runtime Portraits` 是否一致；如果画像摘要、默认回答策略、边界策略或画像字段结构被改坏，输出里会出现 `portrait_issues`。
JSON 输出现在也会带 `runtime_portraits_summary`，调用方可以不读整份画像 JSON。
同时还会带 `runtime_portraits_review_brief`，用于快速判断这次 release review 里有没有画像层面的高影响变化。
如果 bundle 已经是 `final_confirmed`，`validate` 还会校验根目录下的 `release_manifest.json`、`runtime_package.json`、`runtime_release_health.json`、`runtime_smoke.json`、`runtime_prompt_eval.json` 是否存在，且是否和当前 bundle 内容保持一致。

`validate --require-final` 还会额外读取 `analysis/runtime_contract.json` 的 `final_contract_issues`：

- unresolved conflict 不能留到 final
- `persona.decision_patterns`、`work.responsibility_scope`、`work.workflow_patterns`、`work.review_preferences` 不能继续处于 critical uncertainty
- 如果存在 privacy-limited area，runtime contract 必须保留明确的拒答和重定向结构

`promote_colleague_skill.py` 现在会在真正把状态改成 `final_confirmed` 之前先检查这组 runtime gate；如果 runtime contract 还不满足 final-ready，命令会直接返回 `runtime_contract_final_issues` 和扁平的 `runtime_contract_summary`。
另外，如果最近一次 `update --rebuild` 产生了未确认的 runtime drift，`promote` 也会直接拒绝，并返回 `runtime_release_review` / `runtime_release_review_issues`。

`update_colleague_skill.py --rebuild` 现在还会返回 `runtime_contract_drift` 和 `runtime_release_review`：

- 是否从无 major caveat 变成有 required caveat
- 是否新进入 privacy-limited 状态
- 新增或移除的 required caveat 字段
- 重建前后 runtime contract 的扁平摘要
- 分组后的 review 摘要：`new_restrictions`、`new_uncertainty`、`cleared_caveats`
- review severity：`blocking` / `caution` / `informational`

只要本次 rebuild 真的改动了 runtime boundary，bundle 的 `meta.json` 就会记录一条 `runtime_release_review`，状态会变成 `pending_ack`。这条记录现在会保留完整 `history`，至少包括：

- `drift_detected`
- `drift_acknowledged`

`runtime_release_review.last_ack` 还会显式记录它确认的是哪个 `acked_drift_id`。只有当这个 id 等于当前的 `last_drift_id` 时，release gate 才算真的解除。

`validate --require-final` 现在也会检查这条 release review：

- `runtime_release_review.status == pending_ack` 时，final validation 直接失败
- JSON 输出会带 `runtime_release_review`、`runtime_release_review_brief`、`runtime_release_decision` 和 `runtime_release_review_issues`
- text 输出会打印当前 release review 的 `status` / `requires_ack`，以及 brief headline

`promote_colleague_skill.py` 在被 runtime review 挡住时，现在也会直接返回一段 `runtime_release_review_brief`：

- `severity`
- `headline`
- `items`

同时还会返回 `runtime_release_decision`，统一给出：

- `decision`: `allow` / `block` / `caution`
- `reason_codes`
- `requires_ack`
- `review_brief`

这样调用方不用再自己拼 `status + severity + issues`，也不用先读完整 `history` 才知道这次为什么能发或不能发。
同样，调用方现在也不需要自己拆 `runtime_portraits.json` 才能拿到默认模块和边界策略，因为 `promote` 会直接返回 `runtime_portraits_summary`。
如果这次待确认的是画像层面的变化，`promote` / `validate` 还会返回 `runtime_portraits_review_brief`，并且 `runtime_release_decision.reason_codes` 会补充：

- `portrait_boundary_shift`
- `portrait_scope_shift`

成功 promote 之后，bundle 根目录还会落一份稳定的 `release_manifest.json`。它把下游最常用的字段集中到一个文件里：

- bundle 基本信息：name、slug、relationship、state、时间戳
- release 元数据：snapshot_dir、version_count、version_history_count、latest_review_status
- source 汇总：source_count、source_type_counts、detected_platform_counts
- evidence 汇总：evidence_count、balance、field_coverage
- `runtime_contract_summary`
- `runtime_portraits_summary`
- `runtime_release_review`
- `runtime_release_review_brief`
- `runtime_portraits_review_brief`
- `runtime_release_decision`
- `release_health`
- `runtime_smoke_summary`
- `runtime_prompt_eval_summary`

这样下游如果只是要接运行时代理或 UI 展示，就不需要再分别读取 `meta.json`、`sources/manifest.jsonl` 和 `analysis/*.json`。

同时，final bundle 现在还会落一份 `runtime_package.json`，它更偏下游运行时消费，而不是 release 审计。里面会集中放：

- bundle 基本信息
- system prompt 片段：
  `identity`、`runtime_rules`、`runtime_boundaries`、`known_unknowns`、`refusal_pattern`、`answer_style`
- `runtime_contract_summary`
- `runtime_portraits_summary`
  - 这里会直接带三层稳定画像块：`professional_portrait`、`temperament_portrait`、`family_boundary_portrait`
- `release_health`
- `runtime_smoke_summary`
- `runtime_prompt_eval_summary`
- release 决策与 compare brief
- provenance：关联的 `release_manifest.json`、source/evidence 摘要

如果你只想把这个 clone 喂给外部 runtime / agent adapter，优先读 `runtime_package.json`，而不是重新解析整个 bundle。

同时，final bundle 还会落一份稳定的 `runtime_release_health.json`。它是给 UI / runtime adapter / 发布检查直接消费的统一摘要，里面会集中放：

- `release_health`
  - `decision`
  - `review`
  - `compare`
  - `smoke`
  - `prompt_eval`
  - `contract`
  - `portraits`

这样下游不需要自己再把 `release_manifest.json`、`runtime_package.json`、`runtime_smoke.json`、`runtime_prompt_eval.json` 拼一遍，直接读这份就能判断当前 final release 是否健康、为什么健康、以及最值得展示的边界/风险摘要。

现在这份稳定产物里也会带：

- `runtime_release_health_compare_report`
- `runtime_release_health_compare_brief`

它会直接对比上一版 final 的 `runtime_release_health.json`，方便调用方知道“这次 release health 和上一版相比到底变了什么”。

同时，final bundle 还会落一份稳定的 `runtime_smoke.json`。它是 deterministic runtime smoke 的持久化结果，里面会带：

- `runtime_smoke_report`
- `runtime_smoke_brief`
- `runtime_smoke_compare_report`
- `runtime_smoke_compare_brief`

这样调用方不用每次重新跑 smoke，也能直接知道当前 runtime package 是否通过这组基础消费检查，以及相对上一版 final 的变化。

同时，final bundle 还会落一份稳定的 `runtime_prompt_eval.json`。它是默认 deterministic prompt eval 的持久化结果，里面会带：

- `runtime_prompt_eval_report`
- `runtime_prompt_eval_brief`
- `runtime_prompt_eval_compare_report`
- `runtime_prompt_eval_compare_brief`

这样调用方不用每次重新跑 prompt eval，也能直接知道当前 release 的 `decision`、`score`，以及相对上一版 final 的变化。

也可以单独导出 / 重建它：

```bash
python3 colleague-clone/scripts/export_colleague_runtime.py \
  --bundle-dir /tmp/example-bundle
```

如果你只想单独读取当前 final 的统一 health 视图，也可以直接跑：

```bash
python3 colleague-clone/scripts/run_colleague_release_health.py \
  --bundle-dir /tmp/example-bundle \
  --format json
```

它会返回：

- `runtime_release_health`
- `runtime_release_health_compare_report`
- `runtime_release_health_compare_brief`

如果你想在 final bundle 上做一次轻量运行时验收，可以跑 smoke harness：

```bash
python3 colleague-clone/scripts/run_colleague_runtime_smoke.py \
  --bundle-dir /tmp/example-bundle \
  --format text
```

它不会调用真实模型，而是检查 `runtime_package.json` 是否具备处理这些问题所需的运行时信号：

- 工作范围内问题
- 私密 / 越界问题
- 低证据 / 未知问题
- 风格与回答策略问题
- release 决策和 provenance 是否足够支撑运行

如果你希望在 final validation 时顺便跑这组检查：

```bash
python3 colleague-clone/scripts/validate_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --require-final \
  --run-runtime-smoke \
  --format json
```

这时输出会额外带：

- `runtime_smoke_report`
- `runtime_smoke_summary`
- `runtime_smoke_issues`
- `runtime_smoke_compare_report`
- `runtime_smoke_compare_brief`

如果你想要更接近运行时消费的回答预演，可以跑 prompt eval preview：

```bash
python3 colleague-clone/scripts/run_colleague_prompt_eval.py \
  --bundle-dir /tmp/example-bundle \
  --format text
```

它会基于 `runtime_package.json` 生成 5 类固定问题的确定性回答预演：

- `work_in_scope`
- `private_boundary`
- `uncertainty`
- `style_consistency`
- `review_scenario`

这一步仍然不会调用真实模型，但会直接产出 `prompt + answer + checks`，比纯结构 smoke 更接近下游 runtime 消费。

如果你已经有一个本地模型 wrapper，也可以切到 `model` 模式：

```bash
python3 colleague-clone/scripts/run_colleague_prompt_eval.py \
  --bundle-dir /tmp/example-bundle \
  --mode model \
  --model-command /tmp/mock_prompt_eval_model.py \
  --format json
```

`--model-command` 当前约定很简单：

- 进程从 `stdin` 读取一段 JSON
- JSON 至少包含 `profile`、`case`、`runtime_package`
- 进程输出一段 JSON，最少包含 `answer`

首版 `model` 模式仍复用同一套规则检查，只是把答案生成从内置模板换成外部模型/命令。

如果你想用自定义评测集覆盖默认 5 个 case，也可以传一个 JSON 文件：

```bash
python3 colleague-clone/scripts/run_colleague_prompt_eval.py \
  --bundle-dir /tmp/example-bundle \
  --cases-file /tmp/prompt_eval_cases.json \
  --format json
```

这个文件目前使用：

- `schema_version`
- `profile`
- `cases[]`
  - `case_id`
  - `prompt`
  - `expected_checks[]`
  - `severity`

支持的 `expected_checks[]` 首版包括：

- `must_include_default_modules`
- `must_include_review_focus`
- `must_include_workflow`
- `must_refuse_and_redirect`
- `must_acknowledge_uncertainty`
- `must_include_style_signals`

如果你希望在 final validation 时顺便跑这组 prompt eval：

```bash
python3 colleague-clone/scripts/validate_colleague_skill.py \
  --bundle-dir /tmp/example-bundle \
  --require-final \
  --run-prompt-eval \
  --prompt-eval-cases-file /tmp/prompt_eval_cases.json \
  --format json
```

这时输出会额外带：

- `runtime_prompt_eval_report`
- `runtime_prompt_eval_decision`
- `runtime_prompt_eval_summary`
- `runtime_prompt_eval_issues`
- `runtime_prompt_eval_blocking_issues`

其中 `runtime_prompt_eval_report` 现在还会带：

- `profile`
- `case_source`
- `mode`
- `summary`
  - `passed_count`
  - `failed_count`
  - `blocking_failures`
  - `caution_failures`
  - `informational_failures`
  - `score`
- `decision`
  - `decision`: `allow` / `caution` / `block`
  - `blocking`

如果 bundle 已经是 `final_confirmed`，普通 `validate` 还会直接返回当前稳定产物里的：

- `runtime_release_health`
- `runtime_release_health_artifact`
- `runtime_release_health_compare_report`
- `runtime_release_health_compare_brief`
- `runtime_release_health_artifact_issues`
- `runtime_smoke_artifact`
- `runtime_smoke_compare_report`
- `runtime_smoke_compare_brief`
- `runtime_smoke_artifact_issues`
- `runtime_prompt_eval_artifact`
- `runtime_prompt_eval_compare_report`
- `runtime_prompt_eval_compare_brief`
- `runtime_prompt_eval_artifact_issues`

`runtime_release_health_artifact_issues` 代表根目录 `runtime_release_health.json` 和当前 bundle / runtime summaries 不一致。
`runtime_smoke_artifact_issues` 代表根目录 `runtime_smoke.json` 和当前 bundle / runtime package 不一致。
`runtime_prompt_eval_artifact_issues` 代表根目录 `runtime_prompt_eval.json` 和当前 bundle / runtime package 不一致。

`validate` / `promote` 更适合直接消费 `runtime_prompt_eval_decision` 和 `runtime_prompt_eval_summary`，而不是自己扫描整份 case 列表。
另外，现在还可以直接比较当前 final 和上一版 final：

```bash
python3 colleague-clone/scripts/compare_colleague_release.py \
  --bundle-dir /tmp/example-bundle \
  --format text
```

这个 compare 会优先读取最近一个带 `release_manifest.json` 的 snapshot，输出：

- 是否存在上一版 final
- 当前 release 是否发生变化
- 变化的 section，例如 `sources`、`evidence`、`runtime_portraits_summary`
- 一段可直接给 reviewer 用的 `headline + items`

如果当前 bundle 已经有 `release_manifest.json`，`validate` 会返回 `release_compare_report` 和 `release_compare_brief`；`promote` 在成功后也会直接返回这两个字段，方便调用方展示“这次 release 相比上一版变了什么”。

如果你希望通过一个统一入口读取当前 final bundle 的稳定产物，也可以直接跑：

```bash
python3 colleague-clone/scripts/inspect_colleague_release_bundle.py \
  --bundle-dir /tmp/example-bundle \
  --view full \
  --format json
```

支持的 `--view` 目前有：

- `release`
- `runtime`
- `health`
- `full`

这个 inspect 入口会统一返回：

- `artifact_paths`
- `availability`
- `issues`
- `compare_briefs`

其中 `full` 视图还会聚合：

- `release`
- `runtime`
- `health`

这样外部 UI、adapter 或脚本不需要再自己串多个命令，也不需要自己判断哪些稳定产物已经存在。

如果你想看当前实现和外部热门 `colleague-skill` 的结构化差异，见：

- [references/external-comparison.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/references/external-comparison.md)

分析 JSON 里现在会给关键字段补：

- `confidence`
- `confidence_reason`
- `conflicts`
- `resolved_conflicts`
- `resolution_history`

## 看一个现成例子

示例 bundle 在：

- [examples/sample_search_api_predecessor/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_search_api_predecessor/README.md)
- [examples/sample_slack_reviewer/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_slack_reviewer/README.md)
- [examples/sample_feishu_reviewer/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_feishu_reviewer/README.md)
- [examples/sample_dingtalk_reviewer/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_dingtalk_reviewer/README.md)
- [examples/sample_wechat_reviewer/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_wechat_reviewer/README.md)
- [examples/sample_pdf_image_reviewer/README.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/examples/sample_pdf_image_reviewer/README.md)

如果你改了 schema、分析逻辑或 fixture，可以用这个脚本回刷 examples：

```bash
python3 colleague-clone/scripts/generate_example_bundles.py --validate --check-readme-links
```

## 关键文件

- 技能入口：
  [SKILL.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/SKILL.md)
- 本地设计说明：
  [references/design.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/references/design.md)
- schema 说明：
  [references/schemas.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/references/schemas.md)
- 外部对标：
  [references/external-comparison.md](/home/admin_wsl/sunnet/skills/clones/colleague-clone/references/external-comparison.md)
- example 重建：
  [scripts/generate_example_bundles.py](/home/admin_wsl/sunnet/skills/clones/colleague-clone/scripts/generate_example_bundles.py)
