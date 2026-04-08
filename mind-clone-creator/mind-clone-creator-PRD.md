# mind-clone-creator — 完整开发文档

> 本文档是 Claude Code 的完整开发指令。
> 按照文档结构逐步创建所有文件，不需要额外说明。

---

## 一、项目背景与目标

### 1.1 这是什么

`mind-clone-creator` 是一个 Claude Skill，帮助用户通过结构化自我访谈，
创建属于自己的数字分身配置文件。

这是 mind-clone 开源项目的第一个模块，定位是**诚实的工具**：
- 不承诺完美复制人类思维
- 承诺把用户 70% 的显性经验打包成可复用的 AI 顾问
- 输出物是标准化配置文件，可以在平台上上架

### 1.2 和已有 Skill 的关系

```
mind-clone-creator（本项目）
└── 引导用户 → 创建分身配置文件

mind-clone-advisor（已有）
└── 加载配置文件 → 运行分身
```

两个 Skill 形成完整闭环：创建 → 运行。

### 1.3 目标用户

- 有知识积累、有表达习惯的专家
- 经常被重复咨询、想把经验复用的人
- 想把自己方法论传递给团队的人
- 技术背景不限，但需要有耐心完成访谈

### 1.4 成功标准

- 最小标准：用户能跟着流程在 2 小时内创建出一个可用的分身配置文件
- 理想标准：另一个人用这个分身配置文件，觉得"挺像那个人"

---

## 二、文件结构

Claude Code 需要创建以下完整文件结构：

```
mind-clone-creator/
│
├── SKILL.md                              ← Skill 主入口
├── SKILL-OPERATING-STANDARD.md          ← 运行标准
├── README.md                             ← 项目说明
│
├── steps/                                ← 流程文件
│   ├── 01_profession_parse.md
│   ├── 02_self_interview.md
│   ├── 03_mind_profile.md
│   ├── 04_system_prompt.md
│   ├── 05_quality_eval.md
│   └── 06_output.md
│
├── prompts/                              ← Prompt 库
│   ├── profession_analyzer.md
│   ├── interview_guide.md
│   ├── profile_synthesizer.md
│   ├── prompt_generator.md
│   ├── eval_question_gen.md
│   └── eval_scorer.md
│
├── templates/                            ← 模板文件
│   ├── clone_config_v1.yaml
│   ├── mind_profile_template.md
│   └── system_prompt_template.md
│
├── eval/                                 ← 评估体系
│   ├── scoring_rubric.md
│   └── eval_report_template.md
│
└── examples/                             ← 示例
    └── ai_engineer/
        ├── interview_filled.md
        ├── mind_profile.md
        ├── system_prompt.md
        └── clone_config.yaml
```

---

## 三、各文件详细规格

---

### 3.1 SKILL.md

**路径：** `mind-clone-creator/SKILL.md`

**内容要求：**

```markdown
---
name: mind-clone-creator
description: Use when the user wants to create their own digital twin, mind
clone, personal AI advisor, or package their own experience, judgment style,
and work habits into a reusable clone.
---

# Mind Clone Creator

## Scope
Guide users to create their own digital twin config file through structured
self-interview. Output is a standardized clone_config.yaml for use with
mind-clone-advisor.

## Use This Skill When
- User wants to create their own digital twin or mind clone
- User wants to package their experience into a reusable AI advisor
- User wants to generate a system prompt that represents their thinking style
- User says "创建分身", "数字分身", "克隆自己", "create my clone"

## Do Not Use This Skill When
- User wants to clone someone else (use mind-clone-advisor)
- User only wants a one-off persona response
- User wants to clone from public materials (use profile_clone path)

## Mandatory Gates
1. Confirm user is creating their OWN clone (not someone else's)
2. Confirm user understands output is ~70% accuracy, not perfect replication
3. Confirm user has 1-2 hours for the full interview, or 30 min for quick version

## Workflow
1. [01] Parse profession and skills → generate capability config
2. [02] Run structured self-interview (full or quick version)
3. [03] Synthesize interview → mind profile document
4. [04] Generate system prompt from mind profile
5. [05] Run quality evaluation → score report
6. [06] Output standardized clone_config.yaml

## Output Contract
- mind_profile.md: structured thinking profile
- system_prompt.md: ready-to-use system prompt
- clone_config.yaml: complete standardized config file
- eval_report.md: quality score and improvement suggestions

## Failure / Fallback Rules
- If user wants to clone someone else → redirect to mind-clone-advisor
- If interview answers are too vague → ask for specific examples before continuing
- If quality score < 60 → return improvement plan, do not output final config
- If user wants quick version → run quick_interview (5 questions only)

## Reference
Full prompts and templates: see steps/, prompts/, templates/ directories
```

