import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


PARTICIPANT_ROLES = {"gm", "player", "observer"}


def backfill_session_roles_and_permissions(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    TRPGSession = apps.get_model("schedules", "TRPGSession")
    SessionParticipant = apps.get_model("schedules", "SessionParticipant")
    SessionParticipantRole = apps.get_model("schedules", "SessionParticipantRole")
    SessionPermission = apps.get_model("schedules", "SessionPermission")
    ParticipantIdentity = apps.get_model("schedules", "ParticipantIdentity")

    for participant in SessionParticipant.objects.using(db_alias).all().iterator():
        role = participant.role if participant.role in PARTICIPANT_ROLES else "player"
        SessionParticipantRole.objects.using(db_alias).get_or_create(
            participant_id=participant.id,
            role=role,
        )

    sessions = TRPGSession.objects.using(db_alias).all().iterator()
    for session in sessions:
        if session.created_by_id:
            SessionPermission.objects.using(db_alias).get_or_create(
                session_id=session.id,
                user_id=session.created_by_id,
                role="owner",
            )

        if not session.gm_id:
            continue

        participant = (
            SessionParticipant.objects.using(db_alias)
            .filter(session_id=session.id, user_id=session.gm_id)
            .order_by("id")
            .first()
        )
        if participant is None:
            participant = SessionParticipant.objects.using(db_alias).create(
                session_id=session.id,
                user_id=session.gm_id,
                role="gm",
            )

        SessionParticipantRole.objects.using(db_alias).get_or_create(
            participant_id=participant.id,
            role="gm",
        )
        SessionPermission.objects.using(db_alias).get_or_create(
            session_id=session.id,
            user_id=session.gm_id,
            role="secret_keeper",
        )

    for identity in ParticipantIdentity.objects.using(db_alias).all().iterator():
        update_fields = []

        if not identity.group_id:
            group_ids = set(
                SessionParticipant.objects.using(db_alias)
                .filter(
                    participant_identity_id=identity.id,
                    session__group_id__isnull=False,
                )
                .values_list("session__group_id", flat=True)
                .distinct()
            )
            if len(group_ids) == 1:
                identity.group_id = group_ids.pop()
                update_fields.append("group")

        if not identity.user_id:
            user_ids = set(
                SessionParticipant.objects.using(db_alias)
                .filter(
                    participant_identity_id=identity.id,
                    user_id__isnull=False,
                )
                .values_list("user_id", flat=True)
                .distinct()
            )
            if len(user_ids) == 1:
                identity.user_id = user_ids.pop()
                update_fields.append("user")

        if update_fields:
            identity.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0045_remove_legacy_participant_identity_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="sessionparticipant",
            name="sessionparticipant_gm_requires_user",
        ),
        migrations.AlterField(
            model_name="trpgsession",
            name="gm",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gm_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="trpgsession",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sessions",
                to="accounts.group",
            ),
        ),
        migrations.AlterField(
            model_name="sessionparticipant",
            name="role",
            field=models.CharField(
                choices=[("gm", "GM"), ("player", "PL"), ("observer", "Observer")],
                default="player",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="participantidentity",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_participant_identities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="participantidentity",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participant_identities",
                to="accounts.group",
            ),
        ),
        migrations.AddField(
            model_name="participantidentity",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="participant_identities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="SessionParticipantRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[("gm", "GM"), ("player", "Player"), ("observer", "Observer")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "participant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participant_roles",
                        to="schedules.sessionparticipant",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("participant", "role"),
                        name="uniq_participant_role",
                    )
                ],
                "indexes": [
                    models.Index(fields=["role"], name="participant_role_role_idx"),
                    models.Index(fields=["participant", "role"], name="participant_role_lookup_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SessionPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("manager", "Manager"),
                            ("secret_keeper", "Secret keeper"),
                            ("viewer", "Viewer"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="granted_session_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_permissions",
                        to="schedules.trpgsession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("session", "user", "role"),
                        name="uniq_session_permission_role",
                    )
                ],
                "indexes": [
                    models.Index(fields=["session", "role"], name="sess_perm_session_role_idx"),
                    models.Index(fields=["user", "role"], name="sess_perm_user_role_idx"),
                ],
            },
        ),
        migrations.AddIndex(
            model_name="participantidentity",
            index=models.Index(fields=["group", "normalized_name"], name="part_identity_group_name_idx"),
        ),
        migrations.AddIndex(
            model_name="participantidentity",
            index=models.Index(fields=["user"], name="part_identity_user_idx"),
        ),
        migrations.RunPython(backfill_session_roles_and_permissions, migrations.RunPython.noop),
    ]
