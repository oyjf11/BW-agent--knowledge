---
description: Map source code modules to Obsidian knowledge-tree nodes
agent: build
---

Use the `code-to-knowledge-map` skill.

Input:
- `$1` = source repo path
- `$2` = project name

Target output:
`AI-Agent-Interview-Knowledge/11-源码证据库/$2-源码到知识点映射.md`

Rules:
1. Every mapping must include source path evidence.
2. Link to existing Obsidian notes where possible.
3. Do not invent implementation claims.
4. Follow AGENTS.md.