---

### 3.2 SKILL-OPERATING-STANDARD.md

**路径：** `mind-clone-creator/SKILL-OPERATING-STANDARD.md`

**内容要求：**

```markdown
# Operating Standard

## 语言规则
- 默认用中文与用户交互
- 文件输出用中英双语标注字段名
- Prompt 内部用英文（提升 LLM 理解准确性）

## 对话规则
- 每次只问一个区的问题，不要一次性抛出所有问题
- 用户回答模糊时，必须追问具体例子，不允许继续下一步
- 每完成一个步骤，向用户确认再继续

## 质量规则
- 访谈答案少于 50 字的区，标记为"信息不足"，提示用户补充
- 思维画像生成后，必须列出所有"信息不足"项
- 质量评分低于 60 分不允许输出最终配置文件

## 隐私规则
- 不要求用户填写真实姓名，支持匿名
- 默认不把用户的访谈内容发送到本 skill 之外的外部存储或第三方服务
- 为支持跨回合编辑、校验和交付，可在当前工作目录或用户指定输出目录中本地写入访谈草稿、中间状态与最终产物
- 配置文件中的 creator 字段由用户自行决定是否填写真实信息

## 输出规则
- 所有输出文件使用 UTF-8 编码
- yaml 文件严格遵守 clone_config_v1.yaml 模板格式
- 可读 Markdown 交付物顶部应标注生成时间和版本号；条件允许时优先使用中英双语元信息标签
```

---

### 3.3 steps/01_profession_parse.md

**目的：** 解析用户职业和技能，动态生成能力配置

**内容要求：**

```markdown
# Step 01: 职业与技能解析

## 输入
- 用户描述的职业
- 用户描述的核心技能（可选）
- 用户描述的工作内容（可选）

## 处理逻辑
1. 提取职业关键词
2. 调用 profession_analyzer prompt 生成能力配置
3. 向用户展示生成结果，确认后进入下一步

## 引导话术
向用户说：
"我们先了解一下你的职业背景。
请告诉我：
1. 你的职业是什么？
2. 你最核心的技能是哪几项？（3-5项）
3. 你日常工作中最常做的事是什么？

不需要很正式，用你平时介绍自己的方式说就好。"

## 输出
skill_config 对象，包含：
- universal_skills: 通用技能列表
- professional_skills: 专业技能列表
- knowledge_base_recommendations: 建议上传的资料列表

## 异常处理
- 职业描述过于模糊（如"做互联网的"）→ 追问具体角色
- 技能列表为空 → 引导用户描述日常工作内容，从中提取

## 衔接
输出确认后，告知用户："很好，接下来我们开始正式的自我访谈。
全程大约需要 1-2 小时，你也可以选择 30 分钟的快速版本。
你想做哪个版本？"
```

---

### 3.4 steps/02_self_interview.md

**目的：** 引导用户完成结构化自我访谈

**内容要求：**

