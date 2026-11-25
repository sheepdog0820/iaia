import runpy
from unittest.mock import Mock

import pytest
from django.urls import Resolver404, resolve

from tableno_mcp import http
from tableno_mcp.config import pilot_enrollment
from tableno_mcp.http import create_app, main


def test_pilot_enrollment():
    assert pilot_enrollment(" demo-id ", "1, 2,1") == ("demo-id", frozenset({1, 2}))


@pytest.mark.parametrize(
    ("client_id", "user_ids"),
    [("", "1"), ("https://example.test", "1"), ("a" * 101, "1"), ("demo", ""), ("demo", "0"), ("demo", str(2**63))],
)
def test_invalid_pilot_enrollment(client_id, user_ids):
    with pytest.raises(ValueError, match="TABLENO_MCP"):
        pilot_enrollment(client_id, user_ids)


def test_http_and_oauth_routes_are_unavailable_with_default_local_settings(monkeypatch):
    with pytest.raises(Resolver404):
        resolve("/mcp/oauth/authorize/")
    with pytest.raises(RuntimeError, match="有効になっていません"):
        create_app()
    monkeypatch.setenv("APP_ENV", "aws-prod")
    with pytest.raises(SystemExit, match="開発AWS環境専用"):
        main()


def test_http_command_uses_staging_runtime_and_disables_access_logging(monkeypatch, settings):
    monkeypatch.setenv("APP_ENV", "aws-pre")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tableno.settings_production")
    monkeypatch.setattr("django.setup", Mock())
    run = Mock()
    monkeypatch.setattr("uvicorn.run", run)
    settings.TABLENO_MCP_ENABLED = True
    runpy.run_path(http.__file__, run_name="__main__")
    assert run.call_count == 1
    assert run.call_args.kwargs["port"] == 8000
    assert run.call_args.kwargs["access_log"] is False
