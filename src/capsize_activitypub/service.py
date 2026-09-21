from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .client import ActivityPubClient, ActivityPubError
from .config import configured_identity
from .store import ConnectionStore


def _state_path() -> Path:
    return Path(os.environ.get("CAPSIZE_ACTIVITYPUB_STATE", "~/.local/share/capsize/activitypub.sqlite3")).expanduser()


class Handler(BaseHTTPRequestHandler):
    server_version = "CapsizeActivityPub/0.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def send_json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            self.send_json({"status": "ok", "protocol": "activitypub", "version": "0.1.0"})
            return
        if parsed.path == "/api/activitypub/identity":
            self.send_json({"identity": configured_identity().as_dict()})
            return
        if parsed.path == "/api/activitypub/connections":
            state_path = _state_path()
            state_path.parent.mkdir(parents=True, exist_ok=True)
            self.send_json({"actors": ConnectionStore(state_path).list_actors()})
            return
        try:
            with ActivityPubClient(resolve_dns=os.environ.get("CAPSIZE_ACTIVITYPUB_RESOLVE_DNS") == "1") as client:
                if parsed.path == "/api/activitypub/discover":
                    actor = client.discover(query.get("acct", [""])[0])
                    state_path = _state_path()
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    ConnectionStore(state_path).save_actor(actor.as_dict(), time.time())
                    self.send_json({"actor": actor.as_dict()})
                    return
                if parsed.path == "/api/activitypub/timeline":
                    actor_url = query.get("actor", [""])[0]
                    actor = client.actor(actor_url)
                    self.send_json({"actor": actor.as_dict(), "items": client.public_timeline(actor, limit=25)})
                    return
        except ActivityPubError as exc:
            self.send_json({"error": str(exc)}, 502)
            return
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        self.send_json({"error": "Not found"}, 404)


def main() -> None:
    host = os.environ.get("CAPSIZE_ACTIVITYPUB_HOST", "127.0.0.1")
    port = int(os.environ.get("CAPSIZE_ACTIVITYPUB_PORT", "8790"))
    state_path = _state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Capsize ActivityPub bridge listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
