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

    def test_theme_blocks(self):
        sys.path.insert(0, str(ROOT / "test"))
        import check
        import dtcg
        self.assertEqual(showcase.THEMES, check.THEMES)
        html = showcase.build()
        self.assertEqual(showcase.theme_css("zinc"), "")
        for n in showcase.THEMES[1:]:
            self.assertIn("html.theme-%s{" % n, html)
            self.assertIn("html.theme-%s.dark{" % n, html)
            self.assertEqual(showcase.theme_css(n).count("{"), 2)
        self.assertNotIn("html.theme-zinc", html)
        opts = re.search(r'<select id="ds-theme"[^>]*>(.*?)</select>', html, re.S).group(1)
        found = re.findall(r'<option value="([a-z]+)" title="([^"]*)"[^>]*>([^<]*)</option>', opts)
        self.assertEqual([f[0] for f in found], showcase.THEMES)
        for (n, title, label) in found:
            t = dtcg.load_theme(str(ROOT / "themes" / n))
            self.assertEqual((label, title), (t.name, t.description))


if __name__ == "__main__":
    unittest.main()
