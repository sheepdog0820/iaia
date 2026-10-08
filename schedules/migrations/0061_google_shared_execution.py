import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def protect_execution_journal(apps, schema_editor):
    """Do not erase durable evidence, including finished executions, on downgrade."""
    if schema_editor.connection.vendor == "postgresql":
        # Hold the writer lock until the atomic reverse migration finishes. A
        # mere existence check would race with a worker's first journal insert.
        schema_editor.execute('LOCK TABLE "schedules_googlewriteexecution" IN ACCESS EXCLUSIVE MODE')
    elif schema_editor.connection.vendor == "sqlite":
        schema_editor.execute('UPDATE "schedules_googlewriteexecution" SET state=state WHERE 0=1')
    else:
        raise RuntimeError("Google実行記録を保護できないDBのため逆移行できません。")
    execution = apps.get_model("schedules", "GoogleWriteExecution")
    if execution.objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError("Google実行記録が残っているため逆移行できません。保存・復旧方針を確認してください。")


class Migration(migrations.Migration):
    dependencies = [("schedules", "0060_google_write_delete_cascade")]

    operations = [
        migrations.AddField(
            model_name="googlewritetarget",
            name="last_started_sequence",
            field=models.PositiveBigIntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name="googlewritetarget",
            name="active_execution_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.CreateModel(
            name="GoogleWriteExecution",
            fields=[
                ("token", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("job_id_snapshot", models.UUIDField(db_index=True, editable=False)),
                ("admission_binding", models.CharField(editable=False, max_length=64)),
                ("allocation_binding", models.CharField(editable=False, max_length=64)),
                (
                    "state",
                    models.CharField(
                        choices=[("active", "実行中"), ("unknown", "結果確認が必要"), ("finished", "実行終了確認済み")],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("closed_at", models.DateTimeField(editable=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="GoogleWriteExecutionTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveBigIntegerField(editable=False)),
                (
                    "execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="allocations",
                        to="schedules.googlewriteexecution",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="executions",
                        to="schedules.googlewritetarget",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("execution", "target"), name="google_execution_target_unique"),
                    models.CheckConstraint(
                        condition=models.Q(("sequence__gt", 0)), name="google_execution_sequence_positive"
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="GoogleWriteRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ordinal", models.PositiveIntegerField(editable=False)),
                ("request_digest", models.CharField(editable=False, max_length=64)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("intent", "送信結果未確定"),
                            ("known", "応答確認済み"),
                            ("unknown", "結果確認が必要"),
                        ],
                        default="intent",
                        max_length=16,
                    ),
                ),
                ("response_status", models.PositiveSmallIntegerField(editable=False, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("received_at", models.DateTimeField(editable=False, null=True)),
                (
                    "execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests",
                        to="schedules.googlewriteexecution",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("execution", "ordinal"), name="google_execution_request_unique"),
                    models.CheckConstraint(
                        condition=models.Q(("ordinal__gt", 0)), name="google_request_ordinal_positive"
                    ),
                ]
            },
        ),
        # Reverse this guard first, before dropping any journal table/field.
        migrations.RunPython(migrations.RunPython.noop, protect_execution_journal),
    ]
