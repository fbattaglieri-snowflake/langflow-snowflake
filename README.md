# Langflow on Snowflake

An independent deployment kit for Langflow on Snowpark Container Services (SPCS),
with persistent block storage and a private Cortex Chat Completions adapter.

> **UNOFFICIAL PROJECT.** This is not an official Snowflake or Langflow product,
> integration, reference architecture, certification or support offering. Neither
> Snowflake Inc. nor the Langflow project or its owners/maintainers endorse or
> support this repository by virtue of being named here. No affiliation,
> sponsorship or approval is implied. Provided **AS IS**, at your own risk.
> Read [DISCLAIMER.md](DISCLAIMER.md), [SECURITY.md](SECURITY.md) and
> [NOTICE](NOTICE) before deploying.

**Status: initial deployment kit, not production certified.** Local build/tests
are distinct from deployment acceptance. Check [validation](docs/validation.md)
and the current CI results. A successful build is not a clean vulnerability scan.
**Deployment is currently blocked by upstream Langflow HIGH/CRITICAL findings.**
The repository can be reviewed and tested locally; do not bypass the image gate.

## Architecture

```text
Browser -- Snowflake authenticated ingress --> Langflow (one instance)
                                               |
                                               +-- /persist block volume
                                               |   SQLite, files, config, KBs
                                               |
                                               +-- private chat adapter
                                               |     +-- Cortex (SPCS OAuth)
                                               |     +-- optional SPCS Ollama
                                               |
                                               +-- optional pgVector (TLS + EAI)
```

The default deployment needs no n8n/Hermes installation, private base image,
external LLM API key or process running on a laptop. PostgreSQL is optional for
vector memory, **not** the application database. Model access, geographic
availability and Cortex cross-region policy remain account-specific decisions.

## Prerequisites

- Account/region supporting SPCS, block volumes and the selected CPU instance family.
- Administrator able to review bootstrap grants; a dedicated runtime role and deploy user.
- Snowflake CLI, Docker with Linux amd64 support, Python 3.11+, and Trivy.
- Permission to build/pull the pinned public images and push to your own Snowflake registry.
- Persistent encryption/login Snowflake Secrets provisioned through an approved secret-management process.
- At least one Cortex model verified on the **Chat Completions** endpoint for your account, or a configured SPCS Ollama endpoint.

The editor is for **trusted authors**: custom Python can use the container's
service identity. SQLite means one instance only. This is not the upstream
`prod` profile and does not provide multi-tenant isolation or HA.

## Quickstart

Run from a fresh clone. Nothing below selects an existing workstation connection
automatically. Review generated SQL before executing it.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp infrastructure/config.example.json config.local.json
```

1. Fill `config.local.json` with **your** names/account. See [configuration](docs/configuration.md).
2. Create the deploy principal first. For GitHub use the reviewed [OIDC template](infrastructure/sql/00_oidc_trust.sql); for local use an existing approved user. No password belongs in Git.
3. Generate bootstrap SQL, review it, then run it using an explicit administrator connection:

```sh
mkdir -p build
python scripts/deploy.py bootstrap --config config.local.json > build/bootstrap.sql
snow sql --connection YOUR_ADMIN_CONNECTION --filename build/bootstrap.sql
```

4. Provision stable encryption and application login secrets; apply the reviewed [secret grants](infrastructure/sql/10_secret_grants.sql). Keep recoverable backups of the secrets separately from data backups. Never use sample passwords.
5. Set temporary CLI authentication in the environment and the matching account/user/role. For local SSO, `SNOWFLAKE_AUTHENTICATOR=externalbrowser`; for CI use OIDC as documented. The scripts pass `-x` and override account/user/role from your config. Clear unrelated `SNOWFLAKE_*` authentication variables first.
6. Set `image_tag` to the full, reviewed Git commit SHA. Authenticate Docker to your registry with `snow spcs image-registry login -x`. Build and publish:

```sh
python scripts/build_images.py --config config.local.json --publish
```

Both images are fully scanned for HIGH/CRITICAL vulnerabilities **before either
is pushed**. A failed scan stops publication; do not bypass it. See CI for SBOMs.

7. Prepare `build/models.json` using [proxy/models.example.json](proxy/models.example.json). Replace the placeholder with a verified model; select capabilities explicitly. Do not copy a model catalog from an unrelated account.
8. Deploy only after the prerequisites and scans pass:

```sh
python scripts/deploy.py deploy --config config.local.json \
  --catalog build/models.json --apply --allow-create
```

The script discovers the proxy DNS and application endpoint. Sign in to Snowflake
ingress, then to Langflow with the separately provisioned application login.
In **OpenAI Compatible**, save the printed private base URL and a non-secret
placeholder API key (`internal`). Disable streaming. Enable only verified chat
models; do not advertise these entries as embedding models.

For upgrades, take a consistent backup and omit `--allow-create`. Existing
services are altered, not dropped. The script rejects a changed block volume size.
Provision consumer access using the template after the service exists.

## GitHub Actions

[CI](.github/workflows/ci.yml) runs without Snowflake credentials. Manual
[deployment](.github/workflows/deploy.yml) uses the protected `production`
environment and OIDC, runs validation/build/scans again, and deploys that commit.
Configure `DEPLOY_CONFIG_JSON` and `MODEL_CATALOG_JSON` as **environment variables**
containing non-secret JSON. Do not include secret values. See [CI/CD](docs/ci-cd.md).

## Documentation

- [Configuration](docs/configuration.md)
- [Architecture and model compatibility](docs/architecture.md)
- [Security boundaries](docs/security.md)
- [Operations and long runs](docs/operations.md)
- [Backup and recovery](docs/backup-recovery.md)
- [MCP and A2A](docs/mcp-a2a.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Validation status](docs/validation.md)

Repository-authored code is Apache-2.0; upstream components retain their own
licenses. No live demo exports, credentials or account identifiers are distributed.