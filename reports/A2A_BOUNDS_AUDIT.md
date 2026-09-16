# A2A bounded-request audit

The local A2A prototype keeps its existing loopback-only surface and does not
execute worker-provided shell commands. This audit adds regression coverage
for two limits already present in the implementation: the declared request
body cap and the maximum task-list page size.

During the first regression run, an oversized body was rejected with HTTP
400, but `HubError` was being caught by the broader `ValueError` handler and
reported as invalid JSON. The handler now preserves `HubError`, so the
response identifies the request-size cap while retaining the same rejection.

Measured verification on Ubuntu-1: A2A tests `6 passed`; full suite `74
passed`. No external worker, public binding, research experiment, or
scientific claim is involved.
