import base64
import hashlib
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django.test import Client
from django.utils import timezone
from mcp.server.fastmcp.exceptions import ToolError
from rest_framework.exceptions import ValidationError
from starlette.testclient import TestClient

from accounts.character_models import CharacterSheet, CharacterSheet6th
from accounts.models import Group, GroupDiscordSettings
from accounts.serializers import CharacterSheetCreateSerializer
from schedules.models import GoogleIntegration, TRPGSession
from tableno_mcp.config import AWS_PRE_ORIGIN, MCP_RESOURCE, WRITE_SCOPES
from tableno_mcp.http import PilotTokenVerifier, create_app, run_for_user

pytestmark = [
    pytest.mark.skipif(not getattr(settings, "TABLENO_MCP_ENABLED", False), reason="use --ds=tests.mcp_settings"),
    pytest.mark.django_db(transaction=True),
]

CALLBACK = "http://127.0.0.1:1455/callback"
VERIFIER = "v" * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
ACCEPT = "application/json, text/event-stream"


@pytest.fixture
def pilot():
    from oauth2_provider.models import get_application_model

    model = get_application_model()
    client_app = model.objects.create(
        client_id=settings.TABLENO_MCP_CLIENT_ID,
        client_type=model.CLIENT_PUBLIC,
        authorization_grant_type=model.GRANT_AUTHORIZATION_CODE,
        name="Codex",
        redirect_uris=CALLBACK,
    )
    user = get_user_model().objects.create(pk=101, username="pilot")
    other = get_user_model().objects.create(pk=102, username="other")
    browser = Client(enforce_csrf_checks=True, HTTP_HOST=urlsplit(AWS_PRE_ORIGIN).netloc)
    browser.force_login(user)
    return browser, client_app, user, other


def authorize(browser, client_app, **overrides):
    params = {
        "client_id": client_app.client_id,
        "redirect_uri": CALLBACK,
        "response_type": "code",
        "code_challenge": CHALLENGE,
        "code_challenge_method": "S256",
        "state": "pilot-state",
        "scope": "sessions:read characters:read",
        "resource": MCP_RESOURCE,
        **overrides,
    }
    page = browser.get("/mcp/oauth/authorize/", params, secure=True)
    assert page.status_code == 200 and "タブレノへのアクセスを許可" in page.content.decode()
    approval = {**params, "allow": "1"}
    assert browser.post("/mcp/oauth/authorize/", approval, secure=True, HTTP_ORIGIN=AWS_PRE_ORIGIN).status_code == 403
    response = browser.post(
        "/mcp/oauth/authorize/",
        {**approval, "csrfmiddlewaretoken": browser.cookies["csrftoken"].value},
        secure=True,
        HTTP_ORIGIN=AWS_PRE_ORIGIN,
    )
    assert response.status_code == 302
    query = parse_qs(urlsplit(response["Location"]).query)
    assert query["state"] == ["pilot-state"]
    assert query["iss"] == [AWS_PRE_ORIGIN]
    return query["code"][0]


def exchange(browser, client_app, code, **overrides):
    return browser.post(
        "/mcp/oauth/token/",
        {
            "grant_type": "authorization_code",
            "client_id": client_app.client_id,
            "redirect_uri": CALLBACK,
            "code_verifier": VERIFIER,
            "code": code,
            "resource": MCP_RESOURCE,
            **overrides,
        },
        secure=True,
    )


