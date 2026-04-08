# External Comparison

`colleague-clone` 当前实现与外部热门项目 `titanwings/colleague-skill` 的结构化对标。

## 对标对象

- 对标日期：2026-04-07
- 外部仓库：<https://github.com/titanwings/colleague-skill>
- 主要一手材料：
  - README：<https://github.com/titanwings/colleague-skill/blob/main/README.md>
  - SKILL：<https://github.com/titanwings/colleague-skill/blob/main/SKILL.md>
  - INSTALL：<https://github.com/titanwings/colleague-skill/blob/main/INSTALL.md>

按 2026-04-07 抓取到的 GitHub 页面，外部仓库约为 `9.6k stars / 787 forks / 68 issues / 3 pull requests`。这些数字是当日快照，不应视为稳定常量。

## 一句话结论

外部项目强在“产品化采集和交互入口”，当前本地实现强在“schema-first、可审计、可验证、可放行”。

如果目标是让用户更快拿到一个能用的同事 skill，外部项目目前更顺手。
如果目标是把私有材料整理成一个可持续修正、可追溯、可做质量门禁的内部资产，当前 `colleague-clone` 更稳。

## 关键差异

| 维度 | `titanwings/colleague-skill` | 当前 `colleague-clone` | 判断 |
|---|---|---|---|
| 产品形态 | 直接安装成可调用 skill，入口是 `/create-colleague`、`/{slug}`、`/list-colleagues` | 以 bundle + CLI 为主，入口是 `bootstrap/init/normalize/analyze/build/update/promote` | 外部更像现成产品，我们更像可控流水线 |
| 数据采集 | 强调 Feishu / DingTalk / Slack 自动采集，含 API、浏览器、MCP 路径 | 只做本地文件和导出物导入，不做 live connector | 外部领先 |
| 输入覆盖 | README 明示支持 PDF、图片/截图、Feishu JSON、邮件、Markdown、粘贴文本、WeChat 导出兼容 | 已支持 Markdown/TXT、pasted text、generic JSON、Slack/Feishu/DingTalk 导出、`.eml`、`.mbox` | 我们在工作空间导出规范化上更细，但缺图片/PDF/微信 |
| 创建流程 | 以对话式 intake 为主，先问 3 个问题，再选采集方式 | 以 CLI 参数和 bundle 状态迁移为主 | 外部更适合非工程用户 |
| 生成结构 | Work + Persona 双层结构，Persona 使用 5 层建模 | Work + Persona 双层结构，外加 evidence index、analysis JSON、state/meta | 两边核心抽象相近，我们更强调中间态 |
| 进化机制 | 追加文件、会话纠偏、版本回滚，README 强调“never overwrite existing conclusions” | 追加 source、manual override、explicit conflict resolution、rollback、promote | 我们的修正链路更显式 |
| 审计能力 | README / SKILL 中强调 version archive 和 correction，但公开材料里较少看到结构化审计字段 | `version_history.jsonl`、`manual_overrides`、`resolved_conflicts`、`resolution_history`、snapshot versions | 我们领先 |
| 质量门禁 | 更偏“尽快生成可用 skill”，公开材料里未强调严格 final gate | 已有 final validation、evidence balance、coverage、conflict、critical confidence gate | 我们领先 |
| 测试可见性 | GitHub 页面更强调 prompts + tools + install，公开说明更偏产品演示 | 29 个 `unittest` 覆盖导入、分析、更新、回滚、门禁、平台导出 | 我们领先 |
| 复用方式 | 安装到 `.claude/skills/` 或全局目录直接使用 | 目前仍是 repo 内 workflow，需要先跑脚本再消费产物 | 外部更直接 |

## 为什么不能直接拿外部仓库当底座

可以把它当参考实现，但不适合直接 `git clone` 后在此仓库里硬改，原因有三点：

1. 外部项目的主入口是“交互式 skill + prompts + live collectors”，而当前目录的核心是“本地 bundle 流水线 + schema + tests + final gate”。
2. 外部项目把生成结果落到 `colleagues/{slug}/`，当前实现把中间态、分析态、版本态拆成 bundle 目录；数据模型不同，直接套壳会把现有验证链路打散。
3. 当前仓库已经对 `clones/` 体系做了本地化约束，继续沿着现有 `sources -> normalized -> analysis -> build -> validate -> promote` 走，维护成本更低。

更准确的策略是：把外部项目当“产品 benchmark”，不是当“代码基座”。

## 外部项目领先的部分

最值得追的不是它的 prompt 文案，而是这些用户价值：

1. 自动采集入口更多，尤其是 Feishu / DingTalk / Slack 的 live collection。
2. 安装后即可通过 slash command 使用，几乎不需要理解 bundle 内部结构。
3. 支持 PDF、图片/截图、WeChat 导出兼容格式，原材料覆盖面更广。
4. 有更强的“描述一个人也能先生成一个版本”的产品包容性。

## 当前实现领先的部分

当前实现更像内部工程系统，而不是 demo：

1. 中间态明确：`sources/`、`normalized/`、`analysis/`、`versions/` 都可检查。
2. 质量门禁明确：不仅能生成，还能判断能不能升到 `final_confirmed`。
3. 纠偏可审计：手工覆盖、冲突解决、重建后的残留状态都能追踪。
4. 回归测试完整：平台导入、冲突、低置信、预检、回滚都有测试兜底。

## 结论性的产品判断

如果只看“第一次上手是否惊艳”，外部项目现在更强。

如果看“能否成为一个长期维护的内部能力”，当前 `colleague-clone` 的基础更扎实，尤其适合：

- 对证据边界敏感的团队
- 需要版本治理和放行控制的场景
- 不希望模型根据稀疏材料过度拟人的场景

## 建议的下一阶段优先级

建议不要去重写我们已经有的 schema-first 主干，而是沿着外部项目领先的地方补最短板：

1. `P1`：补 PDF / 图片 / 截图输入
   这能直接缩小“材料覆盖面”的差距，而且不破坏现有 bundle 架构。

2. `P1`：补 example 生成自动化
   外部项目更像产品，我们现在示例产物已经多起来了，必须自动化，否则文档会先老化。

3. `P2`：补可选 live connector 层
   先把 connector 设计成可选前置采集器，而不是把 live collection 写进主分析链路。

4. `P2`：补更轻量的交互入口
   可以在不放弃 CLI 的前提下，加一个包装命令或更友好的 bootstrap 向导。

5. `P3`：评估微信导出兼容层
   先支持开源导出物格式，不直接碰聊天客户端。

## 当前推荐路线

下一步最合理的是：

1. 保持当前 bundle / validation / promote 架构不变。
2. 先补输入面和示例自动化。
3. 再考虑把外部项目的“自动采集便利性”作为可选增强层接入。

不建议下一步去做“整体改造成外部项目同款交互式 skill”，那会先损坏现在已经稳定的验证和审计链路。
