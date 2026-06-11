# AWS Database Migration and Recovery Runbook

## Targets

- Production RPO: 24 hours
- Production RTO: 4 hours
- Pre-production RPO/RTO: best effort

## Migration

1. Create and encrypt an RDS snapshot.
2. Enable application maintenance mode and stop workers.
3. Dump the source database with transaction-consistent options.
4. Restore into RDS using a least-privilege migration user.
5. Compare table counts, Django migration state and representative aggregates.
6. Run `python manage.py migrate --check` against RDS.
7. Start one application task and verify `/health/ready`, login, CRUD and uploads.
8. Switch ECS desired count, resume workers and retain the source database read-only.

PostgreSQL:

```bash
pg_dump --format=custom --no-owner --no-acl "$SOURCE_DATABASE_URL" > tableno.dump
pg_restore --clean --if-exists --no-owner --dbname "$TARGET_DATABASE_URL" tableno.dump
```

MySQL:

```bash
mysqldump --single-transaction --routines --triggers --set-gtid-purged=OFF tableno > tableno.sql
mysql --host "$DB_HOST" --user "$DB_USER" --password tableno < tableno.sql
```

## Backup and restore drill

- Keep automated RDS backups for 14 days in production.
- Run a quarterly point-in-time restore into an isolated subnet.
- Verify migrations, row counts, login and one complete session workflow.
- Record elapsed restore time and compare it with the RTO.

## Rollback

Stop new tasks, restore the previous database endpoint and task definition, then verify readiness before reopening traffic.
