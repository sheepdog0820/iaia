import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("schedules", "0056_asyncjob_execution_outcome")]

    operations = [
        migrations.CreateModel(
            name="GoogleJobDispatch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("owner_id_snapshot", models.PositiveBigIntegerField(editable=False)),
                ("job_type_snapshot", models.CharField(editable=False, max_length=80)),
                ("job_created_at", models.DateTimeField(editable=False)),
                ("payload_digest", models.CharField(editable=False, max_length=64)),
                ("ciphertext", models.TextField(editable=False)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "配送待ち"),
                            ("claimed", "投入処理中"),
                            ("delivered", "ワーカー開始確認済み"),
                            ("discarded", "配送対象外"),
                            ("failed", "配送情報を確認できません"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("claim_token", models.UUIDField(blank=True, editable=False, null=True)),
                ("claim_until", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="google_dispatch",
                        to="schedules.asyncjob",
                    ),
                ),
            ],
            options={"indexes": [models.Index(fields=["state", "next_attempt_at"], name="google_dispatch_due_idx")]},
        ),
    ]
