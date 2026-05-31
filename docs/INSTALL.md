# Install

Unzip this package into your workspace root.

## Show hidden files on macOS Finder

Press:

```text
Command + Shift + .
```

Dot directories such as `.agents`, `.opencode`, and `.codex` will become visible.

## Terminal verification

```bash
find .agents/skills -name SKILL.md
find .opencode/skills -name SKILL.md
find .opencode/commands -name "*.md"
```

Expected counts:

- `.agents/skills`: 12 SKILL.md files
- `.opencode/skills`: 12 SKILL.md files
- `.opencode/commands`: 12 command files
- `.codex/prompts`: 12 prompt files
