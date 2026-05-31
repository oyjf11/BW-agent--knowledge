---
description: Identify source-code gaps and interview risks
agent: build
---

Use the `source-risk-audit` skill.

Input:
- `$1` = source repo path
- `$2` = project name

Target output:
`AI-Agent-Interview-Knowledge/11-源码证据库/$2-源码风险清单.md`

Rules:
1. Be conservative.
2. Distinguish implemented / partial / planning-only / no evidence.
3. Provide defensive wording.
4. Do not invent metrics.
5. Follow AGENTS.md.
