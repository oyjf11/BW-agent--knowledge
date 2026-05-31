---
description: Audit the Obsidian Vault structure without modifying files
agent: plan
---

Use the `vault-audit` skill.

Target Vault path:
- Use `$ARGUMENTS` if provided.
- Otherwise inspect `AI-Agent-Interview-Knowledge/`.

Rules:
1. Do not modify files.
2. Do not delete files.
3. Only inspect structure, metadata, templates, links, and empty notes.
4. Follow AGENTS.md.

Output:
- Summary
- Problems by severity
- Suggested fixes
- Files affected
- Risk level
- Next recommended command
