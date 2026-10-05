# Configuration

Copy `infrastructure/config.example.json` to ignored `config.local.json`. Do not
commit the populated file. All keys are required so accidental defaults cannot
silently select a different account. Unquoted SQL names must be uppercase.

| Keys | Purpose |
|---|---|
| account, user, role | Temporary CLI connection; dedicated runtime/deployment role |
| database, schema | Destination object namespace |
| warehouse | Small warehouse for operator queries; not the app compute pool |
| compute_pool, instance_family | Dedicated single-node CPU pool; verify regional availability |
| image_repository, stage | Images and model catalog; no secret values |
| service, proxy_service | Distinct names; derived DNS is discovered after creation |
| encryption_secret, login_secret | Existing secret object names in the configured schema |
| volume_size_gib | Initial block size; cannot be resized through this kit |
| app/proxy_cpu_request/limit | CPU allocation; positive request no greater than limit |
| app/proxy_memory_request/limit_gib | Memory allocation in GiB; positive request no greater than limit |
| image_tag | Reviewed Git commit SHA for publishing; no latest tag |
| pgvector_secret | Empty to disable; otherwise secret name containing a TLS DSN |
| external_access_integrations | Explicit existing EAIs granted to the runtime role |
| ollama_url | Empty to disable; private SPCS HTTP base URL without /v1 |
| a2a_enabled | False by default; enabling does not publish all flows automatically |

The default application resources are 1 CPU/4 GiB requested, 1.5 CPU/6 GiB
limited. Proxy requests 0.5 CPU/512 MiB. Review sizing before changing these
configuration values; this baseline is not load-tested. Pool selection must accommodate
both containers. A public service is not an HTTP-idle autosuspend application.

## Secrets

Use your approved secret provisioning process, not tracked SQL literals:

- Encryption: GENERIC_STRING with a cryptographically random persistent value.
- Login: PASSWORD secret with a unique application administrator identity.
- Optional pgVector: GENERIC_STRING DSN with encoded password and verified TLS,
  preferably `sslmode=verify-full` and the appropriate trust roots.

Do not print secret values or include them in command history, CI variables,
templates, issue reports, image layers or flow exports. The runtime receives
application secrets as environment variables through SPCS; trusted code in that
container can read them. This is not isolation from application authors.

## Optional pgVector

Provision the database/user/extension separately using supported PostgreSQL
procedures for your environment. Snowflake Postgres availability varies by
region. Configure its ingress policy from current authorized egress ranges;
do not use copied CIDRs or 0.0.0.0/0. Add an EAI limited to its exact host:port,
grant USAGE to the runtime role, and READ on the DSN secret. Review and rotate
expiring network ranges. Existing EAIs are not removed implicitly by upgrades.

## Optional Ollama

Supply a deployed SPCS endpoint and models already installed by its operator.
The runtime role needs service endpoint access when the owner differs. No
GPU, model download, foreign service edit or license acceptance is automated.
Model IDs must be explicitly listed in the catalog with backend `ollama`.

## Configuration validation

`python scripts/deploy.py render --config config.local.json --proxy-dns
proxy.synthetic.svc.spcs.internal` generates reviewable JSON service specs
(JSON is YAML-compatible). The synthetic DNS is for offline review only.
Real deployment discovers its own DNS. No default workstation connection or
Snowflake account is inferred.