Use the `source-audit` skill.

Input:
- Source repo path is `$ARGUMENTS`.
- If missing, ask for the source repo path.

Rules:
1. Do not modify files.
2. Do not copy large source code.
3. Prefer source paths and module names as evidence.
4. Do not invent metrics.
5. Follow AGENTS.md.

Output:
1. Tech stack
2. Directory structure
3. Core modules
4. Main execution chain
5. AI / Agent capabilities found
6. Interview evidence candidates
7. Risks / uncertain points