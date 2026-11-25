from tableno.settings import INSTALLED_APPS as TABLENO_APPS
from tableno.settings import *  # noqa: F403
from tableno_mcp.config import OAUTH_SETTINGS

ALLOWED_HOSTS = ["stg.tableno.jp", "testserver"]
INSTALLED_APPS = [*TABLENO_APPS, "oauth2_provider"]
TABLENO_MCP_ENABLED = True
TABLENO_MCP_CLIENT_ID = "codex-pilot-test"
TABLENO_MCP_USER_IDS = frozenset({101, 102})
OAUTH2_PROVIDER = OAUTH_SETTINGS
