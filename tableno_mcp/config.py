AWS_PRE_HOST = "stg.tableno.jp"
AWS_PRE_ORIGIN = f"https://{AWS_PRE_HOST}"
MCP_RESOURCE = f"{AWS_PRE_ORIGIN}/mcp"
SESSIONS_READ = "sessions:read"
CHARACTERS_READ = "characters:read"
SCOPES = {
    SESSIONS_READ: "自分が作成・担当・参加する卓の予定を読む",
    CHARACTERS_READ: "自分が所有する探索者シートを読む",
}

OAUTH_SETTINGS = {
    "SCOPES": SCOPES,
    "DEFAULT_SCOPES": list(SCOPES),
    "OIDC_ISS_ENDPOINT": AWS_PRE_ORIGIN,
    "OAUTH2_PROTECTED_RESOURCE_IDENTIFIER": MCP_RESOURCE,
    "OAUTH2_PROTECTED_RESOURCE_AUTHORIZATION_SERVERS": [AWS_PRE_ORIGIN],
    "OAUTH2_VALIDATOR_CLASS": "tableno_mcp.oauth.PilotOAuthValidator",
    "OAUTH2_TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED": ["none"],
    "OAUTH2_RESPONSE_TYPES_SUPPORTED": ["code"],
    "OAUTH2_GRANT_TYPES_SUPPORTED": ["authorization_code", "refresh_token"],
    "DCR_ENABLED": False,
    "CIMD_ENABLED": False,
    "PKCE_REQUIRED": True,
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,  # nosec B105
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,  # nosec B105
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,  # nosec B105
    "COMPLIANT_BCP_RFC9700_REFRESH_TOKEN": True,  # nosec B105
    "AUTHORIZATION_CODE_EXPIRE_SECONDS": 60,
    "ACCESS_TOKEN_EXPIRE_SECONDS": 900,  # nosec B105
    "REFRESH_TOKEN_EXPIRE_SECONDS": 28800,  # nosec B105
    "REFRESH_TOKEN_GRACE_PERIOD_SECONDS": 0,  # nosec B105
    "REFRESH_TOKEN_REUSE_PROTECTION": True,  # nosec B105
}


def pilot_enrollment(client, user_ids):
    client = client.strip()
    if (
        not client
        or len(client) > 100
        or not all(char.isascii() and (char.isalnum() or char in "-_") for char in client)
    ):
        raise ValueError("TABLENO_MCP_CLIENT_ID に登録済みのクライアントIDを設定してください。")
    try:
        users = frozenset(int(value) for value in user_ids.split(","))
    except ValueError:
        raise ValueError("TABLENO_MCP_USER_IDS に数値の利用者IDを指定してください。") from None
    if any(user_id <= 0 or user_id >= 2**63 for user_id in users):
        raise ValueError("TABLENO_MCP_USER_IDS に有効な利用者IDを指定してください。")
    return client, users
