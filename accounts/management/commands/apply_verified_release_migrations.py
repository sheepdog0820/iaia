"""Apply the fixed five-migration release plan with transactional verification."""

import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from psycopg import sql

BASE = ("accounts", "0064_preserve_character_descendants")
TARGETS = tuple(
    ("accounts", name)
    for name in (
        "0065_stripe_billing_requests",
        "0066_stripe_invoice_states",
        "0067_billing_email_delivery",
        "0068_merge_skill_bonus_into_other",
        "0069_group_ownership_transfer",
    )
)
MODELS = (
    "CustomUser",
    "Group",
    "GroupMembership",
    "CharacterSkill6th",
    "CharacterSkill7th",
    "PremiumSubscription",
    "PremiumAuditLog",
)
NEW_MODELS = ("StripeBillingRequest", "StripeInvoiceState", "BillingEmailDelivery", "GroupOwnershipTransfer")
TABLES = {name: "accounts_" + name.lower() for name in (*MODELS, *NEW_MODELS)}
TABLES["history"] = "django_migrations"
UNCHANGED = ("CustomUser", "PremiumSubscription", "PremiumAuditLog")


class _Rejected(Exception):
    """Fixed public-safe messages only; never carry database exceptions."""


def _require(condition, message="検証条件が一致しないため、適用を中止しました。"):
    if not condition:
        raise _Rejected(message)


def _hash_rows(name, *, expected=False):
    """Hash complete rows inside PostgreSQL; do not fetch private field values."""
    expression = sql.SQL("to_jsonb(r)")
    if expected and name.startswith("CharacterSkill"):
        expression += sql.SQL(
            " || jsonb_build_object('bonus_points', 0, 'other_points', r.other_points::bigint + r.bonus_points::bigint)"
        )
    elif expected and name == "Group":
        expression += sql.SQL(" || jsonb_build_object('owner_id', r.created_by_id)")
    query = sql.SQL(
        "SELECT r.id, encode(sha256(convert_to(({})::text, 'UTF8')), 'hex') FROM {} r ORDER BY r.id"
    ).format(expression, sql.Identifier(TABLES[name]))
    digest = hashlib.sha256()
    count = 0
    with connection.cursor() as cursor:
        cursor.execute(query)
        while batch := cursor.fetchmany(2000):
            for pk, row_hash in batch:
                digest.update(f"{pk}:{row_hash}\n".encode("ascii"))
                count += 1
    return count, digest.hexdigest()


def _schema(apps, names):
    with connection.cursor() as cursor:
        for name in names:
            cursor.execute(
                "SELECT attname, format_type(atttypid, atttypmod), attnotnull "
                "FROM pg_attribute WHERE attrelid = to_regclass(%s) "
                "AND attnum > 0 AND NOT attisdropped ORDER BY attnum",
                [TABLES[name]],
            )
            actual = {column: (kind, required) for column, kind, required in cursor.fetchall()}
            expected = {
                field.column: (field.db_type(connection).replace("varchar(", "character varying("), not field.null)
                for field in apps.get_model("accounts", name)._meta.local_fields
            }
            _require(actual == expected, "想定した列・型・NULL制約と一致しないため、適用を中止しました。")


def _history():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT r.id, r.app, r.name, encode(sha256(convert_to(to_jsonb(r)::text, 'UTF8')), 'hex') "
            "FROM django_migrations r ORDER BY r.id"
        )
        return {pk: (app, name, row_hash) for pk, app, name, row_hash in cursor.fetchall()}


def _members(*, expected=False):
    expression = sql.SQL("to_jsonb(r)")
    if expected:
        expression = sql.SQL(
            "CASE WHEN r.user_id = g.created_by_id "
            "THEN to_jsonb(r) || jsonb_build_object('role', 'admin') ELSE to_jsonb(r) END"
        )
    query = sql.SQL(
        "SELECT r.id, r.group_id, r.user_id, r.role, "
        "encode(sha256(convert_to(({})::text, 'UTF8')), 'hex') "
        "FROM accounts_groupmembership r JOIN accounts_group g ON g.id = r.group_id ORDER BY r.id"
    ).format(expression)
    with connection.cursor() as cursor:
        cursor.execute(query)
        return {pk: (group, user, role, row_hash) for pk, group, user, role, row_hash in cursor.fetchall()}


def _ownership_before(options):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT g.id, g.created_by_id, u.is_active FROM accounts_group g "
            "LEFT JOIN accounts_customuser u ON u.id = g.created_by_id ORDER BY g.id"
        )
        groups = cursor.fetchall()
        _require(
            all(user is not None and active is True for _, user, active in groups),
            "作成者不明・無効のグループがあるため、適用しません。",
        )
        cursor.execute(
            "SELECT count(*) FROM accounts_groupmembership m "
            "LEFT JOIN accounts_group g ON g.id = m.group_id "
            "LEFT JOIN accounts_customuser u ON u.id = m.user_id "
            "WHERE g.id IS NULL OR u.id IS NULL OR m.role NOT IN ('admin', 'member')"
        )
        _require(cursor.fetchone()[0] == 0)
    members = _members(expected=True)
    pairs = {(row[0], row[1]) for row in members.values()}
    _require(len(pairs) == len(members))
    missing = {(group, user) for group, user, _ in groups} - pairs
    owners = {group: user for group, user, _ in groups}
    promoted = sum(role != "admin" and owners[group] == user for group, user, role, _ in members.values())
    counts = {"groups": len(groups), "memberships_created": len(missing), "memberships_promoted": promoted}
    _require(
        tuple(counts.values())
        == (
            options["expected_group_count"],
            options["expected_owner_membership_create_count"],
            options["expected_owner_membership_promote_count"],
        ),
        "承認された所有者補完件数と一致しないため、適用しません。",
    )
    return members, missing, counts


