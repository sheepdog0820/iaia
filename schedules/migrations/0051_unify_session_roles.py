from django.db import migrations, models


ROLE_PRIORITY = {
    "owner": 4,
    "manager": 3,
    "gm": 2,
    "player": 1,
}


def _preferred_role(session, participant, roles):
    normalized = {"player" if role == "observer" else role for role in roles if role}
    if participant.user_id and session.created_by_id == participant.user_id:
        return "owner"
    if "manager" in normalized:
        return "manager"
    if "owner" in normalized:
        return "manager"
    if "gm" in normalized or (participant.user_id and session.gm_id == participant.user_id):
        return "gm"
    return "player"


def _set_single_role(role_manager, participant, role):
    existing = list(role_manager.filter(participant=participant).order_by("id"))
    if existing:
        keeper = next((item for item in existing if item.role == role), existing[0])
        role_manager.filter(participant=participant).exclude(id=keeper.id).delete()
        if keeper.role != role:
            keeper.role = role
            keeper.save(update_fields=["role"])
    else:
        role_manager.create(participant=participant, role=role)


def unify_roles(apps, schema_editor):
    TRPGSession = apps.get_model("schedules", "TRPGSession")
    SessionParticipant = apps.get_model("schedules", "SessionParticipant")
    SessionParticipantRole = apps.get_model("schedules", "SessionParticipantRole")
    SessionPermission = apps.get_model("schedules", "SessionPermission")
    SessionInvitation = apps.get_model("schedules", "SessionInvitation")

    db_alias = schema_editor.connection.alias

    role_manager = SessionParticipantRole.objects.using(db_alias)
    for role in role_manager.filter(role="observer"):
        if role_manager.filter(participant_id=role.participant_id, role="player").exclude(id=role.id).exists():
            role.delete()
        else:
            role.role = "player"
            role.save(update_fields=["role"])
    SessionInvitation.objects.using(db_alias).filter(invited_role="observer").update(invited_role="player")

    for session in TRPGSession.objects.using(db_alias).all().iterator():
        participant_by_user_id = {
            participant.user_id: participant
            for participant in SessionParticipant.objects.using(db_alias).filter(session=session, user_id__isnull=False)
        }

        if session.created_by_id and session.created_by_id not in participant_by_user_id:
            participant_by_user_id[session.created_by_id] = SessionParticipant.objects.using(db_alias).create(
                session=session,
                user_id=session.created_by_id,
            )

        if session.gm_id and session.gm_id not in participant_by_user_id:
            participant_by_user_id[session.gm_id] = SessionParticipant.objects.using(db_alias).create(
                session=session,
                user_id=session.gm_id,
            )

        permission_roles_by_user_id = {}
        for permission in SessionPermission.objects.using(db_alias).filter(session=session):
            permission_roles_by_user_id.setdefault(permission.user_id, set()).add(permission.role)
            if permission.user_id not in participant_by_user_id:
                participant_by_user_id[permission.user_id] = SessionParticipant.objects.using(db_alias).create(
                    session=session,
                    user_id=permission.user_id,
                )

        participants = SessionParticipant.objects.using(db_alias).filter(session=session).order_by("id")
        for participant in participants:
            current_roles = set(
                SessionParticipantRole.objects.using(db_alias)
                .filter(participant=participant)
                .values_list("role", flat=True)
            )
            if participant.user_id:
                current_roles.update(permission_roles_by_user_id.get(participant.user_id, set()))
                if session.gm_id == participant.user_id:
                    current_roles.add("gm")
            role = _preferred_role(session, participant, current_roles)
            _set_single_role(SessionParticipantRole.objects.using(db_alias), participant, role)


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0050_participantclaimrequest"),
    ]

    operations = [
        migrations.RunPython(unify_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sessionparticipantrole",
            name="role",
            field=models.CharField(
                choices=[
                    ("owner", "作成者"),
                    ("manager", "運用管理者"),
                    ("gm", "GM"),
                    ("player", "PL"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="sessionparticipantrole",
            name="uniq_participant_role",
        ),
        migrations.AddConstraint(
            model_name="sessionparticipantrole",
            constraint=models.UniqueConstraint(
                fields=("participant",),
                name="uniq_participant_single_role",
            ),
        ),
        migrations.AlterField(
            model_name="sessioninvitation",
            name="invited_role",
            field=models.CharField(
                choices=[
                    ("player", "PL"),
                    ("gm", "GM"),
                ],
                default="player",
                help_text="Session role assigned when the invitation is accepted",
                max_length=10,
            ),
        ),
        migrations.DeleteModel(
            name="SessionPermission",
        ),
    ]
