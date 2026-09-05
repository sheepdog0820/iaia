from functools import wraps

from django.conf import settings
from django.core.management import CommandError


def local_development_only(handle):
    """Reject shared environments before a bulk seed/reset command touches the DB."""

    @wraps(handle)
    def guarded(*args, **kwargs):
        if (
            not settings.DEBUG
            or settings.APP_ENV not in {"local", "dev", "development"}
            or settings.ENVIRONMENT not in {"local", "development"}
        ):
            raise CommandError("テストデータの作成・削除はDEBUG=Trueのローカル開発環境でのみ実行できます。")
        return handle(*args, **kwargs)

    return guarded
