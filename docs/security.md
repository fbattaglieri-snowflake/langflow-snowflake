# Security boundaries

- Treat the editor as a code execution environment for trusted authors only.
- Snowflake ingress authentication and Langflow authentication are separate.
- Auto-login and automatic activation of new users are disabled at startup.
- Use a dedicated runtime role, reviewed inherited grants and explicit consumers.
- The proxy has a private endpoint; never change it to public without adding and reviewing application authentication.
- Preserve SSRF protections; the application allows only the discovered proxy host.
- Do not attach unrestricted EAIs. Additional providers require separately reviewed egress and credentials.
- Runtime OAuth tokens are read fresh and not persisted in catalogs or images.
- Secrets in application environments are visible to trusted container code.
- DO_NOT_TRACK is set, but complete telemetry suppression is **not certified**. Egress restrictions and traffic/log verification remain necessary.
- Cortex may use cross-region inference according to account policy; do not infer residency from the SPCS pool region.

Repository CI checks secrets and full container vulnerability inventories. No
upstream tree is excluded and unfixed vulnerabilities are not hidden. A failed
scanner is a failed gate, not a clean result. No workflow publishes or deploys
on an ordinary push. Keep dependency updates reviewed and build contexts narrow.

Use security advisories or an appropriate private reporting channel for sensitive
findings. Never attach tokens, DSNs, flow exports, databases or backup keys to
public issues. See [SECURITY.md](../SECURITY.md).