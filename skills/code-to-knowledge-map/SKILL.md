---
name: code-to-knowledge-map
description: Map source code modules to Obsidian knowledge-tree nodes and generate source-evidence mapping.
---

# code-to-knowledge-map

## Goal

Connect source modules to the AI / Agent knowledge tree.

## Mapping dimensions

- Source module path
- Function / class / config evidence
- Knowledge tree node
- Interview value
- Confidence: high / medium / low
- Notes / caveats

## Rules

- Every mapping must include source path evidence.
- If no clear source evidence exists, mark `源码中未发现明确实现`.
- Do not copy large code blocks.
