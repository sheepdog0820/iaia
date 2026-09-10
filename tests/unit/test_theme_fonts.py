import re
import unittest
from pathlib import Path


class ThemeFontTests(unittest.TestCase):
    def test_theme_fonts_are_local_and_have_licenses(self):
        root = Path(__file__).resolve().parents[2]
        theme = root / "static/css/arkham_modern.css"
        css = theme.read_text(encoding="utf-8")
        self.assertNotIn("fonts.googleapis.com", css)
        self.assertNotIn("fonts.gstatic.com", css)
        fonts = root / "static/vendor/theme-fonts/fonts.css"
        font_css = fonts.read_text(encoding="utf-8")
        template = (root / "templates/base.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'public_font' 'theme-fonts/fonts.css' %}", template)
        self.assertNotRegex(font_css, r"https?://")
        urls = re.findall(r"url\(['\"]?([^)'\"]+)", font_css)
        self.assertTrue(urls)
        for url in urls:
            with self.subTest(font=url):
                data = (fonts.parent / url).read_bytes()
                self.assertEqual(data[:4], b"wOF2")
        for family in ("Inter", "Poppins"):
            self.assertIn(f"font-family: '{family}'", font_css)
            license_text = (fonts.parent / f"{family}-OFL.txt").read_text(encoding="utf-8")
            self.assertIn("SIL OPEN FONT LICENSE", license_text)
