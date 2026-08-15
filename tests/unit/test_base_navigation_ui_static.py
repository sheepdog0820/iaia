import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class BaseNavigationUiStaticTests(SimpleTestCase):
    def test_user_dropdown_opens_toward_viewport(self):
        template = (Path(settings.BASE_DIR) / "templates/base.html").read_text(encoding="utf-8")

        user_menu = re.search(
            r'id="navbarDropdown".*?<ul class="([^"]*dropdown-menu[^"]*)">',
            template,
            re.DOTALL,
        )

        self.assertIsNotNone(user_menu)
        self.assertIn("dropdown-menu-end", user_menu.group(1).split())
