"""Проверка собранного хаба: python tests/check_site.py [--live]
--live: каждая ссылка и ассет /wow/... со страниц хаба отвечает 200 на https://gabella.site"""
import os
import http.client
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build  # noqa: E402
import content as C  # noqa: E402

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def wow_refs(html):
    refs = set(re.findall(r'''(?:href|src)="(/wow/[^"]*)"''', html))
    refs |= set(re.findall(r'url\((/wow/[^)]*)\)', html))
    for srcset in re.findall(r'srcset="([^"]*)"', html):
        refs |= {p.split()[0] for p in srcset.split(',') if p.strip().startswith('/wow/')}
    refs |= set(re.findall(r"fetch\('(/wow/[^']*)'\)", html))
    return refs


def main():
    live = '--live' in sys.argv
    refs = set()
    for lang in C.LANGS:
        html = read(build.OUT[lang])
        check(html == build.render(lang), f'{lang}: собранный файл устарел — запусти python build.py')
        check('@@' not in html, f'{lang}: остались @@')
        check(f'<link rel="canonical" href="{build.url(lang)}">' in html, f'{lang}: canonical')
        for other in C.LANGS + ['x-default']:
            check(f'hreflang="{other}"' in html, f'{lang}: нет hreflang {other}')
        check(os.path.exists(os.path.join(ROOT, 'assets', f'og-{lang}.jpg')), f'{lang}: нет og-{lang}.jpg')
        refs |= wow_refs(html)
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    check(len(ET.fromstring(read('sitemap.xml')).findall('s:url', ns)) == 3, 'sitemap: не 3 URL')
    check(read('robots.txt').count('Sitemap:') == 2, 'robots: не 2 строки Sitemap')
    check(read('CNAME').strip() == 'gabella.site', 'CNAME')
    if live:
        for ref in sorted(refs):
            code = None
            for attempt in range(2):
                try:
                    code = urllib.request.urlopen(urllib.request.Request(C.SITE + ref, method='HEAD'), timeout=20).status
                    break
                except urllib.error.HTTPError as e:
                    code = e.code
                    break
                except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
                    code = f'ошибка сети: {e}'
            check(code == 200, f'live {ref}: {code}')
        print(f'live: проверено {len(refs)} адресов /wow/')
    if fails:
        print('\n'.join('FAIL ' + f for f in fails))
        sys.exit(1)
    print('check_site: OK')


if __name__ == '__main__':
    main()
