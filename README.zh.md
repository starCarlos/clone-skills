# clone-skills

[English README](README.md)

把“分身 / clone / 顾问型人格”从一次性的 prompt，做成更可复用、更可审查、更能扩展的技能工作流。

`clone-skills` 是一个从私有 monorepo 中抽离出来、面向开源发布的 clone 构建仓库。它关注的不是“写一个像谁的 prompt”这么简单，而是把判断方式、来源材料、工作流程和边界约束整理成可长期复用的 skill。

## 你能得到什么

当前仓库公开提供两条 clone 工作流：

| Skill | 适合构建什么 |
| --- | --- |
| `mind-clone-creator` | 基于你自己的经验、判断方式、工作习惯和表达风格构建 clone |
| `mind-clone-advisor` | 基于他人的公开资料构建合规的 advisor workflow |

根目录的 [SKILL.md](SKILL.md) 是公开入口，会先判断该走哪条工作流。

## 这些 Skill 的优势

很多“分身”项目最后只停留在“写一个像谁的 prompt”。这套工作流更进一步：

- 它先把“来源是什么”说清楚，再处理 prompt 和产物，这样 clone 是先被建立，再被表达，而不是把所有问题都塞进一个 system prompt
- 它把 clone 的结构显式展开，而不是把能力埋在黑箱里
- 它会把边界写清楚：什么已经成立，什么还需要 workflow 设计，什么必须因为合规原因暂停
- 它输出的是一组可复用资产，而不是一段临时文案，比如 profile、prompt、workflow 产物和评测结果
- 它比零散的 persona 设定更容易维护、复查和继续扩展

## 层级模型

当前公开的两条工作流，各自有不同的层级模型。这里的重点不是“模仿语气”，而是把思维克隆做成一套可向上展开的结构。

### `mind-clone-creator`

`mind-clone-creator` 可以理解成一个向上展开的四层结构：

1. 人格层
2. 工具层
3. 工作流层
4. 决策层

默认交付一定先落在人格层。只有在具体工作单元被定义之后，更高的工作流层和决策层才有意义，这样 clone 才不会一开始就漂浮在抽象设定里。

### `mind-clone-advisor`

`mind-clone-advisor` 可以理解成一个合规优先的三层结构：

1. 语料与合规层
2. 画像与 Prompt 层
3. 可选图谱层

当启用图谱层时，概念层级默认按下面的方式建模：

- 信念 -> 模型 -> 话题

这让你不只是在复述某个人说过什么，也能更系统地理解这些观点是怎样组织起来的。

## 你可以拿它做什么

- 做一个更像你本人回答问题、评审方案、澄清需求的数字分身
- 把自己的工作习惯沉淀成 clone，并逐步扩展成 workflow-oriented work clone
- 基于某个作者、投资人、创始人或公众人物的公开资料，构建 advisor workflow
- 交付结构化 clone 资产，而不是零散笔记，比如 profile 文件、prompt、评测结果和 workflow 产物
- 从多个层级理解一个人的思维方式，从信念、模型一路看到话题和证据结构

## 如何选择

- 当事实来源是你自己，也就是你的回答、你的材料和你的工作风格时，使用 `mind-clone-creator`
- 当事实来源是某个人的公开资料，而且你需要处理授权、合规和资料质量检查时，使用 `mind-clone-advisor`

如果你还没想清楚来源对象是谁，可以先从根路由进入，再让它继续分流。

## 快速开始

在支持 skill 的环境里，可以直接这样开始：

- `我想创建自己的数字分身`
- `我想把自己的经验做成 AI 顾问`
- `我想用公开资料构建某个人的顾问型分身`

## 仓库范围

这个仓库有意保持在较窄的公开范围内：

- 面向公开发布的自我 clone 构建
- 基于公开资料的 advisor 构建
- 为这两条流程服务的 prompts、scripts、references 和 evaluation 资产

本地 runtime 产物、会话日志和环境相关工作区数据不会纳入版本控制。

## 目录结构

```text
clone-skills/
├── SKILL.md
├── README.md
├── README.zh.md
├── mind-clone-advisor/
└── mind-clone-creator/
```

## 相关文档

- [SKILL.md](SKILL.md)：clone 相关请求的根路由入口
- [mind-clone-creator/README.md](mind-clone-creator/README.md)：自我 clone 工作流总览
- [mind-clone-creator/README.zh.md](mind-clone-creator/README.zh.md)：自我 clone 工作流中文版 README
- [mind-clone-creator/SKILL.md](mind-clone-creator/SKILL.md)：自我 clone 的完整 skill 说明
- [mind-clone-advisor/README.md](mind-clone-advisor/README.md)：基于公开资料的 advisor workflow 总览
- [mind-clone-advisor/README.zh.md](mind-clone-advisor/README.zh.md)：公开资料 advisor 工作流中文版 README
- [mind-clone-advisor/SKILL.md](mind-clone-advisor/SKILL.md)：基于公开资料的 advisor workflow 入口
- [mind-clone-advisor/思维克隆_私人顾问构建指南.md](mind-clone-advisor/思维克隆_私人顾问构建指南.md)：更完整的中文操作指南

## 边界说明

- 这个仓库默认不承诺交付一个可完全替代人工工作的自治 Agent
- `mind-clone-advisor` 只适合用于合法公开资料和合规审查明确的场景
- `mind-clone-advisor/registry/` 下的文件应视为模板，不应直接当作生产数据
- 任何生成出来的示例内容，在继续对外发布前都应先人工复查

## 仓库维护约定

- 本地配置和生成物尽量使用相对路径
- 本地 runtime 输出、日志和会话产物不要提交进仓库
- 公开文档应始终与当前实际发布的模块保持一致

## 许可

MIT
