from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from daphne.access import AccessLogGenerator

from tableno.server import PrivateAccessServer, private_action_logger


class ServerAccessLoggingTests(TestCase):
    def test_invitation_paths_and_query_values_are_not_written(self):
        for path in (
            "/group-invitations/fixture-token/",
            "/api/group-invitations/fixture-token/join/",
            "/%67roup-invitations/fixture-token/",
            "/login/?next=%2Fgroup-invitations%2Ffixture-token%2F",
        ):
            with self.subTest(path=path):
                stream = StringIO()
                details = {"client": "127.0.0.1", "method": "GET", "path": path, "status": 404, "size": 12}
                private_action_logger(AccessLogGenerator(stream))("http", "complete", details)
                self.assertNotIn("fixture-token", stream.getvalue())
                self.assertNotIn("?next", stream.getvalue())
                self.assertIn("GET /", stream.getvalue())
                self.assertIn("404 12", stream.getvalue())
                self.assertEqual(details["path"], path)

    def test_ordinary_path_and_status_remain_observable(self):
        stream = StringIO()
        private_action_logger(AccessLogGenerator(stream))(
            "http",
            "complete",
            {"client": "127.0.0.1", "method": "POST", "path": "/api/accounts/groups/12/", "status": 403, "size": 20},
        )
        self.assertIn("POST /api/accounts/groups/12/", stream.getvalue())
        self.assertIn("403 20", stream.getvalue())

    def test_control_characters_cannot_forge_log_lines(self):
        stream = StringIO()
        private_action_logger(AccessLogGenerator(stream))(
            "http",
            "complete",
            {"client": "127.0.0.1", "method": "GET", "path": "/bad%0Aforged%0Dentry", "status": 404, "size": 0},
        )
        self.assertEqual(len(stream.getvalue().splitlines()), 1)

    def test_server_wraps_logger_without_changing_other_options(self):
        logger = AccessLogGenerator(StringIO())
        with patch("tableno.server.Server.__init__", return_value=None) as initialize:
            PrivateAccessServer(application="fixture", endpoints=["tcp:8000"], action_logger=logger)
        self.assertEqual(initialize.call_args.kwargs["endpoints"], ["tcp:8000"])
        self.assertIsNot(initialize.call_args.kwargs["action_logger"], logger)
        with patch("tableno.server.Server.__init__", return_value=None) as initialize:
            PrivateAccessServer(application="fixture", endpoints=["tcp:8000"], action_logger=None)
        self.assertIsNone(initialize.call_args.kwargs["action_logger"])

    def test_websocket_logging_also_omits_query(self):
        stream = StringIO()
        private_action_logger(AccessLogGenerator(stream))(
            "websocket", "connected", {"client": "127.0.0.1", "path": "/ws/session/12/?token=fixture-token"}
        )
        self.assertIn("WSCONNECT /ws/session/12/", stream.getvalue())
        self.assertNotIn("fixture-token", stream.getvalue())

    def test_action_without_path_is_forwarded_unchanged(self):
        calls = []
        details = {"status": 200}
        private_action_logger(lambda *args: calls.append(args))("other", "event", details)
        self.assertEqual(calls, [("other", "event", details)])
