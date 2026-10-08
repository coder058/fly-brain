"""Local, durable A2A 1.0 HTTP+JSON research-task hub (stdlib only).

This prototype queues work; it never executes agent-supplied shell commands.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

A2A_VERSION = "1.0.0"
TERMINAL = {"TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED",
            "TASK_STATE_REJECTED"}
# GUESS: local prototype request cap; adjust only after measuring real artifact payloads.
MAX_BODY_BYTES = 1_048_576
DRAIN_LIMIT_BYTES = 4 * MAX_BODY_BYTES
# GUESS: local single-user lock-wait budget; server is loopback-only.
DB_TIMEOUT_SECONDS = 15.0
# GUESS: prototype pagination defaults/cap; tune from observed task volume.
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def agent_message(text: str) -> dict:
    return {"role": "ROLE_AGENT", "parts": [{"text": text}], "messageId": str(uuid.uuid4())}


class HubError(ValueError):
    pass


class HubStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, context_id TEXT NOT NULL,
                    message_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    assigned_to TEXT, lease_until REAL, attempts INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS tasks_queue ON tasks(state, created_at);
                CREATE INDEX IF NOT EXISTS tasks_lease ON tasks(state, lease_until);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL, created_at TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
            """)
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT_SECONDS)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _task(row) -> dict:
        return json.loads(row["payload"])

    @staticmethod
    def _put_event(db, task_id: str, event: dict) -> None:
        db.execute("INSERT INTO events(task_id,created_at,event_json) VALUES(?,?,?)",
                   (task_id, utc_now(), json.dumps(event, separators=(",", ":"))))

    def create_task(self, message: dict, metadata: dict | None = None) -> dict:
        if not isinstance(message, dict) or message.get("role") != "ROLE_USER":
            raise HubError("message.role must be ROLE_USER")
        parts = message.get("parts")
        if not isinstance(parts, list) or not parts or any(
            not isinstance(p, dict) or not isinstance(p.get("text"), str) for p in parts
        ):
            raise HubError("this hub accepts non-empty text-only message parts")
        now = utc_now()
        msg_id = str(message.get("messageId") or uuid.uuid4())
        task_id = str(uuid.uuid4())
        context_id = str(message.get("contextId") or uuid.uuid4())
        user_message = {**message, "messageId": msg_id, "contextId": context_id,
                        "taskId": task_id, "role": "ROLE_USER"}
        task = {
            "id": task_id,
            "contextId": context_id,
            "status": {"state": "TASK_STATE_SUBMITTED", "timestamp": now,
                       "message": agent_message("Queued for a registered research worker.")},
            "artifacts": [],
            "history": [user_message],
            "metadata": {**(metadata or {}), "hub": {
                "assignedTo": None, "attempt": 0, "leaseUntil": None,
            }},
        }
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM tasks WHERE message_id=?", (msg_id,)).fetchone()
            if existing:
                return self._task(existing)
            db.execute("""INSERT INTO tasks
                (id,context_id,message_id,state,created_at,updated_at,assigned_to,lease_until,attempts,payload)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (task_id, context_id, msg_id, "TASK_STATE_SUBMITTED", now, now,
                 None, None, 0, json.dumps(task)))
            self._put_event(db, task_id, {"type": "created", "state": "TASK_STATE_SUBMITTED",
                                          "messageId": msg_id})
        return task

    def get_task(self, task_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise HubError("task not found")
        return self._task(row)

    def list_tasks(self, state: str | None = None, context_id: str | None = None,
                   limit: int = 100) -> list[dict]:
        if limit < 1 or limit > MAX_PAGE_SIZE:
            raise HubError(f"pageSize must be between 1 and {MAX_PAGE_SIZE}")
        query, params = "SELECT * FROM tasks", []
        filters = []
        if state:
            filters.append("state=?"); params.append(state)
        if context_id:
            filters.append("context_id=?"); params.append(context_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at,id LIMIT ?"; params.append(limit)
        with self._connect() as db:
            return [self._task(row) for row in db.execute(query, params).fetchall()]

    def _recover_expired_tx(self, db, now: float) -> list[str]:
        rows = db.execute("SELECT * FROM tasks WHERE state='TASK_STATE_WORKING' AND lease_until<=?",
                          (now,)).fetchall()
        recovered = []
        for row in rows:
            task = self._task(row)
            task["status"] = {"state": "TASK_STATE_SUBMITTED", "timestamp": utc_now(),
                              "message": agent_message("Worker lease expired; returned to queue for recovery.")}
            task["metadata"].setdefault("hub", {}).update(
                {"assignedTo": None, "leaseUntil": None, "lastFailure": "lease_expired"}
            )
            db.execute("""UPDATE tasks SET state=?,updated_at=?,assigned_to=NULL,lease_until=NULL,
                payload=? WHERE id=?""",
                ("TASK_STATE_SUBMITTED", utc_now(), json.dumps(task), row["id"]))
            self._put_event(db, row["id"], {"type": "lease_expired", "requeued": True,
                                            "previousWorker": row["assigned_to"]})
            recovered.append(row["id"])
        return recovered

    def recover_expired(self, now: float | None = None) -> list[str]:
        import time
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._recover_expired_tx(db, time.time() if now is None else now)

    def claim_next(self, worker_id: str, lease_seconds: int) -> dict | None:
        import time
        worker_id = str(worker_id).strip()
        if not worker_id or int(lease_seconds) <= 0:
            raise HubError("workerId and a positive leaseSeconds are required")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover_expired_tx(db, now)
            row = db.execute("SELECT * FROM tasks WHERE state='TASK_STATE_SUBMITTED' "
                             "ORDER BY created_at,id LIMIT 1").fetchone()
            if not row:
                return None
            task = self._task(row)
            lease_until = now + int(lease_seconds)
            attempt = int(row["attempts"]) + 1
            task["status"] = {"state": "TASK_STATE_WORKING", "timestamp": utc_now(),
                              "message": agent_message(f"Claimed by worker {worker_id}.")}
            task["metadata"].setdefault("hub", {}).update({
                "assignedTo": worker_id, "attempt": attempt, "leaseUntil": lease_until,
            })
            task["history"].append(task["status"]["message"])
            db.execute("""UPDATE tasks SET state=?,updated_at=?,assigned_to=?,lease_until=?,attempts=?,payload=?
                WHERE id=?""",
                ("TASK_STATE_WORKING", utc_now(), worker_id, lease_until, attempt,
                 json.dumps(task), row["id"]))
            self._put_event(db, row["id"], {"type": "claimed", "workerId": worker_id,
                                            "attempt": attempt, "leaseUntil": lease_until})
            return task

    def _owned_working_task(self, db, task_id: str, worker_id: str):
        row = db.execute("SELECT * FROM tasks WHERE id=? AND state='TASK_STATE_WORKING' "
                         "AND assigned_to=?", (task_id, worker_id)).fetchone()
        if not row:
            raise HubError("task is not working under this worker")
        return row, self._task(row)

    def complete(self, task_id: str, worker_id: str, artifacts: list, budget_used=None) -> dict:
        clean = []
        for item in artifacts:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) \
                    or not isinstance(item.get("text"), str):
                raise HubError("artifacts must contain text fields name and text")
            clean.append({"artifactId": str(uuid.uuid4()), "name": item["name"],
                          "parts": [{"text": item["text"]}]})
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row, task = self._owned_working_task(db, task_id, worker_id)
            now = utc_now()
            task["artifacts"] = clean
            task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now,
                              "message": agent_message("Worker completed the task and attached its artifacts.")}
            task["history"].append(task["status"]["message"])
            task["metadata"].setdefault("hub", {}).update({
                "assignedTo": None, "leaseUntil": None, "budgetUsed": budget_used,
            })
            db.execute("UPDATE tasks SET state=?,updated_at=?,assigned_to=NULL,lease_until=NULL,payload=? WHERE id=?",
                       ("TASK_STATE_COMPLETED", now, json.dumps(task), task_id))
            self._put_event(db, task_id, {"type": "completed", "workerId": worker_id,
                                          "artifactCount": len(clean), "budgetUsed": budget_used})
        return task

    def fail(self, task_id: str, worker_id: str, reason: str) -> dict:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row, task = self._owned_working_task(db, task_id, worker_id)
            now = utc_now()
            task["status"] = {"state": "TASK_STATE_FAILED", "timestamp": now,
                              "message": agent_message(str(reason))}
            task["history"].append(task["status"]["message"])
            task["metadata"].setdefault("hub", {}).update({"assignedTo": None, "leaseUntil": None})
            db.execute("UPDATE tasks SET state=?,updated_at=?,assigned_to=NULL,lease_until=NULL,payload=? WHERE id=?",
                       ("TASK_STATE_FAILED", now, json.dumps(task), task_id))
            self._put_event(db, task_id, {"type": "failed", "workerId": worker_id, "reason": str(reason)})
        return task

    def cancel(self, task_id: str) -> dict:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise HubError("task not found")
            task = self._task(row)
            if row["state"] in TERMINAL:
                raise HubError("task is already terminal")
            now = utc_now()
            task["status"] = {"state": "TASK_STATE_CANCELED", "timestamp": now,
                              "message": agent_message("Canceled by the requester.")}
            db.execute("UPDATE tasks SET state=?,updated_at=?,assigned_to=NULL,lease_until=NULL,payload=? WHERE id=?",
                       ("TASK_STATE_CANCELED", now, json.dumps(task), task_id))
            self._put_event(db, task_id, {"type": "canceled"})
        return task

    def events(self, task_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT created_at,event_json FROM events WHERE task_id=? ORDER BY seq",
                              (task_id,)).fetchall()
        if not rows:
            self.get_task(task_id)
        return [{"createdAt": row["created_at"], **json.loads(row["event_json"])} for row in rows]


def agent_card(base_url: str) -> dict:
    return {
        "protocolVersion": A2A_VERSION,
        "name": "Fly Lab Research Hub",
        "description": "Durable task queue for bounded, auditable Fly Lab research cycles.",
        "supportedInterfaces": [{"url": base_url, "protocolBinding": "HTTP+JSON",
                                 "protocolVersion": A2A_VERSION}],
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "research-cycle", "name": "Research cycle coordination",
                    "description": "Queue bounded research tasks, record artifacts, and recover expired worker leases.",
                    "tags": ["research", "reproducibility", "human-approval"],
                    "examples": ["Queue a low-cost EXP-MEM-001 pilot for review."],
                    "inputModes": ["text/plain"], "outputModes": ["text/plain"]}],
    }


class A2AHandler(BaseHTTPRequestHandler):
    server_version = "FlyLabA2A/0.1"

    def log_message(self, fmt, *args):
        print("A2A", self.address_string(), fmt % args)

    def send_json(self, payload: dict, status=HTTPStatus.OK):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/a2a+json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _discard_body(self, n: int) -> None:
        while n > 0:
            chunk = self.rfile.read(min(n, 65536))
            if not chunk:
                return
            n -= len(chunk)

    def read_json(self) -> dict:
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BODY_BYTES:
                if size > MAX_BODY_BYTES:
                    # Drain a bounded amount before replying: closing on an unread body makes
                    # the client hit EPIPE mid-upload instead of reading the 400.
                    self._discard_body(min(size, DRAIN_LIMIT_BYTES))
                    self.close_connection = True
                raise HubError("request body size is invalid or exceeds the local cap")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise HubError("request body must be a JSON object")
            return payload
        except HubError:
            raise
        except (ValueError, json.JSONDecodeError) as exc:
            raise HubError("request body is not valid JSON") from exc

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/.well-known/agent-card.json":
            return self.send_json(agent_card(self.server.base_url))
        if url.path == "/tasks":
            query = parse_qs(url.query)
            try:
                tasks = self.server.store.list_tasks(
                    state=query.get("status", [None])[0],
                    context_id=query.get("contextId", [None])[0],
                    limit=int(query.get("pageSize", [str(DEFAULT_PAGE_SIZE)])[0]),
                )
                return self.send_json({"tasks": tasks})
            except (HubError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        if url.path.startswith("/tasks/"):
            task_id = unquote(url.path[len("/tasks/"):])
            try:
                return self.send_json(self.server.store.get_task(task_id))
            except HubError as exc:
                return self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        if url.path.startswith("/local/tasks/") and url.path.endswith("/events"):
            task_id = unquote(url.path[len("/local/tasks/"):-len("/events")].strip("/"))
            try:
                return self.send_json({"events": self.server.store.events(task_id)})
            except HubError as exc:
                return self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        return self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/message:send":
                config = payload.get("configuration") or {}
                if config.get("returnImmediately") is not True:
                    raise HubError("set configuration.returnImmediately=true; this queue does not block for worker completion")
                if "message" not in payload:
                    raise HubError("message is required")
                return self.send_json({"task": self.server.store.create_task(
                    payload["message"], payload.get("metadata") or {})})
            if path == "/local/workers/claim":
                task = self.server.store.claim_next(payload.get("workerId", ""),
                                                    int(payload.get("leaseSeconds", 0)))
                return self.send_json({"task": task})
            if path == "/local/tasks/recover":
                return self.send_json({"recoveredTaskIds": self.server.store.recover_expired()})
            prefix = "/local/tasks/"
            if path.startswith(prefix) and path.endswith(":complete"):
                task_id = unquote(path[len(prefix):-len(":complete")])
                task = self.server.store.complete(task_id, payload.get("workerId", ""),
                                                  payload.get("artifacts", []),
                                                  payload.get("budgetUsed"))
                return self.send_json({"task": task})
            if path.startswith(prefix) and path.endswith(":fail"):
                task_id = unquote(path[len(prefix):-len(":fail")])
                task = self.server.store.fail(task_id, payload.get("workerId", ""),
                                              payload.get("reason", "worker reported failure"))
                return self.send_json({"task": task})
            if path.startswith("/tasks/") and path.endswith(":cancel"):
                task_id = unquote(path[len("/tasks/"):-len(":cancel")])
                return self.send_json(self.server.store.cancel(task_id))
            return self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except HubError as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": f"invalid request: {exc}"}, HTTPStatus.BAD_REQUEST)


def serve(db_path: str | Path, port: int) -> None:
    store = HubStore(db_path)
    server = ThreadingHTTPServer(("127.0.0.1", int(port)), A2AHandler)
    server.store = store
    server.base_url = f"http://127.0.0.1:{int(port)}"
    print(f"Fly Lab A2A listening on {server.base_url}; database={store.db_path}")
    print("Loopback only. Use SSH port forwarding; do not expose this prototype publicly.")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="SQLite file for durable tasks and events")
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args(argv)
    # SOURCE: TCP/UDP port field is an unsigned 16-bit value; zero is not a service port here.
    if not 1 <= args.port <= 65535:
        parser.error("port must be in 1..65535")
    serve(args.database, args.port)


if __name__ == "__main__":
    main()
