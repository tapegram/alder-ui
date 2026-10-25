"""The showcase (index.html) covers every demo page, in demo/index.html's order."""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import showcase  # noqa: E402


class ShowcaseTest(unittest.TestCase):
    def test_order_matches_demo_index(self):
        links = re.findall(r'<li><a href="([a-z]+)\.html">', (ROOT / "demo" / "index.html").read_text())
        self.assertEqual(showcase.ORDER, links)

    def test_every_demo_page_has_a_section(self):
        pages = {p.stem for p in (ROOT / "demo").glob("*.html")} - {"index", "parity"}
        self.assertEqual(set(showcase.ORDER), pages)
        html = showcase.build()
        for n in showcase.ORDER:
            self.assertIn('<section id="%s" class="ds-sec">' % n, html)


if __name__ == "__main__":
    unittest.main()
