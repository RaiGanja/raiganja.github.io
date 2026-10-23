import json
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

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
            self.assertIn(f'<html lang="{content.HREFLANG[lang]}"', html)
            self.assertIn(f'<link rel="canonical" href="{build.url(lang)}">', html)

    def test_hreflang_full_set(self):
        for lang in content.LANGS:
            html = build.render(lang)
            for other in content.LANGS:
                self.assertIn(f'<link rel="alternate" hreflang="{content.HREFLANG[other]}" href="{build.url(other)}">', html)
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
        self.assertEqual(build.url('pt'), 'https://gabella.site/pt/')
        self.assertEqual(build.OUT['pl'], 'pl/index.html')

    def test_nine_languages_like_guide(self):
        self.assertEqual(content.LANGS, ['ru', 'en', 'uk', 'de', 'fr', 'es', 'pt', 'it', 'pl'])
        self.assertEqual(content.HREFLANG['pt'], 'pt-BR')
        html = build.render('pt')
        self.assertIn('<html lang="pt-BR"', html)
        self.assertIn('<link rel="alternate" hreflang="pt-BR" href="https://gabella.site/pt/">', html)
        self.assertIn('<meta property="og:locale" content="pt_BR">', html)

    def test_every_language_fully_translated(self):
        keys = set(content.T['ru'])
        for lang in content.LANGS:
            self.assertEqual(set(content.T[lang]), keys, lang)
            self.assertTrue(all(v.strip() for v in content.T[lang].values()), lang)
            self.assertIn(lang, content.AUTONYM)
            self.assertIn(lang, content.HINT)
            for s in content.GAMES[0]['sections']:
                self.assertTrue(s['name'].get(lang), (lang, s['path']))
            self.assertIn('%d', content.T[lang]['rel_left'])
            self.assertIn('%h', content.T[lang]['rel_left'])
        for lang in content.LANGS[1:]:
            self.assertNotEqual(content.T[lang]['h1'], content.T['ru']['h1'], lang)


class BodyTest(unittest.TestCase):
    def test_section_links_follow_language(self):
        for lang in content.LANGS:
            html = build.render(lang)
            for s in content.GAMES[0]['sections']:
                self.assertIn(f'href="{build.guide(lang)}{s["path"]}"', html, (lang, s['path']))

    def test_hero_and_countdown(self):
        for lang in content.LANGS:
            html = build.render(lang)
            t = content.T[lang]
            self.assertIn(f'href="{build.guide(lang)}" class="hero-cta"', html)
            self.assertIn(f'data-at="{content.RELEASE}"', html)
            self.assertIn(f'>{t["rel_static"]}</span>', html)
            self.assertIn('/wow/assets/art/hero_dawn-1440.webp', html)

    def test_news_block_hidden_by_default(self):
        html = build.render('en')
        self.assertIn('<section id="news" class="news wrap" hidden', html)
        self.assertIn('href="/wow/en/guides/news/" id="news-all"', html)

    def test_lang_switch(self):
        html = build.render('uk')
        self.assertIn('aria-label="Мова: Українська">UK</button><ul class="langlist" hidden>', html)
        self.assertIn('<a href="/" data-lang="ru" hreflang="ru" lang="ru"><span>Русский</span><small>RU</small></a>', html)
        self.assertIn('<a href="/uk/" data-lang="uk" hreflang="uk" lang="uk" aria-current="page"><span>Українська</span>', html)
        self.assertIn('<a href="/pt/" data-lang="pt" hreflang="pt-BR" lang="pt-BR">Português (Brasil)</a>', html)
        self.assertEqual(html.count('data-lang="pl"'), 2)

    def test_lang_hint_shared_with_guide(self):
        html = build.render('de')
        self.assertIn("'gabella-lang-hint'", html)
        self.assertIn('"pl": ["Ta strona jest dostępna po polsku"', html)

    def test_fonts_from_guide(self):
        html = build.render('ru')
        self.assertIn('url(/wow/assets/fonts/bona-nova-sc-cyrillic.woff2)', html)
        self.assertIn('url(/wow/assets/fonts/golos-text-latin.woff2)', html)
        self.assertIn('url(/wow/assets/fonts/golos-text-latin-ext.woff2)', html)

    def test_disclaimer(self):
        for lang in content.LANGS:
            self.assertIn(build.esc(content.T[lang]['disclaimer']), build.render(lang))

    def test_no_forbidden_words(self):
        for lang in content.LANGS:
            low = build.render(lang).lower()
            for w in ('discord', 'дискорд', ' ai ', ' ии ', 'claude', 'kaeris'):
                self.assertNotIn(w, low, (lang, w))


class JsTest(unittest.TestCase):
    def test_script_reads_news_and_countdown(self):
        html = build.render('ru')
        self.assertIn("fetch('/wow/assets/news.json')", html)
        self.assertIn("getElementById('cd')", html)
        self.assertNotIn('innerHTML', html)

    def test_hidden_attribute_beats_grid_display(self):
        html = build.render('en')
        self.assertIn('[hidden] { display: none !important; }', html)
        self.assertIn(r"/^\d{4}-\d{2}-\d{2}$/.test(n.date)", html)
        self.assertIn("typeof n.title === 'string'", html)


class SeoTest(unittest.TestCase):
    def test_json_ld(self):
        html = build.render('en')
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        data = json.loads(m.group(1))
        self.assertEqual(data['@type'], 'WebSite')
        self.assertEqual(data['url'], 'https://gabella.site/en/')
        self.assertEqual(data['inLanguage'], 'en')
        self.assertEqual(data['hasPart'][0]['url'], 'https://gabella.site/wow/en/')

    def test_sitemap(self):
        root = ET.fromstring(build.sitemap())
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'x': 'http://www.w3.org/1999/xhtml'}
        locs = [u.find('s:loc', ns).text for u in root.findall('s:url', ns)]
        self.assertEqual(locs, [build.url(l) for l in content.LANGS])
        self.assertEqual(locs[3], 'https://gabella.site/de/')
        for u in root.findall('s:url', ns):
            self.assertEqual(len(u.findall('x:link', ns)), len(content.LANGS) + 1)

    def test_robots(self):
        r = build.robots()
        self.assertIn('Sitemap: https://gabella.site/sitemap.xml', r)
        self.assertIn('Sitemap: https://gabella.site/wow/sitemap.xml', r)
        self.assertIn('Allow: /', r)

    def test_no_beacon_without_token(self):
        self.assertNotIn('cloudflareinsights', build.render('ru'))


class OgTest(unittest.TestCase):
    def test_og_files(self):
        from PIL import Image
        for lang in content.LANGS:
            path = os.path.join(build.ROOT, 'assets', f'og-{lang}.jpg')
            self.assertTrue(os.path.exists(path), path)
            with Image.open(path) as im:
                self.assertEqual(im.size, (1200, 630))
                self.assertEqual(im.format, 'JPEG')


if __name__ == '__main__':
    unittest.main()
