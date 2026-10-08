"""Rollback independent TestCase scenarios, never real-commit worker tests."""

from contextlib import contextmanager

from django.db import connection, transaction


@contextmanager
def rollback_google_subcase():
    # TestCase already suppresses on_commit. TransactionTestCase callers must
    # use fresh fixtures instead; wrapping them would hide actual dispatch.
    if not connection.in_atomic_block:
        raise RuntimeError("独立ケースのrollbackはTestCase内だけで使用してください。")
    with transaction.atomic():
        try:
            yield
        finally:
            transaction.set_rollback(True)
