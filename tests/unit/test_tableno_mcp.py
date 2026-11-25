import os
import sqlite3
import subprocess
import sys
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from accounts.character_models import (
    CharacterEquipment7th,
    CharacterSheet,
    CharacterSheet6th,
    CharacterSheet7th,
    CharacterSkill7th,
)
from schedules.models import SessionOccurrence, SessionParticipant, TRPGSession
from tableno_mcp.queries import get_character, get_next_session, list_my_characters
from tableno_mcp.server import LocalSetupError, configure_django


def test_configure_django_rejects_other_environments(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "aws-pre")
    with pytest.raises(LocalSetupError, match="APP_ENV=local"):
        configure_django(tmp_path / "data.sqlite3")


@pytest.mark.parametrize(
    ("database_state", "message"),
    [
        ("missing", "SQLiteファイルが見つかりません"),
        ("no_schema", "SQLiteからアカウントを読み取れません"),
        ("no_user", "アカウントが無効か、見つかりません"),
    ],
)
def test_server_reports_configuration_failures(tmp_path, database_state, message):
    pytest.importorskip("mcp")
    path = tmp_path / "data.sqlite3"
    if database_state == "no_schema":
        path.touch()
    elif database_state == "no_user":
        with sqlite3.connect(path) as database:
            database.execute(
                "CREATE TABLE accounts_customuser (id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER)"
            )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "tableno_mcp.server", "--database", str(path), "--username", "unknown"],
        env={**os.environ, "APP_ENV": "local", "DJANGO_SETTINGS_MODULE": "tableno.settings", "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert message in result.stderr


@pytest.mark.django_db
class TestTablenoMcpQueries:
    @pytest.fixture(autouse=True)
    def setup_users(self):
        self.user = get_user_model().objects.create(username="mcp-user")
        self.other = get_user_model().objects.create(username="other-user")

    def test_next_session_uses_actual_occurrence_and_only_my_active_sessions(self):
        now = timezone.now()
        session = TRPGSession.objects.create(
            title="継続卓",
            date=now - timedelta(days=1),
            created_by=self.other,
            visibility="private",
            description="GM専用メモ",
            duration_minutes=120,
        )
        SessionParticipant.objects.create(session=session, user=self.user)
        upcoming = SessionOccurrence.objects.create(session=session, start_at=now + timedelta(days=2))
        TRPGSession.objects.create(title="無関係な公開卓", date=now + timedelta(hours=1), visibility="public")
        TRPGSession.objects.create(
            title="中止", date=now + timedelta(hours=2), created_by=self.user, status="cancelled"
        )
        TRPGSession.objects.create(title="別の予定", date=now + timedelta(days=3), created_by=self.user)

        result = get_next_session(self.user, now=now)

        assert result == {
            "session": {
                "id": str(session.id),
                "occurrence_id": str(upcoming.id),
                "title": "継続卓",
                "start_at": timezone.localtime(upcoming.start_at).isoformat(),
                "duration_minutes": 120,
                "status": "planned",
            }
        }

    def test_next_session_supports_legacy_date_and_no_result(self):
        now = timezone.now()
        assert get_next_session(self.user, now=now) == {"session": None}
        session = TRPGSession.objects.create(title="次の卓", date=now, created_by=self.user)
        session.occurrences.all().delete()

        result = get_next_session(self.user, now=now)["session"]

        assert result["id"] == str(session.id)
        assert result["occurrence_id"] is None

    def test_character_list_search_and_detail_are_limited_to_owner(self):
        sixth = self.make_character(self.user, "6th", "探索者その1", "タンサクシャソノイチ")
        seventh = self.make_character(self.user, "7th", "探索者その2")
        other_sheet = self.make_character(self.other, "7th", "探索者その3")
        other_sheet.allowed_users.add(self.user)
        CharacterSkill7th.objects.create(character_sheet=seventh.system_data, skill_name="目星", base_value=25)
        CharacterEquipment7th.objects.create(
            character_sheet=seventh.system_data, item_type="item", name="懐中電灯", quantity=2, description="個人メモ"
        )

        first_page = list_my_characters(self.user, page=1, limit=1)
        second_page = list_my_characters(self.user, page=2, limit=1)
        assert [row["id"] for row in first_page["items"]] == [str(seventh.id)]
        assert first_page["has_more"] is True
        assert [row["id"] for row in second_page["items"]] == [str(sixth.id)]
        assert second_page["has_more"] is False
        assert [row["id"] for row in list_my_characters(self.user, query="タンサクシャ")["items"]] == [str(sixth.id)]

        result = get_character(self.user, seventh.pk)["character"]
        assert result["edition"] == "7th"
        assert result["abilities"]["str"] == 55
        assert result["status_summary"]["hp"]["current"] == 11
        assert result["skills"] == [{"name": "目星", "value": 25}]
        assert result["equipment"] == [{"name": "懐中電灯", "quantity": 2}]
        assert "秘匿情報" not in repr(result)
        assert "個人メモ" not in repr(result)
        assert get_character(self.user, sixth.pk)["character"]["edition"] == "6th"
        assert get_character(self.user, other_sheet.pk) == get_character(self.user, 999999) == {"character": None}

    @staticmethod
    def make_character(owner, edition, name, kana=""):
        sheet = CharacterSheet.objects.create(user=owner, edition=edition)
        model = CharacterSheet7th if edition == "7th" else CharacterSheet6th
        model.objects.create(
            character_sheet=sheet,
            name=name,
            name_kana=kana,
            str_value=55 if edition == "7th" else 11,
            hit_points_current=11,
            secret_ho_info="秘匿情報",
        )
        return sheet


@pytest.mark.django_db(transaction=True)
def test_stdio_reads_disposable_data_with_only_the_requested_tools(tmp_path):
    import asyncio

    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    user = get_user_model().objects.create(username="mcp-user")
    sheet = TestTablenoMcpQueries.make_character(user, "6th", "試験用探索者")
    TRPGSession.objects.create(title="試験卓", created_by=user, date=timezone.now() + timedelta(days=1))
    database_path = tmp_path / "local.sqlite3"
    with sqlite3.connect(database_path) as database:
        connection.connection.backup(database)

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tableno_mcp.server", "--database", str(database_path), "--username", "mcp-user"],
        env={**os.environ, "APP_ENV": "local", "DJANGO_SETTINGS_MODULE": "tableno.settings"},
    )

    async def check_tools():
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                available = {tool.name: tool.annotations for tool in (await session.list_tools()).tools}
                assert set(available) == {"get_next_session", "list_my_characters", "get_character"}
                assert all(item.readOnlyHint and item.openWorldHint is False for item in available.values())
                upcoming = await session.call_tool("get_next_session", {})
                assert upcoming.structuredContent["session"]["title"] == "試験卓"
                listed = await session.call_tool("list_my_characters", {})
                assert listed.structuredContent["items"][0]["id"] == str(sheet.pk)
                character = await session.call_tool("get_character", {"character_id": str(sheet.pk)})
                assert character.structuredContent["character"]["name"] == "試験用探索者"
                with sqlite3.connect(database_path) as database:
                    database.execute("UPDATE accounts_customuser SET is_active=0 WHERE id=?", (user.pk,))
                denied = await session.call_tool("list_my_characters", {})
                assert denied.isError
                assert "アカウント" in denied.content[0].text
                with sqlite3.connect(database_path) as database:
                    database.execute("DROP TABLE accounts_customuser")
                unavailable = await session.call_tool("list_my_characters", {})
                assert unavailable.isError
                assert "ローカルSQLiteから読み取れません" in unavailable.content[0].text

    asyncio.run(check_tools())


def test_django_connection_refuses_writes(tmp_path):
    database_path = tmp_path / "local.sqlite3"
    with sqlite3.connect(database_path) as database:
        database.execute("CREATE TABLE example (id INTEGER)")

    script = """
import sys
from pathlib import Path

from django.db import OperationalError, connection
from tableno_mcp.server import configure_django

configure_django(Path(sys.argv[1]))
with connection.cursor() as cursor:
    assert cursor.execute('SELECT COUNT(*) FROM example').fetchone() == (0,)
    try:
        cursor.execute('INSERT INTO example VALUES (1)')
    except OperationalError as error:
        assert 'readonly' in str(error)
    else:
        raise AssertionError('Database write succeeded')
"""
    subprocess.run(  # nosec B603
        [sys.executable, "-c", script, str(database_path)],
        env={**os.environ, "APP_ENV": "local", "DJANGO_SETTINGS_MODULE": "tableno.settings"},
        check=True,
        timeout=30,
    )
