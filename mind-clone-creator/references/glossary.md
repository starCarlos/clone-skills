# Glossary

## 核心术语

| 术语 | 含义 |
| --- | --- |
| `persona-only` | 只走人格层分身链路，不强制同时开启 workflow 轨道。 |
| `persona-plus-workflow` | 在同一个 working bundle 里同时保留人格层和 workflow 轨道。 |
| `working bundle` | 人格层和可选 workflow 轨道的总入口目录。 |
| `workflow blueprint pipeline` | workflow 访谈、阶段确认、blueprint 生成所在的中间层。 |
| `workflow runtime bundle` | workflow 已进入执行层后的运行包。 |
| `personal clone skill` | 人格层最终 skill 目录。 |
| `workflow clone skill` | 带 workflow 蓝图的工作型 skill 目录。 |
| `target_work_unit` | 你希望工作型替身稳定接住的第一类典型工作单元。 |
| `blocker` | 当前不能继续自动推进，必须先由人补料或确认的阻塞点。 |
| `coherent stack` | bundle、pipeline、runtime、personal skill、workflow skill 在内容链路上彼此一致的一组产物。 |
| `stack_ref` | 在 operator 摘要里压缩展示当前选中的 stack 身份。 |
| `sample-stack` | 仓库维护者重建出来的一套已知样例 stack。 |
| `current-stack` | 从某个具体 working bundle 反推出来的 coherent stack。 |
| `latest-stack` | `/tmp` 下当前被选中的最新 coherent stack。 |
| `release-readiness` | 把单测、sample rebuild、blueprint gate、doctor/validate/explain 等总检查收在一起的发布前检查。 |

## 文件层术语

| 文件 | 含义 |
| --- | --- |
| `personal_interview.md` | 人格层访谈入口。 |
| `workflow_interview.md` | workflow 轨道访谈入口。 |
| `stage_confirmation.md` | workflow 阶段草稿确认稿。 |
| `workflow_blueprint.md` | 已正式成型的 workflow 蓝图。 |
| `workflow_task_state.yaml` | workflow runtime 的当前任务状态。 |
| `NEXT_INTERVIEW_UPDATE.md` | 当前最值得先补的下一块访谈内容。 |
| `PENDING_INTERVIEW_ACTIONS.json` | 全部未完成访谈动作的结构化队列。 |
| `*_manifest.json` | 某一层产物的主清单，通常也是 refresh / 续跑入口。 |
| `*_summary.json` | 某次校验或某层产物的汇总状态。 |

## 怎么用这份表

- 看不懂 bundle / pipeline / runtime 的区别时，先看这份 glossary。
- 看不懂某个文件为什么存在、下一步该干嘛时，再回到 [current_system_flow.md](/home/admin_wsl/.openclaw/workspace/skills/mind-clone-creator/references/current_system_flow.md) 第 8 节“关键文件速查”。
