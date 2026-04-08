# Prompt: Profile Synthesizer

## 用途

将访谈内容处理成结构化思维画像。

## Prompt

```text
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

## Few-shot 示例

输入摘要：

- 身份：AI 工程师，做 RAG 和评估
- 原则：先定义问题，再选技术
- 风格：直接，喜欢举例
- 边界：不做拍脑袋上线

输出片段：

```markdown
## 身份定位
主要做 AI 系统工程，擅长把模型能力落到真实业务里，价值在于把问题定义清楚并做成可上线方案。

## 能力边界
顶级能力：RAG 系统设计、模型评估、Python 工程化
熟练能力：数据处理、实验设计
明确边界：对缺少业务目标的问题不会直接给方案；不熟悉的行业问题会先说明假设

## 信息不足项
- 价值排序：建议补充一个速度和质量冲突时的真实决策案例
```
