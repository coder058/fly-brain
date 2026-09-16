# Fly Lab A2A research hub

Small stdlib-only local coordinator using A2A 1.0 HTTP+JSON task/message shapes. It exposes an Agent Card, queued `message:send`, task lookup/list/cancel, and a separate localhost worker API for claim/complete/fail/lease recovery. It persists task state, attempt counts and ordered events in SQLite. It never executes worker-provided shell commands.

The request must set `configuration.returnImmediately: true`, because this prototype queues work for an external worker and does not block for model completion. Streaming, push notifications, binary artifacts, authentication and multi-tenant access are not implemented. The worker API is a Fly Lab local extension, not an A2A standard operation.

Start it on the VPS with a persistent user-owned DB path:

```sh
.venv/bin/python -m flylab.a2a_hub --database /home/ubuntu/fly-lab/state/a2a.sqlite --port 8765
```

The server binds only to `127.0.0.1`. Reach it through an SSH port forward; do not bind it publicly. Discovery is `GET /.well-known/agent-card.json`; A2A REST endpoints are `POST /message:send`, `GET /tasks/{id}`, `GET /tasks`, and `POST /tasks/{id}:cancel`.

For an agent adapter, poll `POST /local/workers/claim` with `workerId` and `leaseSeconds`; complete with `POST /local/tasks/{id}:complete` and text artifacts, or report failure with `POST /local/tasks/{id}:fail`. Expired worker leases return to `submitted` and emit an event. `POST /local/tasks/recover` runs recovery eagerly; task history is at `GET /local/tasks/{id}/events`.

Budgets are stored in task metadata and returned to workers. This prototype records reported budget usage but does **not** enforce model-token or CPU budgets; an adapter must enforce those limits. Cursor/Codex service integration is not included: no local Cursor or Codex worker executable was found on the VPS. Unit tests simulate sequential workers and an expired lease; they do not claim an external-agent integration.

The protocol surface follows the official [A2A v1.0.0 specification](https://a2a-protocol.org/v1.0.0/specification/), specifically its HTTP+JSON endpoints, Agent Card discovery, asynchronous tasks and task-state lifecycle. This implementation is a deliberately limited subset, not a conformance-certified server.
