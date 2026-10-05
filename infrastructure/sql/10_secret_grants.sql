-- TEMPLATE ONLY: provision secrets through your organization's approved process.
-- Encryption secret: GENERIC_STRING, stable random value; never rotate on deploy.
-- Login secret: PASSWORD, dedicated application administrator username/password.
-- Optional vector DSN secret: GENERIC_STRING, TLS connection string.
USE ROLE SECURITYADMIN;
GRANT READ ON SECRET <DATABASE>.<SCHEMA>.<ENCRYPTION_SECRET> TO ROLE <RUNTIME_ROLE>;
GRANT READ ON SECRET <DATABASE>.<SCHEMA>.<LOGIN_SECRET> TO ROLE <RUNTIME_ROLE>;
-- If pgVector is enabled, also grant READ on its secret and USAGE on its EAI.
-- Access for UI consumers is separate from the privileged authoring role:
GRANT USAGE ON DATABASE <DATABASE> TO ROLE <CONSUMER_ROLE>;
GRANT USAGE ON SCHEMA <DATABASE>.<SCHEMA> TO ROLE <CONSUMER_ROLE>;
GRANT SERVICE ROLE <DATABASE>.<SCHEMA>.<SERVICE>!ALL_ENDPOINTS_USAGE TO ROLE <CONSUMER_ROLE>;