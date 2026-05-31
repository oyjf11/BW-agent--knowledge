---
name: project-evidence-card
description: Generate source-based project evidence cards for interview expression.
---

# project-evidence-card

## Goal

Turn source code evidence into interview-ready project evidence cards.

## Card template

```markdown
# 证据卡：{能力点}

## 对应源码
## 解决的问题
## 实现方式
## 面试怎么讲
## 可能追问
## 证据强度
## 待确认点
```

## Rules

- Every card must contain source paths.
- Do not claim implementation without source evidence.
- Mark missing evidence as `源码中未发现明确实现`.
