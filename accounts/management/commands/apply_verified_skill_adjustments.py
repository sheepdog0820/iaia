"""Apply only 0068 while verifying every stored skill column in one transaction."""

import hashlib
import json

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

TARGET = ("accounts", "0068_merge_skill_bonus_into_other")
SKILL_QUERIES = {
    "6th": "SELECT * FROM accounts_characterskill6th ORDER BY id",
    "7th": "SELECT * FROM accounts_characterskill7th ORDER BY id",
}


class _GuardRejected(Exception):
    """Only fixed, public-safe rejection messages are carried by this type."""


def _fingerprints(*, expected_merge=False):
    results = {}
    for edition, query in SKILL_QUERIES.items():
        digest = hashlib.sha256()
        count = 0
        with connection.chunked_cursor() as cursor:
            cursor.execute(query)
            columns = [column.name for column in cursor.description]
            while batch := cursor.fetchmany(2000):
                for values in batch:
                    row = dict(zip(columns, values, strict=True))
                    if expected_merge:
                        merged = row["other_points"] + row["bonus_points"]
                        if not -2147483648 <= merged <= 2147483647:
                            raise _GuardRejected("合算後の値が整数範囲を超えるため、適用しません。")
                        row.update(bonus_points=0, other_points=merged)
                    digest.update(json.dumps(row, cls=DjangoJSONEncoder, sort_keys=True).encode("utf-8") + b"\n")
                    count += 1
        results[edition] = (count, digest.hexdigest())
    return results


class Command(BaseCommand):
    help = "承認・非公開バックアップの確認後、0068だけを全行検証付きで適用します。既定では適用しません。"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="承認済みの適用を明示します。")
        parser.add_argument("--expected-host", help="承認済みの接続先ホスト。")
        parser.add_argument("--expected-database", help="承認済みのDB名。")

    def handle(self, *args, **options):
        if not options["apply"] or not options["expected_host"] or not options["expected_database"]:
            raise CommandError(
                "適用と承認済みの接続先を明示してください。読み取りにはrelease_database_preflightを使います。"
            )
        if connection.vendor != "postgresql":
            raise CommandError("この操作はPostgreSQL専用です。")
        if (
            connection.settings_dict["HOST"] != options["expected_host"]
            or connection.settings_dict["NAME"] != options["expected_database"]
        ):
            raise CommandError("承認済みの接続先が一致しません。")
        try:
            if not connection.get_autocommit():
                raise _GuardRejected("既存トランザクション内では実行できません。")
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_database()")
                    if cursor.fetchone()[0] != options["expected_database"]:
                        raise _GuardRejected("承認済みの接続先が一致しません。")
                    cursor.execute("SET LOCAL lock_timeout = '2s'")
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute(
                        "LOCK TABLE django_migrations, accounts_characterskill6th, accounts_characterskill7th "
                        "IN SHARE ROW EXCLUSIVE MODE"
                    )
                executor = MigrationExecutor(connection)
                executor.loader.check_consistent_history(connection)
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                if [(migration.app_label, migration.name, backwards) for migration, backwards in plan] != [
                    (*TARGET, False)
                ]:
                    raise _GuardRejected("未適用の0068だけであることを確認できないため、適用しません。")
                expected = _fingerprints(expected_merge=True)
                executor.migrate([TARGET])
                if _fingerprints() != expected:
                    raise _GuardRejected("移行前後の全行比較が一致しないため、変更を取り消しました。")
                if TARGET not in MigrationRecorder(connection).applied_migrations():
                    raise _GuardRejected("0068の適用記録を確認できないため、変更を取り消しました。")
        except _GuardRejected as exc:
            raise CommandError(str(exc)) from None
        except Exception:
            # Database/migration exceptions may include SQL, connection details or row data.
            raise CommandError(
                "検証付き移行に失敗しました。適用状態を読み取りで再確認し、接続・ロック・スキーマを確認してください。"
            ) from None
        self.stdout.write(
            json.dumps(
                {"status": "applied", "rows_verified": {edition: value[0] for edition, value in expected.items()}}
            )
        )
