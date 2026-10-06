import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("schedules", "0058_google_dispatch_delete_cascade")]

    operations = [
        migrations.CreateModel(
            name="GoogleWriteTarget",
            fields=[
                ("resource_key", models.CharField(editable=False, max_length=64, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveBigIntegerField(default=0, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name="GoogleWriteAdmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("owner_id_snapshot", models.PositiveBigIntegerField(editable=False)),
                ("job_type_snapshot", models.CharField(editable=False, max_length=80)),
                ("job_created_at", models.DateTimeField(editable=False)),
                ("payload_digest", models.CharField(editable=False, max_length=64)),
                ("allocation_digest", models.CharField(editable=False, max_length=64)),
                ("snapshot_binding", models.CharField(editable=False, max_length=64)),
                ("ciphertext", models.TextField(editable=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="google_write_admission",
                        to="schedules.asyncjob",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GoogleWriteReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveBigIntegerField(editable=False)),
                (
                    "admission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reservations",
                        to="schedules.googlewriteadmission",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="schedules.googlewritetarget",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("target", "sequence"), name="google_write_target_sequence_unique"),
                    models.UniqueConstraint(
                        fields=("admission", "target"), name="google_write_admission_target_unique"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("sequence__gt", 0)), name="google_write_sequence_positive"
                    ),
                ]
            },
        ),
    ]
