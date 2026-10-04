"""Protect synchronous billing commands without changing Stripe client globals."""

import logging
import os
from contextvars import ContextVar
from functools import wraps

import stripe
from django.core.management.base import CommandError

_protected_command = ContextVar("stripe_protected_command", default=False)
UNEXPECTED_ERROR_SUMMARY = "予期しないエラーで処理を停止しました。秘匿情報を除いて原因を確認してください。"


class StripeCommandLogFilter(logging.Filter):
    def filter(self, record):
        if _protected_command.get():
            # SDK logs include arbitrary response bodies, error messages and POST data.
            record.msg = "Stripe検証コマンドのSDK詳細ログを省略しました。"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


# Install once; the context-local flag leaves unrelated threads/requests unchanged.
logging.getLogger("stripe").addFilter(StripeCommandLogFilter())


def stripe_error_summary(error):
    category = "API"
    for error_type, label in (
        (stripe.AuthenticationError, "認証"),
        (stripe.PermissionError, "権限"),
        (stripe.APIConnectionError, "通信"),
        (stripe.RateLimitError, "呼び出し制限"),
    ):
        if isinstance(error, error_type):
            category = label
            break
    status = error.http_status
    http = f"（HTTP {status}）" if type(status) is int and 100 <= status <= 599 else ""
    return f"Stripeの{category}エラー{http}で停止しました。処理結果を確認するまで再実行しないでください。"


def safe_stripe_command(function):
    @wraps(function)
    def protected(*args, **kwargs):
        # SDK 16 caches STRIPE_LOG at import and also supports stripe.log. Its
        # direct stderr printing bypasses logging filters: fail before any API call.
        if any(
            value in ("debug", "info") for value in (stripe.log, stripe._util.STRIPE_LOG, os.environ.get("STRIPE_LOG"))
        ):
            raise CommandError("Stripeの詳細ログを無効にしてから実行してください（STRIPE_LOG / stripe.log）。")
        token = _protected_command.set(True)
        try:
            return function(*args, **kwargs)
        except stripe.StripeError as error:
            raise CommandError(stripe_error_summary(error)) from None
        except CommandError as error:
            # Preserve existing validation diagnostics, but never render a raw
            # SDK exception that a validation error may have chained from.
            raise CommandError(str(error)) from None
        except Exception:
            raise CommandError(UNEXPECTED_ERROR_SUMMARY) from None
        finally:
            _protected_command.reset(token)

    return protected
