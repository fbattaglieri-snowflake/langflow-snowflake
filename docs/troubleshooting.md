# Troubleshooting

| Symptom | Check |
|---|---|
| Proxy fails startup | Placeholder/empty catalog, invalid backend or missing SNOWFLAKE_HOST |
| Model appears but call fails | Exact endpoint, access grants, regional availability and catalog capability flags |
| Tools rejected | Tools default to disabled; qualify before enabling; no model fallback |
| Streaming rejected | Public adapter deliberately supports non-streaming Chat Completions only |
| Langflow login fails | Two authentication layers; mounted login secret; auto-login disabled |
| SQLite write errors | /persist is a block mount, ownership transition succeeded, one instance only |
| pgVector absent/fails | pgvector extra, DSN secret, TLS, exact-host EAI and database ingress policy |
| Upgrade refused | Volume mismatch or missing service; do not bypass by dropping state |
| Long run disconnects | Poll the existing background job; never blindly repeat writes |
| CI scan fails | Review actual inventory/advisories; update dependencies, not scanner exclusions |
| CLI fails | Explicit account/user/role/auth; no default local connection is selected |

Keep diagnostics private and redact prompts/credentials. Adapter errors do not
echo upstream bodies; inspect the upstream service securely rather than adding
public debug dumps. SQL templates with placeholders are not executable until
configured. Regional availability is not guaranteed by successful offline tests.