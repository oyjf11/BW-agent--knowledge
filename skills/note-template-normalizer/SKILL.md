---
name: note-template-normalizer
description: Normalize Obsidian Markdown note templates by adding missing frontmatter and required headings without overwriting existing content.
---

# note-template-normalizer

## Goal

Make note structure consistent without overwriting existing content.

## Concept note required headings

```markdown
## 一句话定义
## 解决什么问题
## 如何实现
## 项目映射
## 高频追问
## 我的回答要点
```

## Project note required headings

```markdown
## 30 秒版本
## 项目背景
## 核心流程
## 技术亮点
## 产品价值
## 指标结果
## Bad Case
## 我的贡献
## 可被追问的问题
```

## Rules

- Follow `AGENTS.md`.
- Do not delete files.
- Do not overwrite existing content.
- Do not invent project facts or metrics.
- For multi-file changes, output a plan first.

## Output format

Return changed files, skipped files, risks, and next recommended command.
