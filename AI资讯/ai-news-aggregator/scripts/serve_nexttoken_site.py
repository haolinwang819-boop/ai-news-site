#!/usr/bin/env python3
"""
Serve the static website and persist subscription requests.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from subscription_registry import DEFAULT_REGISTRY_PATH, active_subscriptions, upsert_subscription
from supabase_subscription_store import upsert_subscription_to_supabase


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
WEBSITE_DIR = WORKSPACE_ROOT / "website"


class NextTokenSiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBSITE_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "registryPath": str(DEFAULT_REGISTRY_PATH),
                    "activeSubscriberCount": len(active_subscriptions()),
                },
            )
            return
        if parsed.path == "/api/subscriptions":
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "subscribers": active_subscriptions(),
                },
            )
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/subscriptions":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") if length else "{}")
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid JSON payload"})
            return

        email = str(payload.get("email") or "").strip()
        modules = payload.get("modules") or []
        if not isinstance(modules, list):
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Modules must be a list"})
            return

        try:
            record = upsert_subscription(email=email, modules=modules, source="website")
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return

        supabase_status = {"mirrored": False}
        try:
            upsert_subscription_to_supabase(
                {
                    "email": record["email"],
                    "status": record["status"],
                    "section_ids": record["section_ids"],
                    "section_labels": record["section_labels"],
                    "source": record["source"],
                },
                use_service_role=True,
            )
            supabase_status = {"mirrored": True}
        except Exception as exc:
            supabase_status = {"mirrored": False, "warning": str(exc)}

        self._write_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "subscription": record,
                "registryPath": str(DEFAULT_REGISTRY_PATH),
                "supabase": supabase_status,
            },
        )

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the NextToken website and subscription API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NextTokenSiteHandler)
    print(f"Serving NextToken website at http://{args.host}:{args.port}")
    print(f"Subscription registry: {DEFAULT_REGISTRY_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
