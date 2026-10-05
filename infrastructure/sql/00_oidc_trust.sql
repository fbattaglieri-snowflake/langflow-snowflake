-- TEMPLATE ONLY. Replace both placeholders and review before executing.
-- This creates a real principal; run only with explicit administrator approval.
USE ROLE USERADMIN;
CREATE USER <DEPLOY_USER>
  TYPE = SERVICE
  DEFAULT_ROLE = PUBLIC
  WORKLOAD_IDENTITY = (
    TYPE = OIDC
    ISSUER = 'https://token.actions.githubusercontent.com'
    SUBJECT = 'repo:<GITHUB_OWNER>/<GITHUB_REPOSITORY>:environment:production'
  );
-- Bootstrap grants the configured runtime/deployment role to this user.
-- Restrict the production GitHub environment to main and required reviewers.