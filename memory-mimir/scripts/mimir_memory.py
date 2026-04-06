#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        fail(f"missing required environment variable: {name}")
    return value


def request(method: str, path: str, payload=None):
    base_url = env("MIMIR_API_URL")
    api_key = env("MIMIR_API_KEY")
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "mimir-agent/1.0",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"{method} {path} failed: {exc.code} {body}", exc.code)
    except urllib.error.URLError as exc:
        fail(f"{method} {path} failed: {exc}")


def resolve_identity():
    user_id = os.environ.get("MIMIR_USER_ID", "").strip()
    group_id = os.environ.get("MIMIR_GROUP_ID", "").strip()
    if user_id:
        return user_id, group_id or user_id
    body = request("GET", "/api/v1/me")
    if not isinstance(body, dict):
        fail("unexpected response from /api/v1/me")
    user_id = body.get("user_id", "").strip()
    if not user_id:
        fail("unable to resolve user_id from /api/v1/me")
    group_id = body.get("group_id", "").strip() or user_id
    return user_id, group_id


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def handle_store(args):
    user_id, group_id = resolve_identity()
    common = {
        "user_id": user_id,
        "group_id": group_id,
    }
    if args.timestamp:
        common["timestamp"] = args.timestamp
    if args.confidence:
        common["confidence"] = args.confidence
    if args.source:
        common["source"] = args.source

    if args.kind == "note":
        payload = dict(common)
        payload["content"] = args.content
        if args.note_id:
            payload["note_id"] = args.note_id
        body = request("POST", "/api/v1/ingest/note", payload)
    elif args.kind == "document":
        payload = dict(common)
        payload["title"] = args.title or ""
        payload["content"] = args.content
        payload["mime_type"] = args.mime_type
        if args.document_id:
            payload["document_id"] = args.document_id
        if args.source_url:
            payload["source_url"] = args.source_url
        body = request("POST", "/api/v1/ingest/document", payload)
    else:
        with open(args.messages_file, "r", encoding="utf-8") as handle:
            messages = json.load(handle)
        payload = dict(common)
        payload["messages"] = messages
        body = request("POST", "/api/v1/ingest/session", payload)
    print_json(body)


def handle_search(args):
    user_id, group_id = resolve_identity()
    payload = {
        "query": args.query,
        "user_id": user_id,
        "group_id": group_id,
        "retrieve_method": args.method,
        "top_k": args.top_k,
    }
    if args.memory_type:
        payload["memory_types"] = args.memory_type
    if args.start_time:
        payload["start_time"] = args.start_time
    if args.end_time:
        payload["end_time"] = args.end_time
    print_json(request("POST", "/api/v1/search", payload))


def handle_graph(args):
    _, group_id = resolve_identity()
    payload = {
        "group_id": group_id,
        "hops": args.hops,
        "max_results": args.max_results,
    }
    if args.entity_name:
        payload["entity_names"] = args.entity_name
    if args.entity_id:
        payload["entity_ids"] = args.entity_id
    if args.relation_type:
        payload["relation_types"] = args.relation_type
    if args.entity_type:
        payload["entity_types"] = args.entity_type
    print_json(request("POST", "/api/v1/graph/traverse", payload))


def parse_attributes(values):
    attributes = {}
    for item in values:
        if "=" not in item:
            fail(f"invalid --attribute value {item!r}; expected key=value")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            fail(f"invalid --attribute value {item!r}; key cannot be empty")
        attributes[key] = value
    return attributes


def handle_update(args):
    payload = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.summary is not None:
        payload["summary"] = args.summary
    if args.alias:
        payload["aliases"] = args.alias
    if args.attribute:
        payload["attributes"] = parse_attributes(args.attribute)
    if not payload:
        fail("update requires at least one patch field")
    print_json(request("PATCH", f"/api/v1/entities/{args.entity_id}", payload))


def handle_delete(args):
    print_json(request("DELETE", f"/api/v1/entities/{args.entity_id}"))


def build_parser():
    parser = argparse.ArgumentParser(description="Explicit Mimir memory operations")
    sub = parser.add_subparsers(dest="command", required=True)

    store = sub.add_parser("store", help="store note, document, or session")
    store.add_argument("--kind", choices=["note", "document", "session"], required=True)
    store.add_argument("--content")
    store.add_argument("--title")
    store.add_argument("--mime-type", default="text/plain")
    store.add_argument("--source-url")
    store.add_argument("--note-id")
    store.add_argument("--document-id")
    store.add_argument("--messages-file")
    store.add_argument("--timestamp")
    store.add_argument("--confidence")
    store.add_argument("--source")
    store.set_defaults(func=handle_store)

    search = sub.add_parser("search", help="search memory")
    search.add_argument("--query", required=True)
    search.add_argument("--method", default="full")
    search.add_argument("--memory-type", action="append")
    search.add_argument("--top-k", type=int, default=10)
    search.add_argument("--start-time")
    search.add_argument("--end-time")
    search.set_defaults(func=handle_search)

    graph = sub.add_parser("graph", help="traverse the graph")
    graph.add_argument("--entity-name", action="append")
    graph.add_argument("--entity-id", action="append")
    graph.add_argument("--hops", type=int, default=2)
    graph.add_argument("--max-results", type=int, default=100)
    graph.add_argument("--relation-type", action="append")
    graph.add_argument("--entity-type", action="append")
    graph.set_defaults(func=handle_graph)

    update = sub.add_parser("update", help="patch an entity")
    update.add_argument("--entity-id", required=True)
    update.add_argument("--name")
    update.add_argument("--summary")
    update.add_argument("--alias", action="append")
    update.add_argument("--attribute", action="append")
    update.set_defaults(func=handle_update)

    delete = sub.add_parser("delete", help="delete an entity")
    delete.add_argument("--entity-id", required=True)
    delete.set_defaults(func=handle_delete)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "store":
        if args.kind in {"note", "document"} and not args.content:
            fail("--content is required for note/document store")
        if args.kind == "session" and not args.messages_file:
            fail("--messages-file is required for session store")
    if args.command == "graph" and not (args.entity_name or args.entity_id):
        fail("graph requires at least one --entity-name or --entity-id")

    args.func(args)


if __name__ == "__main__":
    main()
