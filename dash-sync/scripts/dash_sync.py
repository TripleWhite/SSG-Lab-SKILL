#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Optional


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def env(name: str, required: bool = True, default: str = "") -> str:
    value = os.environ.get(name, default).strip()
    if required and not value:
        fail(f"missing required environment variable: {name}")
    return value


def parse_timeout_seconds() -> float:
    raw = env("DASH_SYNC_TIMEOUT_SECONDS", required=False, default="15")
    if not raw:
        return 15.0
    try:
        timeout = float(raw)
    except ValueError:
        fail("DASH_SYNC_TIMEOUT_SECONDS must be a positive number")
    if timeout <= 0:
        fail("DASH_SYNC_TIMEOUT_SECONDS must be a positive number")
    return timeout


def parse_json_object(label: str, raw: Optional[str]) -> Dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid {label}: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must decode to a JSON object")
    return value


def merge_data(extra_json: Optional[str], explicit: Dict) -> Dict:
    payload = parse_json_object("data-json", extra_json)
    for key, value in explicit.items():
        if value is not None:
            payload[key] = value
    return payload


def request(payload: Dict) -> Dict:
    base_url = env("SSGLAB_API_URL")
    api_key = env("DASH_SYNC_API_KEY")
    timeout = parse_timeout_seconds()
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "api/dash-sync")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"POST /api/dash-sync failed: {exc.code} {body}", exc.code)
    except urllib.error.URLError as exc:
        fail(f"POST /api/dash-sync failed: {exc}")

    if not body:
        return {}

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        fail(f"dash-sync response was not valid JSON: {exc}")

    if isinstance(parsed, dict) and parsed.get("status") == "error":
        fail(json.dumps(parsed, ensure_ascii=False))

    if not isinstance(parsed, dict):
        fail("dash-sync response must be a JSON object")

    return parsed


def print_json(data: Dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def require_non_empty(label: str, value: Optional[str]) -> str:
    if value is None or not value.strip():
        fail(f"{label} is required")
    return value.strip()


def metadata_arg(raw: Optional[str]) -> Optional[Dict]:
    if raw is None:
        return None
    return parse_json_object("metadata-json", raw)


def raw_data_arg(raw: Optional[str]) -> Optional[Dict]:
    if raw is None:
        return None
    return parse_json_object("raw-data-json", raw)


def handle_project(args) -> None:
    data = merge_data(
        args.data_json,
        {
            "name": require_non_empty("name", args.name),
            "industry": args.industry,
            "stage": args.stage,
            "status": args.status,
            "founder_name": args.founder_name,
            "founder_contact": args.founder_contact,
            "description": args.description,
            "source": args.source,
            "metadata": metadata_arg(args.metadata_json),
        },
    )
    payload = {
        "action": "upsert_project",
        "mimir_entity_id": require_non_empty("mimir-entity-id", args.mimir_entity_id),
        "data": data,
    }
    print_json(request(payload))


def handle_sourcing(args) -> None:
    data = merge_data(
        args.data_json,
        {
            "project_id": args.project_id,
            "project_name": args.project_name,
            "platform": require_non_empty("platform", args.platform),
            "url": args.url,
            "title": args.title,
            "summary": args.summary,
            "raw_data": raw_data_arg(args.raw_data_json),
            "sourced_at": args.sourced_at,
        },
    )
    payload = {
        "action": "upsert_sourcing",
        "mimir_entity_id": require_non_empty("mimir-entity-id", args.mimir_entity_id),
        "data": data,
    }
    print_json(request(payload))


def handle_match(args) -> None:
    data = merge_data(
        args.data_json,
        {
            "project_id": args.project_id,
            "project_name": args.project_name,
            "match_type": args.match_type,
            "confidence": args.confidence,
            "rationale": args.rationale,
            "matched_with": args.matched_with,
            "status": args.status,
            "metadata": metadata_arg(args.metadata_json),
        },
    )
    payload = {
        "action": "upsert_match",
        "mimir_entity_id": require_non_empty("mimir-entity-id", args.mimir_entity_id),
        "data": data,
    }
    print_json(request(payload))


def handle_telemetry(args) -> None:
    agent_url_key = require_non_empty("agent-url-key", args.agent_url_key).lower()
    data = merge_data(
        args.data_json,
        {
            "agent_url_key": agent_url_key,
            "channel": args.channel,
            "conversation_id": args.conversation_id,
            "event_type": args.event_type,
            "occurred_at": args.occurred_at,
            "source": args.source,
        },
    )
    mimir_entity_id = (
        args.mimir_entity_id.strip()
        if args.mimir_entity_id is not None and args.mimir_entity_id.strip()
        else f"reactive-agent:{agent_url_key}"
    )
    payload = {
        "action": "record_reactive_telemetry",
        "mimir_entity_id": mimir_entity_id,
        "data": data,
    }
    print_json(request(payload))


def build_parser():
    parser = argparse.ArgumentParser(description="Mirror structured data into the SSG Lab dashboard")
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project", help="upsert a dashboard project/company row")
    project.add_argument("--mimir-entity-id", required=True)
    project.add_argument("--name", required=True)
    project.add_argument("--industry")
    project.add_argument("--stage")
    project.add_argument("--status")
    project.add_argument("--founder-name")
    project.add_argument("--founder-contact")
    project.add_argument("--description")
    project.add_argument("--source")
    project.add_argument("--metadata-json")
    project.add_argument("--data-json")
    project.set_defaults(func=handle_project)

    sourcing = sub.add_parser("sourcing", help="upsert a sourcing result row")
    sourcing.add_argument("--mimir-entity-id", required=True)
    sourcing_project = sourcing.add_mutually_exclusive_group(required=True)
    sourcing_project.add_argument("--project-id")
    sourcing_project.add_argument("--project-name")
    sourcing.add_argument("--platform", required=True)
    sourcing.add_argument("--url")
    sourcing.add_argument("--title")
    sourcing.add_argument("--summary")
    sourcing.add_argument("--raw-data-json")
    sourcing.add_argument("--sourced-at")
    sourcing.add_argument("--data-json")
    sourcing.set_defaults(func=handle_sourcing)

    match = sub.add_parser("match", help="upsert a match result row")
    match.add_argument("--mimir-entity-id", required=True)
    match.add_argument("--project-id")
    match.add_argument("--project-name")
    match.add_argument("--match-type")
    match.add_argument("--confidence", type=float)
    match.add_argument("--rationale")
    match.add_argument("--matched-with")
    match.add_argument("--status")
    match.add_argument("--metadata-json")
    match.add_argument("--data-json")
    match.set_defaults(func=handle_match)

    telemetry = sub.add_parser("telemetry", help="record reactive agent telemetry")
    telemetry.add_argument("--agent-url-key", required=True)
    telemetry.add_argument("--mimir-entity-id")
    telemetry.add_argument("--channel")
    telemetry.add_argument("--conversation-id")
    telemetry.add_argument("--event-type")
    telemetry.add_argument("--occurred-at")
    telemetry.add_argument("--source")
    telemetry.add_argument("--data-json")
    telemetry.set_defaults(func=handle_telemetry)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
