import builtins
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from accounts.background_removal import remove_background


class BackgroundRemovalModelTests(SimpleTestCase):
    def setUp(self):
        self.onnxruntime = SimpleNamespace(disable_telemetry_events=Mock())
        self.module_patch = patch.dict(sys.modules, {"onnxruntime": self.onnxruntime})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.environment_patch = patch.dict(os.environ, {"ORT_DISABLE_TELEMETRY": "0"})
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)

    def test_uses_explicit_u2net_cpu_session_instead_of_library_default(self):
        session = object()
        rembg = SimpleNamespace(new_session=Mock(return_value=session), remove=Mock(return_value=b"png-result"))
        with patch.dict(sys.modules, {"rembg": rembg}):
            result = remove_background(b"source-image")
        rembg.new_session.assert_called_once_with("u2net", providers=["CPUExecutionProvider"])
        rembg.remove.assert_called_once_with(b"source-image", session=session)
        self.assertEqual(result, b"png-result")

    def test_model_initialization_failure_does_not_fall_back_to_default(self):
        rembg = SimpleNamespace(new_session=Mock(side_effect=RuntimeError("model unavailable")), remove=Mock())
        with patch.dict(sys.modules, {"rembg": rembg}):
            with self.assertRaisesRegex(RuntimeError, "model unavailable"):
                remove_background(b"source-image")
        rembg.remove.assert_not_called()

    def test_optout_is_set_before_native_and_rembg_imports(self):
        events = []
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name in {"onnxruntime", "rembg"}:
                self.assertEqual(os.environ.get("ORT_DISABLE_TELEMETRY"), "1")
                events.append(name)
            return original_import(name, *args, **kwargs)

        self.onnxruntime.disable_telemetry_events.side_effect = lambda: events.append("disable")
        session = object()
        rembg = SimpleNamespace(
            new_session=Mock(side_effect=lambda *args, **kwargs: events.append("session") or session),
            remove=Mock(return_value=b"png-result"),
        )
        with patch.dict(sys.modules, {"rembg": rembg}), patch("builtins.__import__", side_effect=guarded_import):
            self.assertIs(builtins.__import__("os"), os)
            self.assertEqual(remove_background(b"source-image"), b"png-result")
        self.assertEqual(events, ["onnxruntime", "disable", "rembg", "session"])
        self.onnxruntime.disable_telemetry_events.assert_called_once_with()

    def test_missing_or_false_environment_cannot_enable_telemetry(self):
        rembg = SimpleNamespace(new_session=Mock(), remove=Mock(return_value=b"png-result"))
        for previous in (None, "", "0", "false", "no", "1"):
            with self.subTest(previous=previous), patch.dict(os.environ), patch.dict(sys.modules, {"rembg": rembg}):
                if previous is None:
                    os.environ.pop("ORT_DISABLE_TELEMETRY", None)
                else:
                    os.environ["ORT_DISABLE_TELEMETRY"] = previous
                self.onnxruntime.disable_telemetry_events.reset_mock()
                self.assertEqual(remove_background(b"source-image"), b"png-result")
                self.assertEqual(os.environ.get("ORT_DISABLE_TELEMETRY"), "1")
                self.onnxruntime.disable_telemetry_events.assert_called_once_with()

    def test_loaded_native_module_is_disabled_again_for_each_request(self):
        rembg = SimpleNamespace(new_session=Mock(), remove=Mock(return_value=b"png-result"))
        with patch.dict(sys.modules, {"rembg": rembg}):
            remove_background(b"first-source")
            os.environ["ORT_DISABLE_TELEMETRY"] = "false"
            remove_background(b"second-source")
        self.assertEqual(self.onnxruntime.disable_telemetry_events.call_count, 2)
        self.assertEqual(rembg.new_session.call_count, 2)
        self.assertEqual(os.environ["ORT_DISABLE_TELEMETRY"], "1")

    def test_telemetry_disable_failure_prevents_model_loading_and_processing(self):
        self.onnxruntime.disable_telemetry_events.side_effect = RuntimeError("telemetry optout unavailable")
        rembg = SimpleNamespace(new_session=Mock(), remove=Mock())
        with patch.dict(sys.modules, {"rembg": rembg}):
            with self.assertRaisesRegex(RuntimeError, "telemetry optout unavailable"):
                remove_background(b"source-image")
        rembg.new_session.assert_not_called()
        rembg.remove.assert_not_called()
