"""Separate creator history from consent-based current group ownership."""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def initialize_owners(apps, schema_editor):
    group_model = apps.get_model("accounts", "Group")
    membership_model = apps.get_model("accounts", "GroupMembership")
    alias = schema_editor.connection.alias
    for group in group_model.objects.using(alias).order_by("pk").iterator(chunk_size=2000):
        if group.created_by_id is None:
            raise ValueError("作成者不明のグループがあるため、所有者の初期設定を中止しました。")
        group.owner_id = group.created_by_id
        group.save(using=alias, update_fields=["owner"])
        membership_model.objects.using(alias).update_or_create(
            group_id=group.pk, user_id=group.owner_id, defaults={"role": "admin"}
        )


def guard_reversal(apps, schema_editor):
    group_model = apps.get_model("accounts", "Group")
    transfer_model = apps.get_model("accounts", "GroupOwnershipTransfer")
    alias = schema_editor.connection.alias
    if (
        transfer_model.objects.using(alias).exists()
        or group_model.objects.using(alias)
        .filter(
            models.Q(owner__isnull=True) | models.Q(created_by__isnull=True) | ~models.Q(owner=models.F("created_by"))
        )
        .exists()
    ):
        raise IrreversibleError("現在の所有者・申請を失うため逆移行できません。無断で元所有者へ戻さないでください。")
    # Membership roles remain intact. Do not undo permissions granted with consent.


class Migration(migrations.Migration):
    dependencies = [("accounts", "0068_merge_skill_bonus_into_other")]

    operations = [
        migrations.AddField(
            model_name="group",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_groups",
                to=settings.AUTH_USER_MODEL,
                verbose_name="所有者",
            ),
        ),
        migrations.AlterField(
            model_name="group",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_groups",
                to=settings.AUTH_USER_MODEL,
                verbose_name="作成者",
            ),
        ),
        migrations.CreateModel(
            name="GroupOwnershipTransfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "group",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ownership_transfer",
                        to="accounts.group",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_group_ownership_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_group_ownership_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=~models.Q(requested_by=models.F("target")), name="group_ownership_users_must_differ"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(expires_at__gt=models.F("created_at")),
                        name="group_ownership_expiry_after_creation",
                    ),
                ],
            },
        ),
        migrations.RunPython(initialize_owners, guard_reversal),
        migrations.AlterField(
            model_name="group",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_groups",
                to=settings.AUTH_USER_MODEL,
                verbose_name="所有者",
            ),
        ),
    ]
