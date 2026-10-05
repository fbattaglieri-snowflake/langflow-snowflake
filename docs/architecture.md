# Architecture and model contract

The kit builds the public Langflow image with a persistent entrypoint and the
pgvector Python extra. It does not patch the Langflow application or bundle the
upstream source. The entrypoint owns only /persist before dropping root to UID
1000. SQLite, configuration and knowledge bases live on that block volume.

A separate private adapter exposes `/health`, `/v1/models` and non-streaming
`/v1/chat/completions`. **It is intentionally narrower than a general LLM gateway.**
It has no SQL, Responses, Messages, embedding, arbitrary URL, retry or model
fallback route. Invalid catalogs fail startup. The catalog example deliberately
cannot run until the operator replaces the placeholder.

For Cortex the adapter reads `/snowflake/session/token` each request and uses
the Snowflake-provided `SNOWFLAKE_HOST`. It can explicitly rename max_tokens and
normalize missing finish_reason fields per catalog entry. Normalization infers
stop/tool_calls/length and cannot reconstruct every upstream refusal/filter
condition; enable only after endpoint-specific tests.

Ollama requests are passed without Cortex payload rewrites or Snowflake tokens.
Only a configured private SPCS endpoint is allowed. No external provider route
is enabled. Never forward the Snowflake token to an arbitrary host.

Tools are disabled unless the catalog explicitly enables them. Parallel tool
history is preserved, not collapsed. A model that requires Messages or Responses
is not made compatible by changing its name in the catalog. Qualify text,
single/multiple tool roundtrips, error handling and limits on the exact endpoint
before enabling a model. Listed does not mean verified. Select only chat entries
in Langflow and disable streaming; embedding needs a separately qualified path.

SPCS supplies the service owner's identity, **not caller's rights**. UI users
share a trust boundary. The baseline role can deploy its own services and write
its image repository/stage; it is not a hardened separation-of-duties design.
Split deployer/runtime permissions for production and review inherited PUBLIC
privileges. No grants to user business tables are included.