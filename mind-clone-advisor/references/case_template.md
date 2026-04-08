# 人物 Skill 结构模板

每个人物的完整资料都放在对应人物 skill 里。

最小结构：

```
{person-skill}/
├── SKILL.md
├── thinking_profile.md
└── system_prompt.md
```

推荐结构：

```
{person-skill}/
├── SKILL.md
├── thinking_profile.md
├── system_prompt.md
├── kb/                      # 原始语料/纯文本
│   ├── full_archive/
│   └── plain_text/
├── analysis/                # 抽取结果
│   ├── extractions.jsonl
│   ├── labels.jsonl
│   ├── domain_config.json
│   ├── corpus_summary.json
│   └── corpus_summary.md
├── graph/                   # 图谱产物
│   ├── thought_graph.json
│   ├── thought_graph.mmd
│   ├── graph_report.md
│   ├── relation_graph.json
│   ├── relation_graph.mmd
│   ├── relation_report.md
│   ├── thought_hierarchy.json
│   ├── thought_hierarchy.md
│   ├── argument_chains.jsonl
│   ├── argument_chains.md
│   ├── node_weights.json
│   ├── sample_path_01.json
│   ├── sample_path_02.json
│   └── sample_path_03.json
├── theme_clusters.md         # 主题聚类
├── evaluation_plan.md        # 测试集
├── evaluation_report.md      # artifact coverage 报告，不等于真实问答质量
├── meta/
│   └── build_summary.json    # 构建摘要、语料规模与合规状态
├── scripts/                  # 更新脚本（可选）
├── assets/                   # 模板（可选）
└── notes/                    # 手工备注/校验记录（可选）
```

规则

- 人物 skill 必须可独立生效（含画像与系统提示词）
- 人物相关的语料、抽取、图谱、论证链、脚本都放在该人物 skill 中
- 总思维克隆只提供方法论与工具
