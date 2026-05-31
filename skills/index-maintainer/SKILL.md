---
name: index-maintainer
description: Maintain Obsidian `_index.md` files by linking every Markdown note in each branch folder.
---

# index-maintainer

## Goal

Ensure every branch folder has a correct `_index.md` file.

## Procedure

1. Scan branch folders.
2. Identify Markdown files in each branch.
3. Create `_index.md` if missing.
4. Add missing note links.
5. Keep links sorted by filename where possible.
6. Preserve existing custom notes.

## Rules

- Follow `AGENTS.md`.
- Do not delete files.
- Do not overwrite existing content.
- Do not invent project facts or metrics.
- For multi-file changes, output a plan first.

## Output format

Return changed files, skipped files, risks, and next recommended command.
