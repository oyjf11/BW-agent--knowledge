---
name: vault-audit
description: Audit Obsidian Vault structure, metadata, templates, links, and coverage. Read-only by default.
---

# vault-audit

## Goal
Audit an Obsidian Vault without modifying files.

## Use when
- checking Vault structure
- finding missing `_index.md`
- finding broken links
- finding empty notes
- checking frontmatter and template consistency
- generating a Vault health report

## Rules
- Read-only by default.
- Never delete files.
- Never overwrite content.
- Never invent project facts or metrics.
- Prefer exact file paths in reports.

## Checklist
1. Folder structure.
2. `_index.md` coverage.
3. Markdown file count.
4. Empty or near-empty notes.
5. Missing YAML frontmatter.
6. Missing required headings.
7. Broken Obsidian links.
8. Duplicate titles.
9. Inconsistent tags.
10. Oversized notes.
11. Project mapping coverage.
12. Interview question coverage.

## Output
Return:
- Summary
- Problems by severity
- Affected files
- Suggested fixes
- Recommended next command