```markdown
# Step 02: 结构化自我访谈

## 两个版本

### 快速版（30分钟，5个核心问题）
适合：想先验证效果的用户
还原度：约 60%

问题列表：
Q1. 用3句话介绍自己（不用头衔，用你实际做的事）
Q2. 用“选择题 + 最小锚点 + 系统合成 + 用户确认”的方式收集3条工作原则
Q3. 描述你最近解决过的一个复杂问题，说说你的分析过程
Q4. 当有人问你不擅长的事，你怎么回应？示范一个例子
Q5. 用你平时发消息给朋友的方式，描述一件你最近做的事（100字）

### 完整版（1-2小时，5个区）
适合：想要高质量分身的用户
还原度：约 70-80%

区域划分：
- A 区：身份与能力边界（4题）
- B 区：思维方式（4题）
- C 区：价值观与决策原则（4题）
- D 区：表达风格（3题）
- E 区：示范问答（4题，最重要）

## 完整版题目

### A 区：身份与能力边界

A1. 用3句话介绍自己
格式引导："我做___，帮___解决___问题。
我最擅长___，我不擅长___。
找我的人通常因为___。"

A2. 你的能力地图
- 顶级能力（你在这件事上能排进前10%）：
- 熟练能力（你能做，但不是最强的）：
- 边界（你会拒绝的事，以及为什么）：

A3. 你的知识来源
- 主要影响你的书/作者（3-5个）：
- 你长期关注的领域：
- 你的判断更依赖经验还是数据：
- 你怎么学习新东西：

A4. 你如何定义自己的工作价值
- 你解决的核心问题是什么：
- 你的客户/用户/同事为什么来找你而不是别人：

### B 区：思维方式

B1. 你如何分析一个新问题
请用一个最近处理过的真实问题作为例子：
- 问题是什么：
- 你的第一步是：
- 然后是：
- 结论是怎么来的：

B2. 你最常用的思维框架
列出你真正在用的（不是你知道但很少用的）：
框架名称 → 你在什么场景下会用它

B3. 你如何处理信息不足的情况
当信息不够时，你倾向于怎么做？请举例说明。

B4. 你最容易忽略的视角
- 你自己知道的盲区：
- 别人指出过你的盲区（如果有）：

### C 区：价值观与决策原则

C1. 你的核心信念
先由 skill 生成3-5条候选原则，或通过选择题先定方向。
若使用选择题：
- 选择题只负责定方向，不能直接作为最终人物结论
- 每条都必须补一个最小锚点（项目名、场景词、指标词，或一句真实动作）
- 系统必须把“选项 + 最小锚点”合成为一句更像用户本人的完整表述
- 再让用户确认“像不像我、要不要改”

每条原则最终至少要有：
- 1 条用户确认过的原则表述
- 1 个最小锚点
- 最好再有 1 个完整决策例子

C2. 你的优先级排序（说真实选择，不是标准答案）
- 速度 vs 质量：
- 短期收益 vs 长期价值：
- 确定性 vs 更大的可能性：

C3. 你的红线
列出你会直接拒绝的事，以及原因：

C4. 你如何定义"好的建议"
- 你认为什么样的建议是好建议：
- 你最反感哪种建议方式：
- 你希望自己的分身给人什么感觉：

### D 区：表达风格

D1. 口语化自我描述（100-200字）
用你平时发消息给朋友的方式描述一件最近做的事，不要用书面语。

D2. 你的表达偏好
- 先结论还是先铺垫：
- 偏好举例、框架还是数据：
- 回答通常简短还是系统全面：

D3. 你不喜欢的表达方式
- 你最讨厌的回答风格：
- 你最欣赏的表达方式：

### E 区：示范问答（最重要）

E1. 3个你最常被问到的问题 + 你的真实回答

E2. 一个你有明确立场但可能有人不同意的问题
- 你的立场：
- 你为什么这么认为：
- 你承认这个立场的局限在哪里：

E3. 你完全不擅长的问题，你怎么回应（示范）

E4. 一个你解决过的复杂问题（完整描述）
- 问题背景：
- 你的分析过程：
- 解决方案：
- 结果：
- 如果重来你会改变什么：

## 访谈规则
- 每次只呈现一个区，完成后再进入下一区
- 用户回答少于50字的题目，必须追问："能给我一个具体例子吗？"
- E 区答案如果不够具体，必须追问，不允许跳过
- 到 C 区时，不要让用户从空白开始写原则
- 选择题只能定方向，不能直接输出成“这个人的原则”
- 每条选择题结论后，至少追一个最小锚点
- 系统把“选项 + 最小锚点”合成为一句表述后，必须再让用户确认
- 没有最小锚点的选择题答案，只能算线索，不能算可放入 final 的人物证据

## 输出
interview_data 对象，包含所有区的答案，标注信息充分/不足状态
```

