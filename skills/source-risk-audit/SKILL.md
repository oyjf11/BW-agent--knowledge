---
name: source-risk-audit
description: Identify source-code gaps and interview risks by comparing claimed capabilities with actual implementation evidence.
---

# source-risk-audit

## Goal

Identify which claims are strongly supported by source code and which are weak.

## Categories

- 已有源码明确实现
- 有设计痕迹但实现不完整
- 仅适合作为规划表达
- 未发现证据

## Output

```markdown
# 源码风险清单

| 风险点 | 证据状态 | 原因 | 防守表述 | 建议补充 |
|---|---|---|---|---|
```