def _verify_members(before, missing):
    after = _members()
    _require(set(before) <= set(after))
    for pk, old in before.items():
        _require(after[pk][3] == old[3])
    added = [row for pk, row in after.items() if pk not in before]
    _require(len(added) == len(missing))
    _require({(row[0], row[1]) for row in added} == missing)
    _require(all(row[2] == "admin" for row in added))


class Command(BaseCommand):
    help = "承認・直前backup・全writer停止を別途確認し、0065〜0069だけを検証付きで適用します。既定では適用しません。"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--mode", choices=["billing-skills-ownership"])
        parser.add_argument("--expected-host")
        parser.add_argument("--expected-database")
        parser.add_argument("--backup-reference")
        parser.add_argument("--confirm-writers-stopped", action="store_true")
        for name in ("group-count", "owner-membership-create-count", "owner-membership-promote-count"):
            parser.add_argument("--expected-" + name, type=int)

    def handle(self, *args, **options):
        try:
            _require(options["apply"] is True and options["confirm_writers_stopped"] is True)
            _require(options["mode"] == "billing-skills-ownership")
            for key in ("expected_host", "expected_database", "backup_reference"):
                value = options[key]
                _require(isinstance(value, str) and bool(value.strip()) and len(value) <= 256)
            for key in (
                "expected_group_count",
                "expected_owner_membership_create_count",
                "expected_owner_membership_promote_count",
            ):
                _require(type(options[key]) is int and 0 <= options[key] <= 2**63 - 1)
            _require(connection.vendor == "postgresql", "この操作はPostgreSQL18専用です。")
            _require(
                not settings.DEBUG and not connection.force_debug_cursor,
                "SQL詳細ログを無効にしてから実行してください。",
            )
            _require(
                connection.settings_dict["HOST"] == options["expected_host"]
                and connection.settings_dict["NAME"] == options["expected_database"],
                "承認された接続先と一致しません。",
            )
            _require(
                connection.get_autocommit() and not connection.in_atomic_block,
                "既存トランザクション内では実行できません。",
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_schema(), current_schemas(false), pg_my_temp_schema()")
                _require(
                    cursor.fetchone() == ("public", ["public"], 0),
                    "public以外または一時スキーマがある接続では適用できません。新しい専用接続で再確認してください。",
                )
                cursor.execute(
                    "SELECT current_database(), current_setting('server_version_num')::integer / 10000, "
                    "current_setting('default_transaction_read_only'), current_setting('transaction_read_only'), "
                    "(SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid())"
                )
                _require(
                    cursor.fetchone() == (options["expected_database"], 18, "on", "on", True),
                    "接続先・PG18・TLS・起動時READ ONLYを確認できないため、適用しません。",
                )
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ WRITE")
                    cursor.execute("SET LOCAL lock_timeout = '2s'")
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute(
                        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
                            sql.SQL(", ").join(sql.Identifier(TABLES[name]) for name in ("history", *MODELS))
                        )
                    )
                executor = MigrationExecutor(connection)
                executor.loader.check_consistent_history(connection)
                _require(not (set(executor.loader.applied_migrations) - set(executor.loader.disk_migrations)))
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                _require(
                    [(migration.app_label, migration.name, backwards) for migration, backwards in plan]
                    == [(*target, False) for target in TARGETS],
                    "未適用が0065〜0069の5件だけではないため、適用しません。",
                )
                before_apps = executor.loader.project_state([BASE]).apps
                _schema(before_apps, MODELS)
                tables = set(connection.introspection.table_names())
                _require(not any(TABLES[name] in tables for name in NEW_MODELS))
                with connection.cursor() as cursor:
                    for name in ("CharacterSkill6th", "CharacterSkill7th"):
                        cursor.execute(
                            sql.SQL(
                                "SELECT EXISTS (SELECT 1 FROM {} WHERE other_points::bigint + bonus_points::bigint NOT BETWEEN -2147483648 AND 2147483647)"
                            ).format(sql.Identifier(TABLES[name]))
                        )
                        _require(not cursor.fetchone()[0], "技能の合算値が整数範囲を超えるため、適用しません。")
                expected = {
                    name: _hash_rows(name, expected=True)
                    for name in (*UNCHANGED, "Group", "CharacterSkill6th", "CharacterSkill7th")
                }
                before_history = _history()
                members, missing, ownership_counts = _ownership_before(options)
                executor.migrate([TARGETS[-1]])
                _schema(executor.loader.project_state([TARGETS[-1]]).apps, (*MODELS, *NEW_MODELS))
                _require(all(_hash_rows(name) == value for name, value in expected.items()))
                _verify_members(members, missing)
                _require(all(_hash_rows(name)[0] == 0 for name in NEW_MODELS))
                after_history = _history()
                _require(all(after_history.get(pk) == value for pk, value in before_history.items()))
                _require(
                    [value[:2] for pk, value in after_history.items() if pk not in before_history] == list(TARGETS)
                )
                final_executor = MigrationExecutor(connection)
                final_executor.loader.check_consistent_history(connection)
                _require(not final_executor.migration_plan(final_executor.loader.graph.leaf_nodes()))
        except _Rejected as error:
            raise CommandError(str(error)) from None
        except Exception:
            # COMMIT response loss can leave an unknown outcome; do not promise rollback or rerun.
            raise CommandError(
                "検証付き移行に失敗しました。適用状態を読み取りで照合し、確認前に再実行しないでください。"
            ) from None
        self.stdout.write(
            json.dumps(
                {
                    "status": "applied",
                    "applied_migrations": [f"{app}.{name}" for app, name in TARGETS],
                    "ownership_verified": ownership_counts,
                    "rows_verified": {name: value[0] for name, value in expected.items()},
                }
            )
        )
