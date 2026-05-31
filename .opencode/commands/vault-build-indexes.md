---
description: Build or refresh _index.md files for all branch folders
agent: build
---

Use the `index-maintainer` skill.

Target Vault path:
- Use `$ARGUMENTS` if provided.
- Otherwise use `AI-Agent-Interview-Knowledge/`.

Rules:
1. Do not delete existing index content.
2. Add missing links under `## 自动索引`.
3. Exclude technical folders.
4. Follow AGENTS.md.
