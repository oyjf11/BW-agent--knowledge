# AI Agent Workspace Toolkit v3

This package includes both real hidden discovery paths and visible copies.

## Real discovery paths

- `.agents/skills/<skill-name>/SKILL.md`
- `.opencode/skills/<skill-name>/SKILL.md`
- `.opencode/commands/<command>.md`
- `.codex/prompts/<prompt>.md`

## Visible copies

Because macOS Finder hides dot-directories, the same files are also copied under:

```text
VISIBLE-COPY/
├── agents-skills/
├── opencode-skills/
├── opencode-commands/
└── codex-prompts/
```

These visible copies are only for inspection. The real runtime paths are the dot-directories above.

## Verify after unzip

```bash
find .agents/skills -name SKILL.md
find .opencode/skills -name SKILL.md
find .opencode/commands -name "*.md"
```
