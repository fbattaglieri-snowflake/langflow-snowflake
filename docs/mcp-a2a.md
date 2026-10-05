# Optional MCP and A2A

Both are Langflow capabilities hosted by SPCS, not additional Snowflake products.
A2A is disabled by default in this kit. Enable it only after reviewing which
flows/tools become callable and their write capabilities. Do not assume turning
on the feature publishes or qualifies every flow.

External clients must satisfy Snowflake ingress authentication **and** Langflow
API authentication. Keep API keys and Snowflake credentials in the client's
secret store, not URLs, exported connection JSON or repository files. Private
SPCS clients use service DNS and appropriate service-role access. Never expose
an unauthenticated local forwarding proxy on a public interface.

Configure against the installed release's API/schema. The desktop bridge and
private client settings from the original pilot are deliberately not included.
No end-to-end MCP/A2A client certification is claimed for this public kit.