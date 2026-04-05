---
name: dash-sync
description: >
  Sync structured SSG Lab dashboard records from claude_local or codex_local agents
  into the Supabase dashboard via POST /api/dash-sync. Use when you need to mirror
  a project/company, sourcing result, matching result, or reactive agent telemetry.
  Requires SSGLAB_API_URL and DASH_SYNC_API_KEY. Prefer this skill after a durable
  Mimir write or when an agent heartbeat should update dashboard activity.
---

# dash-sync

Use this skill when a local Paperclip agent needs to mirror structured records into the SSG Lab dashboard without hand-writing `curl` commands.

## Environment

- Required: `SSGLAB_API_URL`
- Required: `DASH_SYNC_API_KEY`
- Optional: `DASH_SYNC_TIMEOUT_SECONDS` (default `15`)

## Command

Run:

```bash
python3 scripts/dash_sync.py <subcommand> ...
```

Subcommands:

- `project`: upsert one dashboard project/company row
- `sourcing`: upsert one sourcing result row and link it to a project
- `match`: upsert one match row, optionally linked to a project
- `telemetry`: record reactive agent activity in `portfolio_items`

Read [references/api-operations.md](references/api-operations.md) for the full parameter list and response shapes.

## Workflow

1. Keep Mimir as the source of truth; use this skill only after you already have structured data worth mirroring.
2. Reuse the stable Mimir entity id as `--mimir-entity-id` for `project`, `sourcing`, and `match`.
3. When you already know the dashboard project UUID, prefer `--project-id`; otherwise pass `--project-name` and let the route find or auto-create the project.
4. When auto-creating a project from `sourcing` or `match`, pass extra helper fields through `--data-json` if you have them (`industry`, `stage`, `project_status`, `founder_name`, `founder_contact`, `description`, `raw_data`).
5. For reactive agent activity, use `telemetry`; the wrapper defaults `mimir_entity_id` to `reactive-agent:<agent-url-key>`.
6. If dashboard sync fails, do not discard the upstream durable write. Report the sync failure separately.

## Examples

```bash
python3 scripts/dash_sync.py project \
  --mimir-entity-id entity_company_123 \
  --name "DesignAI" \
  --industry "AI tooling" \
  --stage "Seed" \
  --founder-name "Alice Chen" \
  --source "feishu-bot"

python3 scripts/dash_sync.py sourcing \
  --mimir-entity-id sourcing_signal_456 \
  --project-name "DesignAI" \
  --platform "feishu" \
  --summary "Founder intro from community member" \
  --raw-data-json '{"employee":"Bob"}'

python3 scripts/dash_sync.py match \
  --mimir-entity-id match_designai_megacorp \
  --project-name "DesignAI" \
  --match-type "supply-demand" \
  --confidence 92 \
  --matched-with "MegaCorp" \
  --rationale "DesignAI needs enterprise design teams."

python3 scripts/dash_sync.py telemetry \
  --agent-url-key feishu-bot \
  --channel feishu \
  --conversation-id oc_test_chat
```
