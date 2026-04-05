# Dash Sync Operations

All commands use:

- `Authorization: Bearer $DASH_SYNC_API_KEY`
- Base URL: `$SSGLAB_API_URL`
- Route: `POST /api/dash-sync`

The wrapper prints the JSON response body and exits non-zero on HTTP failures or `{"status":"error"}` envelopes.

## `project`

Mirror one company/project row into the dashboard.

```bash
python3 scripts/dash_sync.py project \
  --mimir-entity-id entity_company_123 \
  --name "DesignAI"
```

Parameters:

- `--mimir-entity-id`: required stable Mimir entity id
- `--name`: required project/company name
- `--industry`, `--stage`, `--status`: optional project fields
- `--founder-name`, `--founder-contact`, `--description`: optional project fields
- `--source`: optional source label; defaults on the server to `dash_sync`
- `--metadata-json`: optional JSON object for `data.metadata`
- `--data-json`: optional JSON object merged into `data` before explicit flags

Route behavior:

- Uses the Mimir entity id to derive a deterministic dashboard id.
- If a project with the same name already exists, the route reuses that row id instead of creating a duplicate.

Success result:

- `table: "projects"`
- `id`
- `project_id`
- `auto_created_project: false`

## `sourcing`

Mirror one sourcing result row.

```bash
python3 scripts/dash_sync.py sourcing \
  --mimir-entity-id sourcing_signal_456 \
  --project-name "DesignAI" \
  --platform "feishu"
```

Parameters:

- `--mimir-entity-id`: required stable Mimir entity id
- one of `--project-id` or `--project-name`: required
- `--platform`: required sourcing origin
- `--url`, `--title`, `--summary`: optional sourcing fields
- `--raw-data-json`: optional JSON object for `data.raw_data`
- `--sourced-at`: optional RFC3339 timestamp
- `--data-json`: optional JSON object merged into `data` before explicit flags

Route behavior:

- Requires either `project_id` or `project_name`.
- If only `project_name` is provided, the route first looks up an existing project by name.
- If the project does not exist, the route auto-creates one and uses helper fields from `--data-json` such as `industry`, `stage`, `project_status`, `founder_name`, `founder_contact`, `description`, or `raw_data`.

Success result:

- `table: "sourcing_results"`
- `id`
- `project_id`
- `auto_created_project`

## `match`

Mirror one match result row.

```bash
python3 scripts/dash_sync.py match \
  --mimir-entity-id match_designai_megacorp \
  --project-name "DesignAI" \
  --match-type "supply-demand" \
  --confidence 92
```

Parameters:

- `--mimir-entity-id`: required stable Mimir entity id
- `--project-id`, `--project-name`: optional project link
- `--match-type`: optional match type label
- `--confidence`: optional number; accepts `0-1` or `0-100`
- `--rationale`: optional rationale text
- `--matched-with`: optional target name/id text
- `--status`: optional match status; defaults on the server to `pending`
- `--metadata-json`: optional JSON object for `data.metadata`
- `--data-json`: optional JSON object merged into `data` before explicit flags

Route behavior:

- If `project_id` or `project_name` is omitted, the match row can still be written with `project_id: null`.
- If `project_name` is present but the project does not exist, the route auto-creates it using the same helper fields described in `sourcing`.
- `confidence` values above `1` are normalized as percentages and clamped into `0-1`.

Success result:

- `table: "matches"`
- `id`
- `project_id`
- `auto_created_project`

## `telemetry`

Record reactive agent activity in the dashboard.

```bash
python3 scripts/dash_sync.py telemetry \
  --agent-url-key feishu-bot \
  --channel feishu \
  --conversation-id oc_test_chat
```

Parameters:

- `--agent-url-key`: required Paperclip/OpenClaw agent url key
- `--mimir-entity-id`: optional; defaults to `reactive-agent:<agent-url-key>`
- `--channel`: optional transport label
- `--conversation-id`: optional conversation id
- `--event-type`: optional event type; defaults on the server to `message_received`
- `--occurred-at`: optional RFC3339 timestamp
- `--source`: optional source label; defaults on the server to `dash_sync`
- `--data-json`: optional JSON object merged into `data` before explicit flags

Route behavior:

- Writes into `portfolio_items`, not `projects`.
- The server computes the dashboard row id from `agent_url_key`, so repeated telemetry writes update the same row.

Success result:

- `table: "portfolio_items"`
- `id`
- `project_id: null`
- `agent_url_key`
- `recorded_at`
