---
name: code-to-knowledge-map
description: Map source code modules to Obsidian knowledge-tree nodes and generate source-evidence mapping.
---

# code-to-knowledge-map

## Goal
Connect source modules to the AI / Agent knowledge tree.

## Rules
- Prefer existing Obsidian notes.
- Each mapping must include a source path.
- If no clear source evidence exists, mark `源码中未发现明确实现`.
- Do not copy large code blocks.

## Output table
| 源码模块 | 证据 | 对应知识点 | 面试价值 | 置信度 | 备注 |
|---|---|---|---|---|---|