---

### 3.5 steps/03_mind_profile.md

**目的：** 将访谈内容处理成结构化思维画像

**内容要求：**

```markdown
# Step 03: 思维画像生成

## 输入
interview_data（来自 Step 02）

## 处理逻辑
1. 调用 profile_synthesizer prompt
2. 生成结构化思维画像文档
3. 列出所有信息不足项
4. 向用户展示画像，确认准确性

## 展示方式
向用户展示生成的画像，说：
"我根据你的访谈内容生成了你的思维画像，请确认：
1. 有没有描述不准确的地方？
2. 有没有重要的方面没有体现？
可以直接告诉我哪里需要修改。"

## 输出
mind_profile.md，结构见 templates/mind_profile_template.md

## 异常处理
- 信息不足项超过3个 → 提示用户补充，不强制继续
- 用户确认有明显错误 → 重新处理对应区的数据
```

---

### 3.6 steps/04_system_prompt.md

**目的：** 基于思维画像生成可用的 System Prompt

**内容要求：**

```markdown
# Step 04: System Prompt 生成

## 输入
mind_profile.md（来自 Step 03）
skill_config（来自 Step 01）

## 处理逻辑
1. 调用 prompt_generator prompt
2. 生成 System Prompt
3. 向用户展示，确认

## System Prompt 约束
- 不超过 800 字
- 用第一人称，但不扮演"那个人本人"
- 必须包含能力边界声明
- 必须包含不确定性处理方式
- 语言风格匹配用户的表达习惯

## 输出
system_prompt.md，结构见 templates/system_prompt_template.md
```

---

### 3.7 steps/05_quality_eval.md

**目的：** 自动测试分身质量，生成评分报告

**内容要求：**

```markdown
# Step 05: 质量评估

## 输入
system_prompt.md（来自 Step 04）
interview_data（来自 Step 02，用于生成测试问题）

## 处理逻辑
1. 调用 eval_question_gen prompt 生成 10 个测试问题
   - 3个：用户在访谈中已经回答过的问题（验证一致性）
   - 4个：用户擅长领域的新问题（验证推理能力）
   - 2个：用户不擅长领域的问题（验证边界意识）
   - 1个：有争议性的问题（验证立场稳定性）

2. 用生成的 system_prompt 回答这 10 个问题

3. 调用 eval_scorer prompt 评分

## 评分维度
见 eval/scoring_rubric.md

## 输出
eval_report.md，包含：
- 总分（/100）
- 各维度得分
- 具体问题的回答和评价
- 改进建议

## 及格线
总分 >= 60 才允许进入 Step 06
总分 < 60 返回改进建议，提示用户补充访谈内容
```

---

### 3.8 steps/06_output.md

**目的：** 生成最终标准化配置文件

**内容要求：**

```markdown
# Step 06: 输出标准配置文件

## 输入
- skill_config（Step 01）
- interview_data（Step 02）
- mind_profile.md（Step 03）
- system_prompt.md（Step 04）
- eval_report.md（Step 05）

## 处理逻辑
1. 将所有内容组装进 clone_config_v1.yaml 模板
2. 生成最终配置文件
3. 向用户说明如何使用

## 使用说明（向用户展示）
"你的分身配置文件已生成。

你可以：
1. 把 system_prompt.md 的内容粘贴到任何支持自定义 System Prompt 的 AI 工具中使用
2. 把 clone_config.yaml 上传到 mind-clone 平台（即将上线）
3. 把配置文件分享给需要使用你分身的人

注意：
- 分身还原度约为 70%，复杂问题建议本人介入
- 建议每 3 个月根据新的经验更新一次配置文件
- 使用过程中发现偏差，可以重新补充访谈内容"

## 输出文件列表
- clone_config.yaml（主文件）
- mind_profile.md
- system_prompt.md
- eval_report.md
```

---

### 3.9 prompts/profession_analyzer.md

**内容要求：**

