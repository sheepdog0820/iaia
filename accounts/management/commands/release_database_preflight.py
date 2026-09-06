"""Collect deployment evidence without changing PostgreSQL or exposing row data."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction


class Command(BaseCommand):
    help = "PostgreSQLの移行履歴・制約・復旧リスクを読み取り専用で確認します（配備可否の判定ではありません）。"
    requires_system_checks = []

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("この検査はPostgreSQL専用です。")
        try:
            if not connection.get_autocommit():
                raise CommandError("既存トランザクション内では実行できません。")
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SET LOCAL lock_timeout = '1s'")
                cursor.execute("SHOW transaction_read_only")
                report = {"format_version": 1, "read_only": cursor.fetchone()[0] == "on"}
                cursor.execute(
                    "SELECT app, name FROM django_migrations WHERE app IN (%s, %s) ORDER BY app, name",
                    ["accounts", "schedules"],
                )
                report["migrations"] = {"accounts": [], "schedules": []}
                for app, name in cursor.fetchall():
                    report["migrations"][app].append(name)
                report["registry_columns"] = sorted(
                    column.name
                    for column in connection.introspection.get_table_description(cursor, "accounts_charactersheet")
                )
                constraints = connection.introspection.get_constraints(cursor, "schedules_sessionparticipantrole")
                report["role_unique_columns"] = sorted(
                    sorted(item["columns"]) for item in constraints.values() if item["unique"]
                )
                cursor.execute(
                    "SELECT COUNT(*) FROM (SELECT participant_id FROM schedules_sessionparticipantrole "
                    "GROUP BY participant_id HAVING COUNT(*) > 1) AS multiple_roles"
                )
                report["participants_with_multiple_roles"] = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT COUNT(*) FROM (SELECT participant_id, role FROM schedules_sessionparticipantrole "
                    "GROUP BY participant_id, role HAVING COUNT(*) > 1) AS duplicate_roles"
                )
                report["duplicate_role_pairs"] = cursor.fetchone()[0]
        except DatabaseError:
            # Do not print SQL, connection details or database exception text.
            raise CommandError(
                "読み取り専用のDB検査に失敗しました。接続・スキーマ・タイムアウトを確認してください。"
            ) from None

        self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
