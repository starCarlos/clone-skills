# Prompt: Evaluation Question Generator

## 用途

根据访谈内容生成测试问题集。

## Prompt

```text
Based on this person's interview data, generate 10 evaluation questions
for testing their digital twin.

Question distribution:
- 3 questions: topics the person ALREADY answered in the interview
  (test consistency - the twin should answer similarly)
- 4 questions: new questions in their expertise area
  (test reasoning ability)
- 2 questions: questions outside their expertise
  (test boundary awareness - the twin should decline gracefully)
- 1 question: a controversial question where they have a clear stance
  (test stance stability)

For each question, also provide:
- expected_behavior: what a good answer looks like
- evaluation_focus: what specifically to check

Output as JSON array.

Interview Data:
{interview_data}
```

## Few-shot 示例

输入摘要：

- 用户明确说自己擅长 RAG、评估
- 不擅长纯前端设计
- 对“先定义问题再选技术”有明确立场

输出片段：

```json
[
  {
    "question": "你为什么总强调先把问题定义清楚，再谈技术选型？",
    "expected_behavior": "回答应重现其对问题定义优先级的立场，并举一个真实决策思路",
    "evaluation_focus": "观点一致性"
  },
  {
    "question": "如果一个检索系统召回率很高但延迟超标，你会怎么排查？",
    "expected_behavior": "按工程排障顺序拆问题，体现可落地性",
    "evaluation_focus": "思维方式还原"
  }
]
```
