# GitHub Actions and OIDC

CI on push/PR performs offline checks, image builds, complete scans and SBOM
generation. It receives no Snowflake identity. It never deploys. There are no
scheduled jobs. Actions are SHA-pinned; dependency updates require review.

Deployment is workflow_dispatch only, main only, through the `production`
environment. Configure required reviewers and restrict deployment branches to
main **before use**. Do not rely on merely naming an environment as a review gate.
Set non-secret environment variables DEPLOY_CONFIG_JSON (the configuration
schema) and MODEL_CATALOG_JSON (verified catalog). The workflow replaces image_tag
with its exact commit SHA and validates every value before exporting CLI variables.

Create the OIDC service user from the template after administrator review. The
subject must exactly match `repo:OWNER/REPOSITORY:environment:production`, including
case. The role in the configuration must be granted to that user. There is no
long-lived Snowflake password, PAT or private key in GitHub. Runtime application
secrets remain in Snowflake, not GitHub variables.

Bootstrap is deliberately generated/reviewed by an administrator rather than
automatically creating privileged principals from a workflow. Account network or
authentication policies are not modified by this kit. If hosted runners are
blocked, ask the administrator to evaluate the managed network rule
`SNOWFLAKE.NETWORK_SECURITY.GITHUBACTIONS_GLOBAL` in a scoped policy; do not replace
an account policy or copy transient runner CIDRs.

Deployment re-runs tests and complete HIGH/CRITICAL image scans immediately before
push. A failed gate stops deployment, including unfixed upstream vulnerabilities.
No `continue-on-error`, directory exclusion or vulnerability ignore list is used.

Repository protections are operator-configured, not automatically guaranteed:
require PR review and successful validation/image checks on main; enable secret
scanning/push protection and private vulnerability reporting where available.
Forks must update CODEOWNERS. GitHub feature availability varies by plan.