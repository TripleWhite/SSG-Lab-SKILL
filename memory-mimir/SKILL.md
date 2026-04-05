---
name: memory-mimir
description: >
  Use Mimir long-term memory from codex_local or claude_local agents when you need
  to store durable facts, search prior memories, traverse entity relationships,
  correct an entity, or delete a bad entity. Requires MIMIR_API_URL, MIMIR_API_KEY,
  and either MIMIR_USER_ID or a working /api/v1/me identity lookup. Prefer this skill
  for requests like "remember this", "what do we know about X", "show the graph around Y",
  "fix this entity summary", or "delete this wrong entity".
---

# memory-mimir

Use this skill when the task needs explicit Mimir memory operations from a local agent. The skill wraps the Mimir HTTP API behind one Python CLI so you do not have to hand-write `curl` payloads.

## Environment

- Required: `MIMIR_API_URL`, `MIMIR_API_KEY`
- Required unless identity lookup works: `MIMIR_USER_ID`
- Optional: `MIMIR_GROUP_ID` (defaults to `MIMIR_USER_ID`)

If `MIMIR_USER_ID` is unset, the script calls `GET /api/v1/me` and uses `user_id` and `group_id` from that response.

## Command

Run:

```bash
python3 scripts/mimir_memory.py <subcommand> ...
```

Subcommands:

- `store`: write a note, document, or session into Mimir
- `search`: query memories with retrieval and time filters
- `graph`: traverse the knowledge graph from entity names or IDs
- `update`: patch one entity by ID
- `delete`: delete one entity by ID and its attached relations

Read [references/api-operations.md](references/api-operations.md) for the full parameter list and response shapes.

## Workflow

1. Resolve the smallest operation that answers the request.
2. Use `search` or `graph` first when you need an entity ID before `update` or `delete`.
3. When storing a new durable fact, prefer `store --kind note` unless the user supplied a full conversation transcript or document.
4. When correcting bad extracted data, use `update` so the entity stays curated instead of adding a conflicting note.
5. When removing obviously wrong entities, use `delete` only after confirming the entity ID from `search` or `graph`.

## Examples

```bash
python3 scripts/mimir_memory.py store --kind note --content "Arthur prefers pour-over coffee."
python3 scripts/mimir_memory.py search --query "coffee preference" --top-k 5
python3 scripts/mimir_memory.py graph --entity-name Arthur --hops 2
python3 scripts/mimir_memory.py update --entity-id ent_123 --summary "CTO at Mimir" --alias "Arthur Wu"
python3 scripts/mimir_memory.py delete --entity-id ent_bad_456
```
