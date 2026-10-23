import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build  # noqa: E402
import content  # noqa: E402


class HeadTest(unittest.TestCase):
    def test_no_placeholders_left(self):
        for lang in content.LANGS:
            self.assertNotIn('@@', build.render(lang), lang)

    def test_lang_and_canonical(self):
        for lang in content.LANGS:
            html = build.render(lang)
            self.assertIn(f'<html lang="{lang}"', html)
            self.assertIn(f'<link rel="canonical" href="{build.url(lang)}">', html)

    def test_hreflang_full_set(self):
        for lang in content.LANGS:
            html = build.render(lang)
            for other in content.LANGS:
                self.assertIn(f'<link rel="alternate" hreflang="{other}" href="{build.url(other)}">', html)
            self.assertIn(f'<link rel="alternate" hreflang="x-default" href="{content.SITE}/">', html)

    def test_title_and_og(self):
        for lang in content.LANGS:
            html = build.render(lang)
            self.assertIn(f'<title>{content.T[lang]["title"]}</title>', html)
            self.assertIn(f'<meta property="og:image" content="{content.SITE}/assets/og-{lang}.jpg">', html)
            self.assertIn(f'<meta property="og:locale" content="{content.LOCALE[lang]}">', html)

    def test_no_refresh_and_no_sw(self):
        for lang in content.LANGS:
            html = build.render(lang)
            self.assertNotIn('http-equiv="refresh"', html)
            self.assertNotIn('serviceWorker', html)

    def test_single_game_guard(self):
        saved = content.GAMES[:]
        try:
            content.GAMES.append(dict(saved[0], id='x'))
            with self.assertRaises(SystemExit):
                build.render('ru')
        finally:
            content.GAMES[:] = saved

    def test_urls(self):
        self.assertEqual(build.url('ru'), 'https://gabella.site/')
        self.assertEqual(build.url('en'), 'https://gabella.site/en/')
        self.assertEqual(build.guide('uk'), '/wow/uk/')
        self.assertEqual(build.guide('ru'), '/wow/')


if __name__ == '__main__':
    unittest.main()
