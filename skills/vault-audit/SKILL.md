---
name: vault-audit
description: Audit an Obsidian Vault for structure, metadata, templates, links, and coverage. Read-only by default.
---

# vault-audit

## Goal

Audit an Obsidian Vault without modifying files.

## Checklist

1. Folder structure.
2. `_index.md` coverage.
3. Markdown file count.
4. Empty or near-empty notes.
5. Missing YAML frontmatter.
6. Missing required headings.
7. Broken Obsidian links.
8. Unreferenced notes.
9. Duplicate titles.
10. Inconsistent tags.
11. Oversized notes.
12. Project mapping coverage.
13. Interview question coverage.
14. Files outside expected branch structure.

## Output

`# Vault Audit Report` with summary, problems by severity, affected files, suggested fixes, and recommended next command.
