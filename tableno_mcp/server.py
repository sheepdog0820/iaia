import argparse
import os
import sys
from pathlib import Path

import django
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction


class LocalSetupError(Exception):
    pass


def configure_django(database_path: Path):
    if (
        os.environ.get("APP_ENV", "local").strip().lower() != "local"
        or os.environ.get("DJANGO_SETTINGS_MODULE", "tableno.settings") != "tableno.settings"
    ):
        raise LocalSetupError("MCPはAPP_ENV=localのタブレノで利用してください。")
    path = database_path.expanduser().resolve()
    if not path.is_file():
        raise LocalSetupError("指定されたローカルSQLiteファイルが見つかりません。")

    # This process does not load deployment configuration or use Django's signing and login features.
    os.environ.update(
        DJANGO_SETTINGS_MODULE="tableno.settings",
        ENV_FILE="",
        AWS_SECRETS_FILE="",
        AWS_SECRETS_JSON="",
        DB_ENGINE="sqlite",
        DEBUG="0",
        SECRET_KEY="tableno-local-mcp-unused-for-signing",  # nosec B106
    )
    settings.DATABASES["default"]["NAME"] = f"{path.as_uri()}?mode=ro"
    django.setup()


def build_server(username):
    from mcp.server.fastmcp.exceptions import ToolError

    from tableno_mcp.tools import build_tools

    active_users = get_user_model().objects.filter(username=username, is_active=True).only("id")
    try:
        user_id = active_users.values_list("pk", flat=True).first()
    finally:
        connection.close()
    if user_id is None:
        raise LocalSetupError("指定されたローカルアカウントが無効か、見つかりません。")

    @sync_to_async
    def read(operation, _scope, **arguments):
        try:
            with transaction.atomic():
                user = active_users.filter(pk=user_id).first()
                if user is None:
                    raise ToolError("設定済みのローカルアカウントが無効か、見つかりません。")
                return operation(user, **arguments)
        except DatabaseError:
            raise ToolError("ローカルSQLiteから読み取れません。タブレノとDBの状態を確認してください。") from None
        finally:
            connection.close()

    return build_tools(read)


def main():
    parser = argparse.ArgumentParser(description="タブレノのローカル読み取り専用MCPを起動します。")
    parser.add_argument("--database", type=Path, required=True, help="ローカルのSQLiteファイル")
    parser.add_argument("--username", required=True, help="参照する本人のローカルユーザー名")
    args = parser.parse_args()
    try:
        configure_django(args.database)
        server = build_server(args.username)
    except LocalSetupError as error:
        parser.exit(1, f"{error}\n")
    except DatabaseError:
        parser.exit(1, "ローカルSQLiteからアカウントを読み取れません。\n")
    server.run(transport="stdio")


if __name__ == "__main__":
    sys.exit(main())
