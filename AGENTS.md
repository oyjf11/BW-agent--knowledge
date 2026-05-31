# AGENTS.md

This workspace is used for AI / Agent interview knowledge management and source-code evidence mining.

## Correct placement

Place this toolkit at the workspace root.

Recommended layout:

```text
ai-interview-workspace/
├── AGENTS.md
├── .agents/skills/                 # Codex project skills
├── .opencode/skills/               # opencode project skills
├── .opencode/commands/             # opencode commands
├── .codex/prompts/                 # Codex prompt templates
├── scripts/
├── AI-Agent-Interview-Knowledge/   # Obsidian Vault
├── app-generator/
├── opspilot/
└── ai-coding-suite/
```

## Tool discovery rules

- Codex project skills: `.agents/skills/<name>/SKILL.md`
- opencode project skills: `.opencode/skills/<name>/SKILL.md`
- opencode commands: `.opencode/commands/<command>.md`

## Safety rules

1. Run or request `git status` before multi-file changes.
2. Do not delete files.
3. Do not overwrite existing content.
4. Do not invent project metrics.
5. Do not copy large source files into Obsidian notes.
6. Preserve the distinction between confirmed implementation and expression direction.

## Project fact policy

Use only facts present in the Vault, source code, user-provided resumes, user-provided project descriptions, or explicit user instructions.

If a project claim is plausible but not confirmed, write:

> 可作为表达方向，待补充事实依据。
