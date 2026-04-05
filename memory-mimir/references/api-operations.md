# Mimir Memory Operations

All commands use:

- `Authorization: Bearer $MIMIR_API_KEY`
- Base URL: `$MIMIR_API_URL`
- Default `group_id`: `$MIMIR_GROUP_ID` or resolved `user_id`

## `store`

Write new memory into Mimir.

```bash
python3 scripts/mimir_memory.py store --kind note --content "..."
python3 scripts/mimir_memory.py store --kind document --title "Spec" --content "..."
python3 scripts/mimir_memory.py store --kind session --messages-file /abs/path/messages.json
```

Parameters:

- `--kind`: `note`, `document`, or `session`
- `--content`: required for `note` and `document`
- `--title`: optional for `document`
- `--mime-type`: optional for `document`, default `text/plain`
- `--source-url`: optional for `document`
- `--note-id`, `--document-id`: optional caller IDs
- `--messages-file`: required for `session`; JSON array of `{role,sender_name,content}`
- `--timestamp`: optional RFC3339 timestamp
- `--confidence`: optional `HIGH|MEDIUM|LOW`
- `--source`: optional `auto_extracted|agent_curated|user_explicit`

Requests:

- `POST /api/v1/ingest/note`
- `POST /api/v1/ingest/document`
- `POST /api/v1/ingest/session`

Response handling:

- Prints the JSON envelope returned by Mimir.
- Exits non-zero on non-2xx or `"status":"error"`.

## `search`

Search memories.

```bash
python3 scripts/mimir_memory.py search --query "Arthur coffee" --memory-type entity --memory-type relation
```

Parameters:

- `--query`: required
- `--method`: `full`, `rrf`, `bm25`, `keyword`, `vector`, `agentic`; default `full`
- `--memory-type`: repeatable; e.g. `event_log`, `entity`, `relation`, `foresight`
- `--top-k`: default `10`
- `--start-time`, `--end-time`: optional RFC3339 or `YYYY-MM-DD`

Request:

- `POST /api/v1/search`

Response handling:

- Prints the JSON envelope from Mimir.
- Use returned entity IDs for `update` or `delete`.

## `graph`

Traverse the graph around seed entities.

```bash
python3 scripts/mimir_memory.py graph --entity-name Arthur --entity-name Sarah --hops 2
```

Parameters:

- One of `--entity-name` or `--entity-id`, both repeatable
- `--hops`: default `2`
- `--max-results`: default `100`
- `--relation-type`: optional repeatable filter
- `--entity-type`: optional repeatable filter

Request:

- `POST /api/v1/graph/traverse`

Response handling:

- Prints the JSON envelope from Mimir.
- Returned `seed_entities`, `entities`, and `relations` are suitable for review or follow-up mutation.

## `update`

Patch an entity by ID.

```bash
python3 scripts/mimir_memory.py update --entity-id ent_123 --name "Arthur Wu" --summary "Lead engineer"
```

Parameters:

- `--entity-id`: required
- `--name`: optional
- `--summary`: optional
- `--alias`: repeatable
- `--attribute key=value`: repeatable

Request:

- `PATCH /api/v1/entities/{id}`

Response handling:

- Prints the updated entity envelope.
- Manual updates mark the entity as agent-curated on the server so later auto-extraction does not clobber it.

## `delete`

Delete one entity and all relations attached to it.

```bash
python3 scripts/mimir_memory.py delete --entity-id ent_bad_456
```

Parameters:

- `--entity-id`: required

Request:

- `DELETE /api/v1/entities/{id}`

Response handling:

- Prints `{entity_id, deleted_relations}` in the standard envelope.
- Use only after confirming the target ID from `search` or `graph`.
