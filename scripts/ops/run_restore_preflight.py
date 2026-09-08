"""Launch the existing read-only probe without loading application settings."""

import io
import json
import os
import re
import sys


def validated_database(env):
    required = (
        "DB_HOST",
        "RESTORE_EXPECTED_HOST",
        "RESTORE_SOURCE_HOST",
        "DB_NAME",
        "RESTORE_EXPECTED_DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_PORT",
    )
    if any(not env.get(key) for key in required):
        raise ValueError("Missing restore configuration")
    host = env["DB_HOST"]
    if (
        host != env["RESTORE_EXPECTED_HOST"]
        or host.casefold() == env["RESTORE_SOURCE_HOST"].casefold().rstrip(".")
        or not re.fullmatch(r"tableno-restore-drill-[a-z0-9-]+\.[a-z0-9]+\.ap-northeast-1\.rds\.amazonaws\.com", host)
        or env["DB_NAME"] != env["RESTORE_EXPECTED_DB_NAME"]
        or env["DB_PORT"] != "5432"
    ):
        raise ValueError("Restore target mismatch")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": host,
        "PORT": "5432",
        "NAME": env["DB_NAME"],
        "USER": env["DB_USER"],
        "PASSWORD": env["DB_PASSWORD"],
        "OPTIONS": {"sslmode": "require", "connect_timeout": 5},
    }


def run_probe(database):
    import django
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection

    from accounts.management.commands.release_database_preflight import Command

    # No project settings, installed apps, signals, email, cache, S3 or external clients.
    settings.configure(DATABASES={"default": database}, INSTALLED_APPS=[], USE_TZ=True)
    django.setup()
    try:
        if connection.pg_version // 10000 != 18:
            raise ValueError("Unexpected database version")
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != database["NAME"]:
                raise ValueError("Unexpected database name")
        output = io.StringIO()
        call_command(Command(), stdout=output)
        report = json.loads(output.getvalue())
        if report["read_only"] is not True:
            raise ValueError("Read-only transaction not confirmed")
        report["server_major"] = 18
        return report
    finally:
        connection.close()


def main(env=None):
    try:
        report = run_probe(validated_database(os.environ if env is None else env))
    except Exception:
        # Connection and database exceptions can contain credentials and user data.
        print("復元DBの検査に失敗しました。接続先・設定・検証ログを管理者が確認してください。", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