```markdown
# Prompt: Profession Analyzer

## 用途
根据用户描述的职业和技能，动态生成能力配置

## Prompt

```
You are an AI capability architect. Based on the user's profession and skills,
generate a capability configuration for their digital twin.

Output ONLY valid YAML, no explanation, no markdown fences.

Rules:
1. universal_skills: tools that make sense for this profession's daily work
2. professional_skills: specific to their stated expertise
3. knowledge_base_recommendations: practical materials they likely have

User Input:
- Profession: {profession}
- Core Skills: {skills}
- Daily Work: {daily_work}

Output format:
universal_skills:
  web_search:
    enabled: true/false
    use_case: "..."
  code_execution:
    enabled: true/false
    languages: []
  data_analysis:
    enabled: true/false
    formats: []
  file_handling:
    enabled: true/false
    types: []

professional_skills:
  - name: "..."
    trigger: "..."
    action: "..."

knowledge_base_recommendations:
  - type: "..."
    priority: must/recommended/optional
    reason: "..."
```

## Few-shot 示例

输入：
- Profession: AI Engineer
- Core Skills: model training, RAG systems, Python, architecture design
- Daily Work: building AI pipelines, code review, technical consulting

输出：
```yaml
universal_skills:
  web_search:
    enabled: true
    use_case: "查最新论文、框架文档、模型benchmark"
  code_execution:
    enabled: true
    languages: ["Python", "Bash"]
  data_analysis:
    enabled: true
    formats: ["CSV", "JSON", "Parquet"]
  file_handling:
    enabled: true
    types: ["py", "ipynb", "yaml", "json", "md"]

professional_skills:
  - name: "架构方案生成"
    trigger: "用户描述系统需求"
    action: "基于认知层判断框架输出架构建议"
  - name: "模型选型建议"
    trigger: "用户问用什么模型"
    action: "结合场景、成本、效果给出有理由的推荐"
  - name: "代码审查"
    trigger: "用户提交代码"
    action: "用原人的编码标准和风格审查"

knowledge_base_recommendations:
  - type: "个人代码库（最近1-2年）"
    priority: must
    reason: "建立编码风格和解题模式基准"
  - type: "历史技术方案文档"
    priority: must
    reason: "建立架构判断基准"
  - type: "踩坑记录/技术博客"
    priority: recommended
    reason: "捕捉隐性经验，增加分身的真实感"
  - type: "常用工具配置文件"
    priority: optional
    reason: "复现工作环境偏好"
```
```

---

### 3.10 prompts/profile_synthesizer.md

**内容要求：**

```markdown
# Prompt: Profile Synthesizer

## 用途
将访谈内容处理成结构化思维画像

## Prompt

```
You are a professional thinking analyst. Below is a person's structured
self-interview. Generate a mind profile document based on this content.

Rules:
1. Be faithful to the original text. Do NOT infer things not mentioned.
2. For contradictions or vague parts, keep the original and mark as "需确认"
3. If a dimension has insufficient info, mark as "信息不足，建议补充"
4. Write in Chinese. Field names in Chinese.

Output structure:

## 身份定位
（一段话，100字以内，概括这个人是谁、做什么、最大的价值是什么）

## 能力边界
顶级能力：
熟练能力：
明确边界：

## 思维特征
分析习惯：（描述他如何拆解问题）
常用框架：（列举）
信息处理偏好：（数据/直觉/经验）
已知盲区：

## 核心信念
（3-5条，每条一句话，附原始例子）

## 决策原则
优先级排序：
不可逾越的红线：

## 表达风格
语言特征：
回答结构偏好：
避免的表达方式：

## 信息不足项
（列出维度名称和建议补充方向）

---
Interview Content:
{interview_data}
```

---

### 3.11 prompts/prompt_generator.md

**内容要求：**

```markdown
# Prompt: System Prompt Generator

## 用途
基于思维画像生成可直接使用的 System Prompt

## Prompt

