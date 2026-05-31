---
name: link-graph-builder
description: Build meaningful Obsidian double links across the Vault.
---

# link-graph-builder

## Goal
Improve the Vault knowledge graph.

## Rules
- Prefer linking to existing notes.
- Do not create new notes unless explicitly requested.
- Add at most 5 new semantic links per file by default.
- Do not add links just because words match.
- Preserve existing content.

## Link priorities
- Checkpoint ↔ State Machine / Event Log / Idempotency / Durable Execution
- RAG ↔ Chunk / Metadata / Hybrid Search / Rerank / RAG Eval
- Tool Calling ↔ Tool Schema / Tool Executor / MCP / Human Approval
- 应用生成智能体 ↔ Router / Planner / Supabase / RLS / Sandpack
- 运维智能体 ↔ Evidence / Diagnosis / Approval / Verification / RCA
