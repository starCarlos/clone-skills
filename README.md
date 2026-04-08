# clone-skills

从私有 monorepo 中抽离出来、面向开源发布的 clone 构建技能仓库。

当前仓库公开了两条 clone 工作流：

- `mind-clone-creator`：把你自己的经验、判断方式和工作习惯整理成可复用的顾问型或 workflow-oriented clone
- `mind-clone-advisor`：基于他人的公开资料构建合规的 advisor workflow

根目录的 [SKILL.md](SKILL.md) 是公开入口，会把 clone 相关请求路由到合适的子工作流。

## 怎么选择

- 当事实来源是你自己，也就是你的回答、你的材料、你的工作风格时，使用 `mind-clone-creator`
- 当事实来源是某个人的公开资料，而且你需要处理授权、合规和资料质量检查时，使用 `mind-clone-advisor`

## 快速开始

在支持 skill 的环境里，可以直接这样开始：

- `我想创建自己的数字分身`
- `我想把自己的经验做成 AI 顾问`
- `我想用公开资料构建某个人的顾问型分身`

如果你还没想清楚来源对象是谁，可以先从根路由进入，再让它继续分流。

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
├── mind-clone-advisor/
└── mind-clone-creator/
```

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
