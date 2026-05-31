---
name: index-maintainer
description: Maintain Obsidian `_index.md` files by linking every Markdown note in each branch folder.
---

# index-maintainer

## Goal
Ensure each branch folder has a correct `_index.md`.

## Rules
- Do not delete existing `_index.md` content.
- Add missing links under `## 自动索引`.
- Exclude `_index.md` itself.
- Exclude `.git`, `.obsidian`, `.opencode`, `.agents`, `.codex`, `scripts`, `exports`, and `reports`.
- Use Obsidian links: `[[note name]]`.

## Output
- Created indexes
- Updated indexes
- Skipped folders
- Ambiguous duplicate notes
