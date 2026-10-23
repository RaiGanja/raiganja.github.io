"""Сборка хаба gabella.site: python build.py"""
import html as H
import os
import sys

import content as C

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = {'ru': 'index.html', 'en': 'en/index.html', 'uk': 'uk/index.html'}
CF_BEACON_TOKEN = ''


def url(lang):
    return f'{C.SITE}/{C.PREFIX[lang]}'


def guide(lang):
    return C.GAMES[0]['path'] + C.PREFIX[lang]


def esc(s):
    return H.escape(s, quote=True)


def hreflang():
    links = [f'<link rel="alternate" hreflang="{l}" href="{url(l)}">' for l in C.LANGS]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{C.SITE}/">')
    return '\n'.join(links)


def body(lang):
    return f'<h1>{esc(C.T[lang]["h1"])}</h1>'


def css():
    return ''


def render(lang):
    if len(C.GAMES) != 1:
        sys.exit('build.py: в GAMES больше одной игры — сначала нужна сетка игр (спека, «Следующая игра»)')
    t = C.T[lang]
    with open(os.path.join(ROOT, 'index.src.html'), encoding='utf-8') as f:
        page = f.read()
    alt_loc = '\n'.join(f'<meta property="og:locale:alternate" content="{C.LOCALE[l]}">' for l in C.LANGS if l != lang)
    subs = {
        '/*@@CSS@@*/': css(),
        '@@BODY@@': body(lang),
        '@@HREFLANG@@': hreflang(),
        '@@OG_ALTLOC@@': alt_loc,
        '@@LANG@@': lang,
        '@@TITLE@@': esc(t['title']),
        '@@DESC@@': esc(t['desc']),
        '@@URL@@': url(lang),
        '@@OG@@': f'{C.SITE}/assets/og-{lang}.jpg',
        '@@OG_ALT@@': esc(t['og_alt']),
        '@@LOCALE@@': C.LOCALE[lang],
    }
    for k, v in subs.items():
        page = page.replace(k, v)
    if '@@' in page:
        sys.exit(f'build.py: в странице {lang} остались плейсхолдеры @@')
    return page


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def main():
    for lang in C.LANGS:
        write(OUT[lang], render(lang))
    print('hub: собрано', ', '.join(OUT.values()))


if __name__ == '__main__':
    main()
