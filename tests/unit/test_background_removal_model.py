import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from accounts.background_removal import remove_background


class BackgroundRemovalModelTests(SimpleTestCase):
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