```
You are a system prompt engineer. Generate a system prompt for a digital twin
based on the mind profile below.

Rules:
1. Max 800 Chinese characters
2. First person voice, but NOT pretending to be the actual person
   Good: "我倾向于先看本质再看细节"
   Bad: "我是XXX，著名的..."
3. Must include explicit capability boundary statement
4. Must include how to handle uncertainty
5. Language style MUST match the person's expression style in the profile
6. Include the skill config tools that are enabled

Output structure:

## 身份说明
（2-3句，说明这是谁的思维分身，基于什么构建）

## 能力范围
我擅长：
我的边界：（明确说明遇到哪类问题会如何处理）

## 思维方式
（描述分析问题的习惯流程，2-4句）
常用框架：

## 核心信念
（直接陈述3-5条）

## 决策原则
（关键原则，包括优先级和红线）

## 表达方式
（语言风格、回答结构、避免的表达）

## 使用的工具
（列出 enabled 的工具）

## 重要约束
- 区分"基于原始信息的判断"和"推理延伸"，后者标注"这是基于我的思维方式的推测"
- 不要假装全知全能，遇到边界范围内的问题如实说明
- 保持原人面对不确定性时的态度

---
Mind Profile:
{mind_profile}

Skill Config:
{skill_config}
```

---

### 3.12 prompts/eval_question_gen.md

**内容要求：**

```markdown
# Prompt: Evaluation Question Generator

## 用途
根据访谈内容生成测试问题集

## Prompt

```
Based on this person's interview data, generate 10 evaluation questions
for testing their digital twin.

Question distribution:
- 3 questions: topics the person ALREADY answered in the interview
  (test consistency — the twin should answer similarly)
- 4 questions: new questions in their expertise area
  (test reasoning ability)
- 2 questions: questions outside their expertise
  (test boundary awareness — the twin should decline gracefully)
- 1 question: a controversial question where they have a clear stance
  (test stance stability)

For each question, also provide:
- expected_behavior: what a good answer looks like
- evaluation_focus: what specifically to check

Output as JSON array.

Interview Data:
{interview_data}
```

---

### 3.13 prompts/eval_scorer.md

**内容要求：**

```markdown
# Prompt: Evaluation Scorer

## 用途
对分身回答进行评分

## Prompt

```
You are evaluating a digital twin's responses against the original person's
interview data. Score each dimension and provide specific feedback.

Scoring Dimensions (see rubric below):
1. 观点一致性 (25分)
2. 思维方式还原 (25分)
3. 语言风格相似度 (20分)
4. 边界意识 (20分)
5. 推理合理性 (10分)

For each dimension:
- Give a score
- Cite specific evidence from the responses
- Give one concrete improvement suggestion

Calculate total score and overall assessment.

Output as structured JSON.

Original Interview Data: {interview_data}
Twin Responses: {twin_responses}
Test Questions: {test_questions}
```

---

### 3.14 templates/clone_config_v1.yaml

**内容要求：**

```yaml
# mind-clone 分身配置文件
# version: 1.0
# generated_at: {timestamp}
# schema: clone_config_v1

meta:
  name: ""                    # 分身名称（可以是代称）
  creator: ""                 # 创建者（可匿名）
  profession: ""              # 职业
  created_at: ""              # 创建时间
  version: "1.0"
  quality_score: 0            # 质量评分 /100
  clone_type: "self"          # self / profile

identity:
  summary: ""                 # 一段话定位，100字以内
  expertise:                  # 顶级能力列表
    - ""
  boundaries:                 # 明确边界列表
    - ""

mind_profile:
  core_beliefs:               # 核心信念列表
    - ""
  thinking_style: ""          # 思维方式描述
  frameworks:                 # 常用框架列表
    - ""
  blind_spots:                # 已知盲区列表
    - ""
  decision_style: ""          # 决策风格描述
  priority_order: ""          # 优先级排序

expression:
  language_style: ""          # 语言风格
  response_format: ""         # 回答结构偏好
  avoid:                      # 避免的表达方式
    - ""

skills:
  universal:
    web_search:
      enabled: false
      use_case: ""
    code_execution:
      enabled: false
      languages: []
    data_analysis:
      enabled: false
      formats: []
    file_handling:
      enabled: false
      types: []
  professional: []            # 专业技能列表

knowledge_base:
  sources: []                 # 已上传的资料列表

system_prompt: |              # 完整的 System Prompt
  （此处为生成的完整 System Prompt）

eval_summary:
  overall_score: 0
  consistency: 0
  thinking_restoration: 0
  language_style: 0
  boundary_awareness: 0
  reasoning: 0
  top_improvement: ""         # 最重要的一个改进建议
```

