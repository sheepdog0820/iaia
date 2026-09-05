"""Daphne entry point that keeps bearer URLs out of access logs."""

import re
from urllib.parse import unquote

from daphne.cli import CommandLineInterface
from daphne.server import Server

TOKEN_PATHS = re.compile(
    r"(/(?:"
    r"(?:api/)?(?:group-invitations|guest-invitations|session-recruitment)"
    r"|share/(?:sessions|characters|scenarios|stats)"
    r"|calendar/subscribe"
    r"|accounts/(?:confirm-email|password/reset/key)"
    r")/)[^/]+"
)


def private_action_logger(logger):
    def log(protocol, action, details):
        safe_details = details.copy()
        if "path" in safe_details:
            path = unquote(safe_details["path"]).split("?", 1)[0].split("#", 1)[0]
            path = TOKEN_PATHS.sub(r"\1[redacted]", path)
            safe_details["path"] = "".join(character if character.isprintable() else "_" for character in path)
        return logger(protocol, action, safe_details)

    return log


class PrivateAccessServer(Server):
    def __init__(self, **kwargs):
        if kwargs.get("action_logger") is not None:
            kwargs["action_logger"] = private_action_logger(kwargs["action_logger"])
        super().__init__(**kwargs)


class PrivateCommandLineInterface(CommandLineInterface):
    server_class = PrivateAccessServer


if __name__ == "__main__":
    PrivateCommandLineInterface.entrypoint()
