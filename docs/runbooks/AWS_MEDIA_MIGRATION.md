# AWS Media Migration Runbook

## Goal

Move existing `media/` objects to the environment S3 bucket without losing the local rollback source.

## Procedure

1. Freeze media writes or put the application in maintenance mode.
2. Back up the local `media/` directory and record file count and total bytes.
3. Run the planner:
   `python scripts/aws/sync_media.py --bucket <bucket>`
4. Review every planned key, then rerun with `--execute`.
5. Run the planner again. `planned_uploads=0` is required.
6. Start one `aws-pre` task with `USE_S3_STORAGE=True`.
7. Upload, read and delete a test image for characters, sessions, scenarios and handouts.
8. Deploy the remaining tasks and monitor 4xx/5xx and S3 errors.

## Rollback

1. Restore the previous task definition with `USE_S3_STORAGE=False`.
2. Mount the unchanged local media backup.
3. Do not delete S3 objects until the rollback retention period has elapsed.
