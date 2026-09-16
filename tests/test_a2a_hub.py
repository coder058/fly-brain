"""Durability, lease-recovery, and task-lifecycle tests for the local A2A hub."""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from flylab.a2a_hub import (
    A2AHandler,
    HubError,
    HubStore,
    MAX_BODY_BYTES,
    MAX_PAGE_SIZE,
    agent_card,
)


def _message():
    return {"role": "ROLE_USER", "messageId": "idempotency-key-1",
            "parts": [{"text": "Run the bounded memory pilot and report validity."}]}


def test_a2a_task_round_trip_and_idempotency(tmp_path):
    store = HubStore(tmp_path / "hub.sqlite")
    first = store.create_task(_message(), {"budget": {"cpuSeconds": 60}})
    retry = store.create_task(_message(), {"budget": {"cpuSeconds": 999}})
    assert retry["id"] == first["id"]
    assert first["status"]["state"] == "TASK_STATE_SUBMITTED"
    assert store.get_task(first["id"])["metadata"]["budget"]["cpuSeconds"] == 60


def test_task_listing_rejects_page_size_above_declared_cap(tmp_path):
    store = HubStore(tmp_path / "hub.sqlite")
    try:
        store.list_tasks(limit=MAX_PAGE_SIZE + 1)
    except HubError as exc:
        assert str(exc) == f"pageSize must be between 1 and {MAX_PAGE_SIZE}"
    else:
        raise AssertionError("page-size cap was not enforced")


def test_expired_worker_is_recorded_requeued_and_completed(tmp_path):
    store = HubStore(tmp_path / "hub.sqlite")
    task = store.create_task(_message())
    # GUESS: short lease used only to exercise recovery with a synthetic clock.
    claimed = store.claim_next("worker-a", lease_seconds=5)
    assert claimed["status"]["state"] == "TASK_STATE_WORKING"
    expired_at = claimed["metadata"]["hub"]["leaseUntil"] + 1
    assert store.recover_expired(now=expired_at) == [task["id"]]
    retry = store.claim_next("worker-b", lease_seconds=5)
    assert retry["metadata"]["hub"]["attempt"] == 2
    done = store.complete(task["id"], "worker-b", [{"name": "pilot", "text": "PASS: task plumbing only"}],
                          {"tokens": 0, "cpuSeconds": 1})
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert done["artifacts"][0]["parts"][0]["text"] == "PASS: task plumbing only"
    event_types = [event["type"] for event in store.events(task["id"])]
    assert event_types == ["created", "claimed", "lease_expired", "claimed", "completed"]


def test_agent_card_discloses_protocol_and_no_streaming():
    card = agent_card("http://127.0.0.1:8123")
    assert card["protocolVersion"] == "1.0.0"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "HTTP+JSON"
    assert card["capabilities"]["streaming"] is False


def test_loopback_http_agent_card_and_enqueue(tmp_path):
    # SOURCE: port 0 delegates ephemeral loopback port selection to the operating system.
    server = ThreadingHTTPServer(("127.0.0.1", 0), A2AHandler)
    server.store = HubStore(tmp_path / "http-hub.sqlite")
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(server.base_url + "/.well-known/agent-card.json") as response:
            card = json.load(response)
        assert card["protocolVersion"] == "1.0.0"

        payload = {"message": _message(), "configuration": {"returnImmediately": True}}
        request = Request(server.base_url + "/message:send",
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/a2a+json"}, method="POST")
        with urlopen(request) as response:
            task = json.load(response)["task"]
        assert task["status"]["state"] == "TASK_STATE_SUBMITTED"
        with urlopen(server.base_url + "/tasks/" + task["id"]) as response:
            assert json.load(response)["id"] == task["id"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def test_loopback_http_rejects_payload_over_declared_cap(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), A2AHandler)
    server.store = HubStore(tmp_path / "http-hub.sqlite")
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        payload = b"x" * (MAX_BODY_BYTES + 1)
        request = Request(server.base_url + "/message:send", data=payload,
                          headers={"Content-Type": "application/a2a+json"}, method="POST")
        try:
            urlopen(request)
        except HTTPError as exc:
            assert exc.code == 400
            assert "exceeds the local cap" in exc.read().decode()
        else:
            raise AssertionError("oversized payload was accepted")
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
