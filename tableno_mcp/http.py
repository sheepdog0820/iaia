import hashlib
import logging
import os

import django
import uvicorn
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.responses import Response

from tableno.runtime_env import configure_runtime_environment
from tableno_mcp.config import AWS_PRE_HOST, AWS_PRE_ORIGIN, MCP_RESOURCE

logger = logging.getLogger(__name__)


class PilotTokenVerifier:
    @sync_to_async
    def verify_token(self, token):
        from oauth2_provider.models import get_access_token_model

        from tableno_mcp.oauth import pilot_client, pilot_user

        checksum = hashlib.sha256(token.encode()).hexdigest()
        try:
            access = (
                get_access_token_model()
                .objects.select_related("user", "application")
                .filter(token_checksum=checksum, resource=[MCP_RESOURCE])
                .first()
            )
            if (
                access
                and access.is_valid()
                and access.application
                and pilot_client(access.application)
                and pilot_user(access.user)
            ):
                return AccessToken(
                    token=token,
                    client_id=access.application.client_id,
                    subject=str(access.user_id),
                    scopes=access.scope.split(),
                    expires_at=int(access.expires.timestamp()),
                    resource=MCP_RESOURCE,
                )
        except DatabaseError:
            logger.warning("MCPのトークンを検証できませんでした。")
        finally:
            connection.close()
        return None


@sync_to_async
def read_for_user(user_id, operation, **arguments):
    try:
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
            user = (
                get_user_model()
                .objects.filter(pk=user_id, pk__in=settings.TABLENO_MCP_USER_IDS, is_active=True)
                .only("id")
                .first()
            )
            if user is None:
                raise ToolError("このアカウントではタブレノMCPを利用できません。")
            return operation(user, **arguments)
    except DatabaseError:
        raise ToolError("タブレノからデータを読み取れませんでした。") from None
    finally:
        connection.close()


async def read_authorized(operation, scope, **arguments):
    token = get_access_token()
    if token is None or token.subject is None or scope not in token.scopes:
        raise ToolError("この機能の閲覧が許可されていません。")
    return await read_for_user(token.subject, operation, **arguments)


def create_app():
    if not settings.TABLENO_MCP_ENABLED:
        raise RuntimeError("開発AWS環境でタブレノMCPが有効になっていません。")

    from tableno_mcp.tools import build_tools

    server = build_tools(
        read_authorized,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        max_request_body_size=64 * 1024,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(AWS_PRE_ORIGIN),
            resource_server_url=AnyHttpUrl(MCP_RESOURCE),
            validate_token_resource=True,
        ),
        token_verifier=PilotTokenVerifier(),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[AWS_PRE_HOST],
            allowed_origins=[AWS_PRE_ORIGIN],
        ),
    )

    @server.custom_route("/health/live", methods=["GET"])
    async def health(request):
        return Response("ok", media_type="text/plain")

    return server.streamable_http_app()


def main():
    app_env = configure_runtime_environment()
    if app_env != "aws-pre" or os.environ["DJANGO_SETTINGS_MODULE"] != "tableno.settings_production":
        raise SystemExit("HTTP版のタブレノMCPは開発AWS環境専用です。")
    django.setup()
    # The ECS task receives traffic from the ALB on its private interface.
    uvicorn.run(
        create_app(),
        host="0.0.0.0",  # nosec B104
        port=8000,
        access_log=False,
        proxy_headers=False,
        limit_concurrency=64,
    )


if __name__ == "__main__":
    main()
