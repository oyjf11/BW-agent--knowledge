---
name: link-graph-builder
description: Build and repair meaningful Obsidian double links across the Vault.
---

# link-graph-builder

## Goal

Improve the Vault knowledge graph with meaningful Obsidian double links.

## Link priorities

1. `Checkpoint` ↔ `State Machine`, `Event Log`, `Idempotency`, `Durable Execution`, `Human-in-the-loop`
2. `RAG` ↔ `Chunk`, `Metadata`, `Hybrid Search`, `Rerank`, `RAG Eval`
3. `Tool Calling` ↔ `Tool Schema`, `Tool Executor`, `MCP Server`, `MCP Gateway`, `Human Approval`
4. `应用生成智能体` ↔ `Router`, `Planner`, `Supabase`, `RLS`, `Sandpack`, `QA Agent`
5. `运维智能体` ↔ `Evidence Gathering`, `Diagnosis`, `Approval`, `Execution Verification`, `RCA`

## Constraints

- Prefer existing notes.
- Add at most 5 new links per file by default.
- Do not add links just because words match.

## Rules

- Follow `AGENTS.md`.
- Do not delete files.
- Do not overwrite existing content.
- Do not invent project facts or metrics.
- For multi-file changes, output a plan first.

## Output format

Return changed files, skipped files, risks, and next recommended command.
