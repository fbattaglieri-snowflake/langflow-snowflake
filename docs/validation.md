# Validation status

Initial validation is local only. No resources, grants, secrets or flows have
been provisioned in a live Snowflake account for this public kit.

- Linux amd64 application and standalone proxy images build from public bases.
- Final Alpine proxy container passes offline HTTP health and catalog checks.
- Initial 32 unit/HTTP/repository tests pass: synthetic account configuration, SQL input
  guards, volume-change rejection, non-destructive update, actual local HTTP
  routing, OAuth reread, Ollama credential isolation and upstream-error redaction.
- Gitleaks staged scan found no leaks in the initial source snapshot. Final
  publication must repeat this scan and scan the complete new commit history.
- A separate search found no tested private account/endpoint/flow identifiers.
  This complements rather than replaces secret scanning.
- Offline application smoke passed on two consecutive containers sharing a
  disposable volume: real administrator login, SQLite integrity=ok, 46 tables,
  and a persistent file marker. Network was disabled and no host credentials
  were mounted. This is not full SPCS recovery or real flow execution acceptance.
- No complete live deployment, OIDC trust, pgVector, real model/tool roundtrip,
  Playground patch or end-to-end MCP/A2A qualification is claimed.

## Security release blocker

The complete 2026-10-05 scan of the initial Langflow 1.12.2 image found **20 HIGH
and 3 CRITICAL findings**. Packages included PyJWT, chromadb, msgpack, pypdf,
urllib3, setuptools and JavaScript dependencies. Some findings had no fixed
version listed. Counts are package findings, not unique CVEs or exploitability
conclusions. The current upstream release requires a separately tested upgrade;
the kit does not force-install incompatible transitive versions or hide findings.

**Do not deploy this baseline until the complete scan gate passes.** Repository
publication for review is not deployment approval. CI and build/publish scripts
keep the gate blocking, including unfixed vulnerabilities. Any future clean
result must name the exact new image and scanner evidence; it does not erase
the failed baseline.

The first Debian-based proxy candidate also failed its complete scan (58 HIGH,
5 CRITICAL). The final pinned Alpine-based proxy has **0 HIGH/CRITICAL** findings
in the complete scan. This is a real base-image change, not a scanner exclusion.

The upstream 1.12.4 image was separately scanned at digest
`sha256:4304bd9e67db00e72ab20d7a853abbc46d107901215b50a8298f4c4f45127eae`:
19 HIGH and 3 CRITICAL findings remain, including findings with no fixed version.
It was not substituted as a supposedly clean upgrade. Langflow deployment stays
blocked; the tested 1.12.2 baseline is retained transparently for review.