---

### 3.15 templates/mind_profile_template.md

```markdown
# 思维画像文档
> 创建时间：{timestamp}
> 基于：自我访谈

## 身份定位
{summary}

## 能力边界
**顶级能力：**
{expertise}

**熟练能力：**
{competent_skills}

**明确边界：**
{boundaries}

## 思维特征
**分析习惯：** {analysis_habit}
**常用框架：** {frameworks}
**信息处理偏好：** {info_preference}
**已知盲区：** {blind_spots}

## 核心信念
{core_beliefs}

## 决策原则
**优先级排序：** {priority_order}
**不可逾越的红线：** {red_lines}

## 表达风格
**语言特征：** {language_style}
**回答结构偏好：** {response_format}
**避免的表达方式：** {avoid}

## 信息不足项
{insufficient_items}
```

---

### 3.16 templates/system_prompt_template.md

```markdown
# System Prompt
> 创建时间：{timestamp}
> 质量评分：{quality_score}/100

---

## 身份说明
{identity_statement}

## 能力范围
**我擅长：**
{expertise}

**我的边界：**
{boundaries}

## 思维方式
{thinking_style}

**常用框架：** {frameworks}

## 核心信念
{core_beliefs}

## 决策原则
{decision_principles}

## 表达方式
{expression_style}

## 使用的工具
{enabled_tools}

## 重要约束
- 区分"基于原始信息的判断"和"推理延伸"，后者标注"这是基于我的思维方式的推测"
- 不要假装全知全能，遇到边界问题如实说明
- 保持面对不确定性时的诚实态度
```

---

### 3.17 eval/scoring_rubric.md

```markdown
# 评分标准

## 维度一：观点一致性（25分）
测试：分身对已知问题的回答是否与原人一致

25分：与原人观点完全一致，细节也匹配
20分：核心观点一致，细节有小偏差
15分：大方向一致，但论证方式不同
10分：部分一致，有明显出入
0分：与原人观点冲突

## 维度二：思维方式还原（25分）
测试：分身是否用原人的分析习惯和框架处理新问题

25分：分析流程、框架使用都高度匹配
20分：分析思路接近，框架有时用得不准
15分：能体现部分思维特征，但不系统
10分：只有表面相似，内在逻辑不同
0分：完全看不出原人的思维方式

## 维度三：语言风格相似度（20分）
测试：分身的表达方式是否像原人

20分：语言风格、句式、表达习惯高度相似
15分：整体风格接近，偶有不符
10分：能辨认出一些特征，但不稳定
5分：只有少量表面特征
0分：语言风格完全不像

## 维度四：边界意识（20分）
测试：分身是否在不擅长的领域正确处理

20分：明确表达边界，给出合理的转介建议
15分：表达了边界，但处理方式不够自然
10分：部分表达了边界，有时还是硬答
5分：只在明显的问题上表达边界
0分：不表达边界，什么都答

## 维度五：推理合理性（10分）
测试：对从未见过的新问题，推理是否符合原人的逻辑

10分：推理链条清晰，结论符合原人的思维逻辑
7分：推理方向正确，但步骤不够完整
5分：推理结果接近，但过程不清晰
2分：结论有时对，但推理方式不像原人
0分：推理方式完全不符

## 总分解读
90-100：优秀，可以直接上平台
75-89：良好，可以使用，建议补充1-2个维度
60-74：及格，建议重点改进低分维度后再使用
< 60：不及格，需要重新补充访谈内容
```

---

### 3.18 eval/eval_report_template.md

