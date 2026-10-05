# Operations

## Upgrade

Drain active runs; back up data and keys; record image digests and service specs.
Build/scan immutable images from a reviewed commit. Invoke deployment with
`--apply` but without `--allow-create`. It refuses an absent service or changed
block volume. Never DROP/CREATE to fix startup. Upstream DB migrations can make
image-only rollback invalid; restore a compatible database and key together.

The catalog is staged before proxy deployment. For updates, drain requests
before changing it: stage contents are shared with the running service. The
proxy loads the catalog on startup, not per request. Do not publish failed images.

## Suspend and resume

Use explicit fully qualified names with an approved operator connection.
Drain and suspend the application first, then its dedicated proxy. Suspend a
compute pool only if it is dedicated and no other services/jobs use it. Never
suspend a shared Ollama or Postgres dependency as part of this kit's lifecycle.
On resume, make dependencies ready, then proxy, then application. Verify login,
stored flows and a synthetic model call, not only READY.

Running public services keep compute resources allocated; pool autosuspend is
not HTTP-idle application autosuspend. Storage/snapshots/Postgres can still cost
money while compute is suspended.

## Long runs

Long Playground streaming is a known limitation of the tested upstream/ingress
path, not fixed by this kit. Prior testing observed disconnects around 90 seconds
even with periodic progress. This is not a universal hard limit certification.
[SPCS ingress documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/service-network-communications)
describes a 90-second inactivity timeout and recommends polling or WebSockets.

Use Langflow v2 background submission and job polling for long runs, with a
unique idempotency key and the same job ID for all polls. Persist that ID before
waiting. A timeout does not prove failure and must not trigger replay of a flow
with writes. Check the deployed version's OpenAPI for exact payloads. Background
execution surviving a disconnected client does not prove restart durability.
This repository does not modify the Playground frontend or provide a scheduler.