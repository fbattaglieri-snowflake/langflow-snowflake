# Backup and recovery

A flow JSON export is not a complete backup. You need the persistent application
database, files, configuration, knowledge bases, the matching encryption key,
administrator credentials, catalogs and pinned image versions. Vector databases
need their own consistent backup/PITR policy. Never commit any of these backups.

1. Drain runs and suspend/quiesce the application for a consistent block snapshot.
2. Create a Snowflake snapshot using the current documented SPCS snapshot API and your explicit service/volume names.
3. Store keys separately in an approved encrypted secret backup, with tested access recovery.
4. Restore into an isolated service/volume, not over the live service. Use the matching image and key.
5. Verify login, actual decryption, database integrity, flow/file/KB contents and synthetic execution.
6. Validate vector restore separately; check values and retrieval, not just row counts.

`snapshotOnDelete` with seven-day retention is a safety net, not a backup
schedule. Block state survives ordinary suspend/resume but is tied to service
lifecycle. Do not drop the service. A rollback after an upstream migration may
require restoring both the database and image. This kit has not certified full
disaster recovery or in-flight execution recovery.