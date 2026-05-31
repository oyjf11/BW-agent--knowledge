---
name: note-template-normalizer
description: Normalize Obsidian Markdown notes by adding missing frontmatter and required headings without overwriting existing content.
---

# note-template-normalizer

## Goal
Make note structure consistent.

## Required concept headings
- ## 一句话定义
- ## 解决什么问题
- ## 如何实现
- ## 项目映射
- ## 高频追问
- ## 我的回答要点

## Rules
- Do not overwrite existing content.
- Do not remove custom sections.
- Add missing headings at the end if placement is ambiguous.
- Preserve existing YAML frontmatter.
- Add frontmatter only if missing.
- Do not generate full content unless explicitly asked.