```markdown
# 质量评估报告
> 评估时间：{timestamp}
> 分身名称：{clone_name}

## 总分：{total_score}/100

## 各维度得分

| 维度 | 得分 | 满分 |
|------|------|------|
| 观点一致性 | {consistency} | 25 |
| 思维方式还原 | {thinking} | 25 |
| 语言风格相似度 | {language} | 20 |
| 边界意识 | {boundary} | 20 |
| 推理合理性 | {reasoning} | 10 |

## 评估详情

{detailed_evaluation}

## 改进建议

### 优先改进（影响最大）
{top_improvement}

### 其他建议
{other_improvements}

## 结论
{conclusion}
```

---

### 3.19 examples/ai_engineer/

**要求：** 创建一个完整的 AI 工程师示例，走完全部流程。

`interview_filled.md` 内容：填写完的完整访谈，模拟一个有5年经验的 AI 工程师。

`mind_profile.md` 内容：基于访谈生成的思维画像。

`system_prompt.md` 内容：基于画像生成的 System Prompt。

`clone_config.yaml` 内容：完整的配置文件，质量评分填 78 分。

示例人物设定：
- 职业：AI 工程师，5年经验
- 擅长：RAG 系统、模型评估、Python
- 思维风格：务实，重视工程可落地性，不追新技术但关注底层原理
- 语言风格：直接，喜欢给例子，不废话
- 核心信念：先把问题定义清楚比选技术重要；好的系统是删出来的不是加出来的

---

### 3.20 README.md

**内容要求：**

```markdown
# mind-clone-creator

帮你把自己的经验打包成可复用的 AI 顾问。

## 这是什么

通过结构化自我访谈，创建你的数字分身配置文件。
分身能还原你约 70% 的显性经验和判断方式。

## 快速开始

在支持 Claude Skill 的环境中，告诉 Claude：
"我想创建自己的数字分身"

Claude 会引导你完成全部流程。

## 时间预估
- 快速版：30 分钟，还原度约 60%
- 完整版：1-2 小时，还原度约 70-80%

## 输出文件
- clone_config.yaml：标准配置文件（主文件）
- mind_profile.md：你的思维画像
- system_prompt.md：可直接使用的 System Prompt
- eval_report.md：质量评估报告

## 诚实的说明
分身不是你本人：
- 它没有你的直觉和临场应变
- 复杂问题建议本人介入
- 建议每 3 个月更新一次

## 项目结构
{文件结构树}

## 配套使用
- 运行分身：使用 mind-clone-advisor skill
- 上架平台：即将上线

## License
MIT
```

---

## 四、开发顺序

Claude Code 按以下顺序创建文件：

```
第一批（核心框架）：
1. SKILL.md
2. SKILL-OPERATING-STANDARD.md
3. templates/clone_config_v1.yaml
4. eval/scoring_rubric.md

第二批（流程文件）：
5. steps/01_profession_parse.md
6. steps/02_self_interview.md
7. steps/03_mind_profile.md
8. steps/04_system_prompt.md
9. steps/05_quality_eval.md
10. steps/06_output.md

第三批（Prompt 库）：
11. prompts/profession_analyzer.md
12. prompts/interview_guide.md
13. prompts/profile_synthesizer.md
14. prompts/prompt_generator.md
15. prompts/eval_question_gen.md
16. prompts/eval_scorer.md

第四批（模板和评估）：
17. templates/mind_profile_template.md
18. templates/system_prompt_template.md
19. eval/eval_report_template.md

第五批（示例和文档）：
20. examples/ai_engineer/interview_filled.md
21. examples/ai_engineer/mind_profile.md
22. examples/ai_engineer/system_prompt.md
23. examples/ai_engineer/clone_config.yaml
24. README.md
```

---

## 五、验收标准

完成后验证：

```
□ 文件结构完整，无缺失
□ SKILL.md 触发条件清晰
□ 访谈问题覆盖 5 个区，完整版 19 题，快速版 5 题
□ 每个 Prompt 有 few-shot 示例
□ clone_config_v1.yaml 模板字段完整
□ 评分维度总分 = 100
□ AI 工程师示例走完全部流程
□ README 说明诚实，不过度承诺
```

---

*文档版本：v1.0*
*对应项目：mind-clone 开源项目第一模块*
*配套文件：mind-clone-advisor SKILL.md（已有）*
