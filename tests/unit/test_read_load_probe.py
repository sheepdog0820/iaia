import argparse
import io
from contextlib import redirect_stdout
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from tests.performance.read_load import measure, run, summarize


class ReadLoadProbeTests(SimpleTestCase):
    def test_redirects_remain_errors_and_tokens_are_not_reported(self):
        with patch("tests.performance.read_load.requests.get") as get:
            get.return_value.__enter__.return_value.status_code = 302
            row = measure("http://localhost:8000", "/api/", "secret-token", 3)
        self.assertEqual(row["status"], 302)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual(get.call_args.kwargs["timeout"], 3)
        self.assertNotIn("secret-token", str(row))
        report = summarize([row])
        self.assertEqual(report["qualification"], "not_evaluated")
        self.assertEqual(report["endpoints"][0]["successes"], 0)

    def test_timeout_does_not_expose_exception_text(self):
        with patch("tests.performance.read_load.requests.get", side_effect=requests.Timeout("secret-token")):
            row = measure("http://localhost:8000", "/api/", "secret-token", 3)
        self.assertEqual(row["status"], 0)
        self.assertEqual(row["error"], "Timeout")
        self.assertNotIn("secret-token", str(row))

    def test_percentiles_use_nearest_rank_and_include_failed_requests(self):
        rows = [{"path": "/api/", "status": 500 if n == 100 else 200, "error": None, "ms": n} for n in range(1, 101)]
        result = summarize(rows)["endpoints"][0]
        self.assertEqual((result["p50_ms"], result["p95_ms"], result["p99_ms"]), (50, 95, 99))
        self.assertEqual(result["successes"], 99)
        self.assertEqual(result["statuses"], {"200": 99, "500": 1})

    @patch.dict("os.environ", {"TABLENO_LOAD_TOKENS": '["first-token","second-token"]'})
    def test_multiple_identities_and_failed_response_exit_status(self):
        args = argparse.Namespace(
            base_url="http://localhost:8000", path=["/api/"], requests=2, concurrency=2, timeout=3
        )
        with patch(
            "tests.performance.read_load.measure", return_value={"path": "/api/", "status": 403, "error": None, "ms": 1}
        ) as call:
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run(args), 1)
        self.assertEqual({c.args[2] for c in call.call_args_list}, {"first-token", "second-token"})
        self.assertNotIn("first-token", output.getvalue())
        self.assertIn('"identities": 2', output.getvalue())

    def test_invalid_origin_or_counts_fail_before_requests(self):
        for base_url, count in (
            ("http://user:secret@localhost", 1),
            ("http://localhost/api/", 1),
            ("http://localhost", 0),
        ):
            with self.subTest(base_url=base_url, count=count):
                args = argparse.Namespace(base_url=base_url, path=["/api/"], requests=count, concurrency=1, timeout=3)
                with patch("tests.performance.read_load.measure") as call:
                    with self.assertRaises(ValueError):
                        run(args)
                    call.assert_not_called()
