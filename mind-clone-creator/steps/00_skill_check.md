# Step 00: 辅助 Skill 可用性检查

## 目的

在正式创建数字分身前，先确认当前环境里实际可用的辅助 skill，避免把工作流建立在用户并不具备的 skill 上。

## 处理逻辑

1. 盘点当前会话中实际可用的辅助 skill。
2. 先确认当前 skill 自带的 `references/multi-search-engine/SKILL.md` 可作为默认联网搜索助手。
3. 再标记本流程可能会用到的其他 skill 是否可用：
   - `deep-research`
   - `content-harvester`
   - `docx`
   - `pdf`
   - `xlsx`
   - `tikhub-api-helper`
   - `find-skills`
   - `skill-installer`
4. 记录可直接使用的 skill 和当前缺失的 skill。
5. 如果关键 skill 缺失，提前决定降级路径；若后续确实需要补装，再征得用户确认。
6. 用户确认后，可继续调用 `find-skills` / `skill-installer` 帮助发现并安装缺失 skill。

优先使用脚本：

- `scripts/check_helper_skills.py`：输出 `skill_availability`
- `scripts/prepare_skill_gap_plan.py`：当存在缺口时，输出面向用户确认的安装计划
- `scripts/install_helper_skill.py`：只有用户明确确认后，才执行实际安装；默认只输出安装命令与执行计划

## 用户可见性

- 默认后台静默执行
- 但如果发现用户后续大概率会依赖某个缺失 skill，应在正式访谈开始前提示用户确认是否安装

## 输出

`skill_availability` 结果，至少包含：

- `available_helpers`
- `missing_helpers`
- `fallback_plan`

若存在关键缺口，还应追加：

- `skill_gap_plan`
- `confirm_questions`

## 规则

- 不要假设用户拥有和开发环境相同的 skill。
- 当前 skill 自带的 `multi-search-engine` 本地副本是默认联网搜索入口。
- 只有当前环境确认可用的 skill，才可纳入默认工作流。
- 对缺失 skill，只能记录缺口；若后续确实需要安装，必须先征得用户确认。
- 用户确认后，不只是提示缺失，还要尽量帮助用户完成安装或下载接入。
- 若 `find-skills` / `skill-installer` 本身缺失，则只能输出安装建议和手工命令，不能承诺流程内自动补装。
- 调用 `scripts/install_helper_skill.py` 时，只有显式传入 `--confirmed yes --execute` 才能真正安装。
