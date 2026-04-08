# Prompt: Evaluation Scorer

## 用途

对分身回答进行评分。

## Prompt

```text
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

## Few-shot 示例

输入摘要：

- 一致性较好
- 语言风格偏书面
- 边界意识明确

输出片段：

```json
{
  "total_score": 78,
  "dimensions": {
    "consistency": {
      "score": 21,
      "evidence": "对问题定义优先于技术选型的观点与原访谈一致",
      "suggestion": "在回答已知问题时多保留原人的例子和措辞"
    },
    "language_style": {
      "score": 13,
      "evidence": "表达偏完整报告体，缺少原人口语化和直接感",
      "suggestion": "增加短句、先结论后解释，并加入具体案例"
    }
  },
  "overall_assessment": "可用，但建议先优化语言风格相似度"
}
```
