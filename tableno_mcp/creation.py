import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

from django.core import signing
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from mcp.server.fastmcp.exceptions import ToolError
from rest_framework.exceptions import ValidationError

from accounts.character_models import (
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
    CharacterSkill6th,
    CharacterSkill7th,
)
from accounts.serializers import CharacterSheetCreateSerializer
from schedules.serializers import TRPGSessionSerializer
from schedules.session_creation import SESSION_CREATED, queue_session_creation_integrations, save_session
from schedules.tasks import calendar_integrations_for_users, discord_event_settings
from tableno_mcp.config import AWS_PRE_ORIGIN, MAX_CONFIRMATION_TOKEN_LENGTH
from tableno_mcp.models import CreationReceipt

PREVIEW_LIFETIME = 600
PREVIEW_SALT = "tableno-mcp.create.v1"
NO_NOTIFICATIONS = {"discord": False, "google_calendar": False}


def _session(user, payload):
    fields = {
        key: payload[key]
        for key in (
            "title",
            "description",
            "date",
            "location",
            "visibility",
            "duration_minutes",
            "coc_edition",
            "as_gm",
        )
        if payload[key] is not None
    }
    fields.update(group=payload["group_id"], scenario=payload["scenario_id"], status="planned")
    serializer = TRPGSessionSerializer(data=fields, context={"request": SimpleNamespace(user=user, data=fields)})
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    group, scenario = values["group"], values["scenario"]
    discord = (
        discord_event_settings(group.pk, SESSION_CREATED) if group and payload["send_discord_notification"] else None
    )
    calendar = next(calendar_integrations_for_users([user.pk]), None) if payload["sync_google_calendar"] else None
    date = values.get("date")
    preview = {
        "title": values["title"],
        "description": values["description"],
        "date": date.isoformat() if date else None,
        "location": values["location"],
        "group": {"id": group.pk, "name": group.name} if group else None,
        "scenario": {"id": scenario.pk, "title": scenario.title} if scenario else None,
        "visibility": values["visibility"],
        "duration_minutes": values["duration_minutes"],
        "coc_edition": values["coc_edition"],
        "as_gm": payload["as_gm"],
        "status": values["status"],
        "notifications": {"discord": discord is not None, "google_calendar": calendar is not None},
    }
    revision = [item.updated_at.isoformat() if item else None for item in (discord, calendar)]
    return serializer, preview, revision


def _character(user, payload):
    abilities = {f"{key}_value": value for key, value in payload["abilities"].items()}
    fields = {**payload, **abilities, "access_scope": "private"}
    del fields["abilities"]
    if fields["luck"] is None:
        del fields["luck"]
    serializer = CharacterSheetCreateSerializer(
        data=fields, context={"request": SimpleNamespace(user=user, data=fields)}
    )
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    edition = values["edition"]
    if edition == "6th" and "luck" in values:
        raise ToolError("6版の幸運はPOWから計算します。幸運の入力を外してください。")
    detail_model, skill_model = (
        (CharacterSheet6th, CharacterSkill6th) if edition == "6th" else (CharacterSheet7th, CharacterSkill7th)
    )
    detail = detail_model(
        character_sheet=CharacterSheet(user=user, edition=edition),
        occupation_point_method=values["occupation_point_method"],
        **abilities,
    )
    skills = [skill_model(**skill) for skill in values["skills"]]
    for skill in skills:
        skill.clean()
    if len({skill.skill_name for skill in skills}) != len(skills):
        raise ToolError("同じ名前の技能は1件にまとめてください。")
    if sum(skill.occupation_points for skill in skills) > detail.calculate_occupation_points():
        raise ToolError("職業技能ポイントの合計が上限を超えています。")
    if sum(skill.interest_points for skill in skills) > detail.calculate_hobby_points():
        raise ToolError("趣味技能ポイントの合計が上限を超えています。")

    latest_version = (
        detail_model.objects.filter(character_sheet__user=user, name=values["name"]).aggregate(latest=Max("version"))[
            "latest"
        ]
        or 0
    )
    preview = {
        **payload,
        "name": values["name"],
        "skills": [dict(row) for row in values["skills"]],
        "equipment": [dict(row) for row in values["equipment"]],
        "version": latest_version + 1,
        "access_scope": values["access_scope"],
        "notifications": NO_NOTIFICATIONS,
    }
    return serializer, preview, []


def _prepare(kind, user, payload):
    try:
        serializer, preview, revision = (_session if kind == "session" else _character)(user, payload)
    except (ValidationError, ModelValidationError) as error:
        details = error.detail if isinstance(error, ValidationError) else error.message_dict
        raise ToolError(f"入力内容を確認してください。 {json.dumps(details, ensure_ascii=False)}") from None
    snapshot = json.dumps([preview, revision], ensure_ascii=False, sort_keys=True).encode()
    return serializer, preview, hashlib.sha256(snapshot).hexdigest()


def preview_creation(user, *, kind, payload):
    _, preview, digest = _prepare(kind, user, payload)
    token = signing.dumps(
        {"user": user.pk, "kind": kind, "nonce": str(uuid4()), "payload": payload, "digest": digest},
        salt=PREVIEW_SALT,
        compress=True,
    )
    if len(token) > MAX_CONFIRMATION_TOKEN_LENGTH:
        raise ToolError("確認情報が長すぎます。説明や装備の記述を短くしてやり直してください。")
    return {"preview": preview, "confirmation_token": token, "expires_in_seconds": PREVIEW_LIFETIME}


@transaction.atomic
def confirm_creation(user, *, kind, confirmation_token):
    try:
        confirmed = signing.loads(confirmation_token, salt=PREVIEW_SALT, max_age=PREVIEW_LIFETIME)
    except signing.BadSignature:
        raise ToolError("確認情報が無効か期限切れです。プレビューをやり直してください。") from None
    if confirmed["user"] != user.pk or confirmed["kind"] != kind:
        raise ToolError("この作成操作には指定された確認情報を使用できません。")

    receipt, created = CreationReceipt.objects.get_or_create(pk=confirmed["nonce"])
    if created:
        serializer, preview, digest = _prepare(kind, user, confirmed["payload"])
        if digest != confirmed["digest"]:
            raise ToolError("作成内容または連携設定が変わりました。プレビューをやり直してください。")
        try:
            if kind == "session":
                record = save_session(serializer, user, as_gm=preview["as_gm"])

                def enqueue_confirmed_integrations():
                    queue_session_creation_integrations(record, **preview["notifications"])

                if any(preview["notifications"].values()):
                    transaction.on_commit(enqueue_confirmed_integrations, robust=True)
            else:
                record = serializer.save()
        except ValidationError:
            raise ToolError("入力内容を保存できませんでした。プレビューからやり直してください。") from None
        receipt.object_id = record.pk
        receipt.save(update_fields=["object_id"])

    if kind == "session":
        path = reverse("session_detail", kwargs={"pk": receipt.object_id})
    else:
        path = reverse("character_detail", kwargs={"character_id": receipt.object_id})
    return {"id": str(receipt.object_id), "url": f"{AWS_PRE_ORIGIN}{path}"}