def protocol(client, method, *, token=None, params=None):
    headers = {"Accept": ACCEPT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(
        "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    )


def test_oauth_discovery_and_access_with_pkce(pilot):
    browser, client_app, user, other = pilot
    metadata = browser.get("/.well-known/oauth-authorization-server", secure=True).json()
    assert metadata["issuer"] == AWS_PRE_ORIGIN
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    assert "registration_endpoint" not in metadata
    resource = browser.get("/.well-known/oauth-protected-resource/mcp", secure=True).json()
    assert resource["resource"] == MCP_RESOURCE
    assert resource["authorization_servers"] == [AWS_PRE_ORIGIN]
    code = authorize(browser, client_app)
    assert exchange(browser, client_app, code, code_verifier="x" * 64).status_code == 400
    valid = exchange(browser, client_app, code)
    assert valid.status_code == 200, valid.content
    assert exchange(browser, client_app, code).status_code == 400
    token = valid.json()["access_token"]
    session = TRPGSession.objects.create(
        title="本人の卓", created_by=user, date=timezone.now() + timedelta(days=1), description="秘匿メモ"
    )
    TRPGSession.objects.create(title="別人の卓", created_by=other, date=timezone.now() + timedelta(hours=1))
    sheet = CharacterSheet.objects.create(user=user, edition="6th")
    CharacterSheet6th.objects.create(character_sheet=sheet, name="本人の探索者", secret_ho_info="秘匿HO")
    other_sheet = CharacterSheet.objects.create(user=other, edition="6th")
    CharacterSheet6th.objects.create(character_sheet=other_sheet, name="別人の探索者")

    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        assert mcp.get("/health/live").text == "ok"
        response = protocol(mcp, "tools/list")
        assert (
            response.status_code == 401
            and "/.well-known/oauth-protected-resource/mcp" in response.headers["WWW-Authenticate"]
        )
        tools = protocol(mcp, "tools/list", token=token).json()["result"]["tools"]
        assert {tool["name"] for tool in tools} == {"get_next_session", "list_my_characters", "get_character"}
        assert all(tool["annotations"]["readOnlyHint"] for tool in tools)
        result = protocol(mcp, "tools/call", token=token, params={"name": "get_next_session"}).json()["result"]
        assert result["structuredContent"]["session"]["id"] == str(session.pk)
        assert "秘匿メモ" not in repr(result)
        result = protocol(mcp, "tools/call", token=token, params={"name": "list_my_characters"}).json()["result"]
        assert [item["id"] for item in result["structuredContent"]["items"]] == [str(sheet.pk)]
        result = protocol(
            mcp,
            "tools/call",
            token=token,
            params={"name": "get_character", "arguments": {"character_id": str(sheet.pk)}},
        ).json()["result"]
        assert result["structuredContent"]["character"]["name"] == "本人の探索者"
        assert "秘匿HO" not in repr(result)
        result = protocol(
            mcp,
            "tools/call",
            token=token,
            params={"name": "get_character", "arguments": {"character_id": str(other_sheet.pk)}},
        ).json()["result"]
        assert result["structuredContent"]["character"] is None

        browser.force_login(other)
        second = exchange(browser, client_app, authorize(browser, client_app))
        assert second.status_code == 200
        second_token = second.json()["access_token"]
        result = protocol(mcp, "tools/call", token=second_token, params={"name": "list_my_characters"}).json()["result"]
        assert [item["id"] for item in result["structuredContent"]["items"]] == [str(other_sheet.pk)]

        revoked = browser.post(
            "/mcp/oauth/revoke_token/",
            {"client_id": client_app.client_id, "token": token},
            secure=True,
        )
        assert revoked.status_code == 200
        assert protocol(mcp, "tools/list", token=token).status_code == 401


def test_token_and_origin_boundaries(pilot):
    from oauth2_provider.models import get_access_token_model

    browser, client_app, user, _ = pilot
    code = authorize(browser, client_app)
    assert exchange(browser, client_app, code, resource=AWS_PRE_ORIGIN + "/other").status_code == 400
    code = authorize(browser, client_app, scope="characters:read")
    token_response = exchange(browser, client_app, code)
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        denied = protocol(mcp, "tools/call", token=token, params={"name": "get_next_session"}).json()["result"]
        assert denied["isError"]
        assert (
            mcp.post(
                "/mcp",
                headers={"Host": "invalid.example", "Accept": ACCEPT, "Authorization": f"Bearer {token}"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            ).status_code
            == 421
        )
        assert (
            mcp.post(
                "/mcp",
                headers={"Origin": "https://invalid.example", "Accept": ACCEPT, "Authorization": f"Bearer {token}"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            ).status_code
            == 403
        )
        access_tokens = get_access_token_model().objects.filter(user=user)
        access_tokens.update(resource=[AWS_PRE_ORIGIN + "/mcp-other"])
        assert protocol(mcp, "tools/list", token=token).status_code == 401
        access_tokens.update(resource=[MCP_RESOURCE], expires=timezone.now() - timedelta(seconds=1))
        assert protocol(mcp, "tools/list", token=token).status_code == 401
        access_tokens.update(expires=timezone.now() + timedelta(minutes=1))
        user.is_active = False
        user.save(update_fields=["is_active"])
        assert protocol(mcp, "tools/list", token=token).status_code == 401


def test_authorization_limits_pilot_accounts_and_public_client(pilot):
    browser, client_app, _, _ = pilot
    params = {
        "client_id": client_app.client_id,
        "redirect_uri": CALLBACK,
        "response_type": "code",
        "code_challenge": CHALLENGE,
        "code_challenge_method": "S256",
        "scope": "sessions:read",
        "resource": MCP_RESOURCE,
    }
    response = browser.get("/mcp/oauth/authorize/", {**params, "client_id": "unknown"}, secure=True)
    assert 'name="allow"' not in response.content.decode()
    for overrides in (
        {"code_challenge_method": "plain"},
        {"code_challenge": ""},
        {"redirect_uri": "https://wrong.test"},
    ):
        denied = browser.get("/mcp/oauth/authorize/", {**params, **overrides}, secure=True)
        assert 'name="allow"' not in denied.content.decode()
    assert browser.get("/mcp/oauth/authorize/", {**params, "resource": ""}, secure=True).status_code == 400

    assert browser.get("/mcp/oauth/authorize/", params, secure=True).status_code == 200
    for tampered in ({"resource": ""}, {"code_challenge_method": "plain"}, {"client_id": "unknown"}):
        response = browser.post(
            "/mcp/oauth/authorize/",
            {**params, **tampered, "allow": "1", "csrfmiddlewaretoken": browser.cookies["csrftoken"].value},
            secure=True,
            HTTP_ORIGIN=AWS_PRE_ORIGIN,
        )
        assert response.status_code == 400

    outsider = get_user_model().objects.create(pk=103, username="outside-pilot")
    browser.force_login(outsider)
    assert browser.get("/mcp/oauth/authorize/", params, secure=True).status_code == 403
    browser.logout()
    response = browser.get("/mcp/oauth/authorize/", params, secure=True)
    assert response.status_code == 302 and urlsplit(response["Location"]).path == "/accounts/login/"


def test_refresh_token_rotates_and_replay_revokes_new_token(pilot):
    browser, client_app, _, _ = pilot
    response = exchange(browser, client_app, authorize(browser, client_app))
    assert response.status_code == 200
    old = response.json()
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_app.client_id,
        "refresh_token": old["refresh_token"],
        "resource": MCP_RESOURCE,
    }
    response = browser.post("/mcp/oauth/token/", payload, secure=True)
    assert response.status_code == 200
    new = response.json()
    assert new["refresh_token"] != old["refresh_token"]
    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        assert protocol(mcp, "tools/list", token=new["access_token"]).status_code == 200
        assert browser.post("/mcp/oauth/token/", payload, secure=True).status_code == 400
        assert protocol(mcp, "tools/list", token=new["access_token"]).status_code == 401


def test_postgres_tool_transactions_refuse_database_writes(pilot):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL transaction mode")
    _, _, user, _ = pilot

    def write_instead_of_reading(owner):
        owner.username = "changed"
        owner.save(update_fields=["username"])

    with pytest.raises(ToolError, match="データを読み取れません"):
        async_to_sync(run_for_user)(user.pk, write_instead_of_reading)
    user.refresh_from_db()
    assert user.username == "pilot"


def test_missing_or_unavailable_identity_stops_reads(monkeypatch):
    from oauth2_provider.models import get_access_token_model

    def unavailable(*args, **kwargs):
        raise DatabaseError("private database diagnostic")

    monkeypatch.setattr(get_access_token_model().objects, "select_related", unavailable)
    assert async_to_sync(PilotTokenVerifier().verify_token)("opaque-test-value") is None

    def must_not_run(user):
        pytest.fail("read executed for an unapproved user")

    with pytest.raises(ToolError, match="このアカウント"):
        async_to_sync(run_for_user)(999, must_not_run)


@pytest.fixture
def write_pilot(pilot, settings):
    settings.TABLENO_MCP_WRITE_ENABLED = True
    settings.OAUTH2_PROVIDER = {
        **settings.OAUTH2_PROVIDER,
        "SCOPES": settings.OAUTH2_PROVIDER["SCOPES"] | WRITE_SCOPES,
    }
    return pilot


def call_tool(mcp, token, name, **arguments):
    response = protocol(mcp, "tools/call", token=token, params={"name": name, "arguments": arguments})
    return response.json()["result"]


def issue_test_token(browser, client_app, scope):
    response = exchange(browser, client_app, authorize(browser, client_app, scope=scope))
    assert response.status_code == 200
    return response.json()["access_token"]


def test_session_creation_previews_and_queues_only_confirmed_integrations(write_pilot, monkeypatch):
    browser, client_app, user, _ = write_pilot
    token = issue_test_token(browser, client_app, "sessions:write")
    group = Group.objects.create(name="検証グループ", owner=user)
    GoogleIntegration.objects.create(
        user=user, calendar_enabled=True, scopes=[GoogleIntegration.REQUIRED_CALENDAR_SCOPE]
    )
    discord = GroupDiscordSettings.objects.create(group=group, enabled=True, event_types=["session_created"])
    notices = []
    monkeypatch.setattr(
        "schedules.tasks.send_discord_webhook.delay", lambda *args: notices.append(("discord", args[0]))
    )
    monkeypatch.setattr("schedules.tasks._broker_available", lambda: True)

    def queue_google(sync_id, job_id):
        notices.append(("google", sync_id))
        return SimpleNamespace(id="test-job")

    monkeypatch.setattr("schedules.tasks.sync_google_calendar.delay", queue_google)
    data = {
        "title": "MCPで作る卓",
        "date": "2027-01-10T20:00:00+09:00",
        "group_id": group.pk,
        "send_discord_notification": True,
        "sync_google_calendar": True,
    }
    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        before = call_tool(mcp, token, "preview_session_creation", session=data)["structuredContent"]
        assert before["preview"]["date"] == "2027-01-10T20:00:00+09:00"
        assert before["preview"]["notifications"] == {"discord": True, "google_calendar": True}
        assert not TRPGSession.objects.exists() and not notices

        discord.enabled = False
        discord.save(update_fields=["enabled", "updated_at"])
        stale = call_tool(mcp, token, "create_session", confirmation_token=before["confirmation_token"])
        assert stale["isError"] and not TRPGSession.objects.exists()
        discord.enabled = True
        discord.save(update_fields=["enabled", "updated_at"])
        preview = call_tool(mcp, token, "preview_session_creation", session=data)["structuredContent"]
        result = call_tool(mcp, token, "create_session", confirmation_token=preview["confirmation_token"])
        assert not result.get("isError"), result
        same = call_tool(mcp, token, "create_session", confirmation_token=preview["confirmation_token"])
        assert result["structuredContent"] == same["structuredContent"]
        created = TRPGSession.objects.get()
        detail_url = result["structuredContent"]["url"]
        assert urlsplit(detail_url).netloc == urlsplit(AWS_PRE_ORIGIN).netloc
        assert browser.get(urlsplit(detail_url).path, secure=True).status_code == 200
        assert created.created_by == user and created.participants.filter(pk=user.pk).exists()
        assert [kind for kind, _ in notices] == ["discord", "google"]
        silent = call_tool(
            mcp, token, "preview_session_creation", session={"title": "連携なしの卓", "group_id": group.pk}
        )["structuredContent"]
        assert silent["preview"]["notifications"] == {"discord": False, "google_calendar": False}
        assert not call_tool(mcp, token, "create_session", confirmation_token=silent["confirmation_token"]).get(
            "isError"
        )
        assert TRPGSession.objects.count() == 2
        assert [kind for kind, _ in notices] == ["discord", "google"]


def test_character_creation_requires_own_confirmed_preview_and_returns_detail(write_pilot):
    browser, client_app, user, other = write_pilot
    token = issue_test_token(browser, client_app, "characters:write sessions:write")
    read_only = issue_test_token(browser, client_app, "characters:read")
    browser.force_login(other)
    other_token = issue_test_token(browser, client_app, "characters:write")
    abilities = {key: 50 for key in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")}
    character = {
        "edition": "7th",
        "name": "確認用探索者",
        "abilities": abilities,
        "luck": 55,
        "skills": [{"skill_name": "目星", "base_value": 25, "occupation_points": 30}],
    }
    sixth = CharacterSheet.objects.create(user=user, edition="6th")
    CharacterSheet6th.objects.create(character_sheet=sixth, name=character["name"], version=3)
    group = Group.objects.create(name="別の利用者のグループ", owner=other)
    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        assert call_tool(mcp, token, "preview_session_creation", session={"title": "権限外", "group_id": group.pk})[
            "isError"
        ]
        assert call_tool(mcp, read_only, "preview_character_creation", character=character)["isError"]
        assert call_tool(mcp, token, "preview_character_creation", character={**character, "luck": 52})["isError"]
        preview = call_tool(mcp, token, "preview_character_creation", character=character)["structuredContent"]
        assert preview["preview"]["notifications"] == {"discord": False, "google_calendar": False}
        assert preview["preview"]["version"] == 1
        assert CharacterSheet.objects.count() == 1
        key = preview["confirmation_token"]
        assert call_tool(mcp, token, "create_session", confirmation_token=key)["isError"]
        assert call_tool(mcp, other_token, "create_character", confirmation_token=key)["isError"]
        assert call_tool(mcp, token, "create_character", confirmation_token=key + "invalid")["isError"]
        assert CharacterSheet.objects.count() == 1
        result = call_tool(mcp, token, "create_character", confirmation_token=key)["structuredContent"]
        assert call_tool(mcp, token, "create_character", confirmation_token=key)["structuredContent"] == result
        sheet = CharacterSheet.objects.get(edition="7th")
        assert sheet.user_id == user.pk
        assert sheet.access_scope == "private" and sheet.system_data.version == 1
        assert sheet.system_data.skills.get(skill_name="目星").current_value == 55
        browser.force_login(user)
        detail = browser.get(urlsplit(result["url"]).path, secure=True, follow=True)
        assert detail.status_code == 200 and character["name"] in detail.content.decode()


def test_invalid_character_skills_and_expired_preview_do_not_save(write_pilot, monkeypatch):
    browser, client_app, _, _ = write_pilot
    token = issue_test_token(browser, client_app, "characters:write")
    base = {
        "edition": "6th",
        "name": "技能確認",
        "abilities": {key: 10 for key in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")},
    }
    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        for inputs in (
            {"luck": 55},
            {"skills": [{"skill_name": "目星"}, {"skill_name": "目星"}]},
            {"skills": [{"skill_name": "目星", "occupation_points": 201}]},
            {"skills": [{"skill_name": "目星", "interest_points": 101}]},
            {"skills": [{"skill_name": "目星", "base_value": 999, "other_points": 1}]},
        ):
            assert call_tool(mcp, token, "preview_character_creation", character={**base, **inputs})["isError"]
        key = call_tool(mcp, token, "preview_character_creation", character=base)["structuredContent"][
            "confirmation_token"
        ]
        monkeypatch.setattr("tableno_mcp.creation.PREVIEW_LIFETIME", -1)
        assert call_tool(mcp, token, "create_character", confirmation_token=key)["isError"]
        assert not CharacterSheet.objects.exists()


def test_failed_save_rolls_back_and_confirmation_can_be_retried(write_pilot, monkeypatch):
    from tableno_mcp.models import CreationReceipt

    browser, client_app, _, _ = write_pilot
    token = issue_test_token(browser, client_app, "characters:write")
    character = {
        "edition": "6th",
        "name": "再試行用探索者",
        "abilities": {key: 10 for key in ("str", "con", "pow", "dex", "app", "siz", "int", "edu")},
    }
    save = CharacterSheetCreateSerializer.save

    def fail_after_save(serializer, **kwargs):
        save(serializer, **kwargs)
        raise ValidationError("試験用の保存エラー")

    with TestClient(create_app(), base_url=AWS_PRE_ORIGIN) as mcp:
        with monkeypatch.context() as patch:
            patch.setattr("tableno_mcp.creation.MAX_CONFIRMATION_TOKEN_LENGTH", 1)
            assert call_tool(mcp, token, "preview_character_creation", character=character)["isError"]
        key = call_tool(mcp, token, "preview_character_creation", character=character)["structuredContent"][
            "confirmation_token"
        ]
        with monkeypatch.context() as patch:
            patch.setattr(CharacterSheetCreateSerializer, "save", fail_after_save)
            assert call_tool(mcp, token, "create_character", confirmation_token=key)["isError"]
        assert not CharacterSheet.objects.exists()
        assert not CreationReceipt.objects.exists()
        assert not call_tool(mcp, token, "create_character", confirmation_token=key).get("isError")
        assert CharacterSheet.objects.count() == 1 and CreationReceipt.objects.count() == 1
