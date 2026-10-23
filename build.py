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


JS = '''
(() => {
  const cd = document.getElementById('cd');
  const ms = new Date(cd.dataset.at) - new Date();
  if (ms > 0) {
    const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / 36e5);
    cd.textContent = cd.dataset.left.replace('%d', d).replace('%h', h);
  } else cd.textContent = cd.dataset.done;

  const box = document.getElementById('news');
  fetch('/wow/assets/news.json').then(r => r.ok ? r.json() : []).then(list => {
    if (!Array.isArray(list) || !list.length) return;
    const ul = box.querySelector('ul');
    list.filter(n => n && n.date && n.title && /^https:/.test(n.url))
      .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5).forEach(n => {
        const li = document.createElement('li'), t = document.createElement('time'), a = document.createElement('a');
        t.dateTime = n.date; t.textContent = n.date.split('-').reverse().join('.');
        a.href = n.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = n.title;
        li.append(t, a); ul.append(li);
      });
    if (ul.children.length) box.hidden = false;
  }).catch(() => {});
})();
'''


def js():
    return JS


ART = '/wow/assets/art/'
HEROES = {'hero_dawn', 'hero_campfire'}


def pic(art, alt='', lazy=True):
    """Плитка: портрет 360 или шапка 960 из гида."""
    w, h = (960, 536) if art in HEROES else (360, 482)
    load = ' loading="lazy"' if lazy else ''
    return (f'<picture><source type="image/avif" srcset="{ART}{art}-{w}.avif">'
            f'<img src="{ART}{art}-{w}.webp" alt="{esc(alt)}" width="{w}" height="{h}"{load} decoding="async"></picture>')


def hero_pic(art):
    m = f'{ART}{art}-m-600.%s 600w, {ART}{art}-m-1000.%s 1000w'
    d = f'{ART}{art}-960.%s 960w, {ART}{art}-1440.%s 1440w, {ART}{art}-1920.%s 1920w'
    return ('<picture class="hero-art">'
            f'<source media="(max-width: 719px)" type="image/avif" srcset="{m % ("avif", "avif")}" sizes="100vw">'
            f'<source media="(max-width: 719px)" type="image/webp" srcset="{m % ("webp", "webp")}" sizes="100vw">'
            f'<source type="image/avif" srcset="{d % ("avif", "avif", "avif")}" sizes="(min-width: 1272px) 1240px, 100vw">'
            f'<source type="image/webp" srcset="{d % ("webp", "webp", "webp")}" sizes="(min-width: 1272px) 1240px, 100vw">'
            f'<img src="{ART}{art}-1440.webp" alt="" width="1440" height="804" fetchpriority="high" decoding="async"></picture>')


def lang_switch(lang):
    out = []
    for l in C.LANGS:
        cur = ' aria-current="page"' if l == lang else ''
        out.append(f'<a href="/{C.PREFIX[l]}" hreflang="{l}" lang="{l}"{cur}>{l.upper()}</a>')
    return f'<nav class="langs" aria-label="{esc(C.T[lang]["lang_nav"])}">' + ''.join(out) + '</nav>'


def tiles(lang):
    g = C.GAMES[0]
    out = []
    for s in g['sections']:
        name = esc(s['name'][lang])
        out.append(f'<a class="tile" href="{guide(lang)}{s["path"]}">{pic(s["art"])}<b>{name}</b></a>')
    return ''.join(out)


def body(lang):
    t, g = C.T[lang], C.GAMES[0]
    return f'''<header class="top wrap">
<a class="logo" href="/{C.PREFIX[lang]}"><img src="/wow/assets/icons/icon-192.png" alt="" width="32" height="32"><span>Gabella</span></a>
{lang_switch(lang)}
</header>
<main>
<div class="intro wrap"><h1>{esc(t["h1"])}</h1><p>{esc(t["lead"])}</p></div>
<section class="hero wrap" aria-labelledby="g-{g["id"]}">
{hero_pic(g["art"])}
<div class="hero-txt">
<span class="new">{esc(t["new"])}</span>
<h2 id="g-{g["id"]}">{esc(g["name"][lang])}</h2>
<span id="cd" class="cd" data-at="{C.RELEASE}" data-left="{esc(t["rel_left"])}" data-done="{esc(t["rel_done"])}">{esc(t["rel_static"])}</span>
<a href="{guide(lang)}" class="hero-cta">{esc(t["open"])}</a>
</div>
</section>
<section class="sections wrap" aria-labelledby="sec-h">
<h2 id="sec-h">{esc(t["sections_h"])}</h2>
<div class="frame"><div class="tiles">{tiles(lang)}</div></div>
</section>
<section id="news" class="news wrap" hidden aria-labelledby="news-h">
<h2 id="news-h">{esc(t["news_h"])}</h2>
<div class="frame"><ul></ul><a href="{guide(lang)}guides/news/" id="news-all">{esc(t["news_all"])} →</a></div>
</section>
</main>
<footer class="foot wrap">
<p>© Gabella · <a href="{guide(lang)}">{esc(t["guide_link"])}</a></p>
{lang_switch(lang)}
<p class="tm">{esc(t["disclaimer"])}</p>
</footer>'''


FONTS = '/wow/assets/fonts/'
CYR = 'U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116'
LAT = ('U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, '
       'U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD')
LATX = ('U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, '
        'U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF')


def font_faces():
    rows = [('Bona Nova SC', '400 700', 'bona-nova-sc-cyrillic', CYR),
            ('Bona Nova SC', '400 700', 'bona-nova-sc-latin-ext', LATX),
            ('Bona Nova SC', '400 700', 'bona-nova-sc-latin', LAT),
            ('Golos Text', '400 600', 'golos-text-cyrillic', CYR),
            ('Golos Text', '400 600', 'golos-text-latin', LAT)]
    return '\n'.join(f'@font-face {{ font-family: "{f}"; font-style: normal; font-weight: {w}; font-display: swap; '
                     f'src: url({FONTS}{n}.woff2) format("woff2"); unicode-range: {r}; }}' for f, w, n, r in rows)


CSS = '''
:root { --bg: #0a0b0d; --fg: #ece6d8; --muted: #a3a7ae; --gold: #c9a54a; --gold-2: #e0c27a; --gold-ink: #15110a;
  --panel: rgba(15,18,26,.9); --pline: rgba(255,255,255,.08); --wrap: 1240px; --ease: cubic-bezier(.2,.7,.2,1);
  --font-display: "Bona Nova SC", Georgia, "Times New Roman", serif; --font-body: "Golos Text", "Segoe UI", system-ui, sans-serif;
  color-scheme: dark; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.55 var(--font-body); -webkit-font-smoothing: antialiased; }
a { color: inherit; }
img { display: block; max-width: 100%; }
h1, h2 { font-family: var(--font-display); font-weight: 700; letter-spacing: .03em; line-height: 1.1; margin: 0; text-wrap: balance; }
.wrap { width: min(var(--wrap), 100% - 32px); margin-inline: auto; }
.top { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 0; }
.logo { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; font: 700 1.35rem/1 var(--font-display); letter-spacing: .04em; color: var(--gold); }
.logo img { border-radius: 8px; }
.langs { display: flex; gap: 4px; }
.langs a { padding: 6px 10px; border-radius: 6px; text-decoration: none; font-size: .88rem; color: var(--muted); }
.langs a:hover { color: var(--fg); }
.langs a[aria-current] { color: var(--gold-ink); background: var(--gold); }
.intro { padding: 28px 0 22px; display: grid; gap: 8px; }
.intro h1 { font-size: clamp(2rem, 5vw, 3.4rem); }
.intro p { margin: 0; color: var(--muted); font-size: 1.08rem; max-width: 60ch; }
.hero { position: relative; isolation: isolate; overflow: hidden; border-radius: 10px; border: 1px solid var(--pline);
  min-height: clamp(360px, 42vw, 520px); display: grid; align-items: end; }
.hero-art, .hero-art img { position: absolute; inset: 0; width: 100%; height: 100%; }
.hero-art { z-index: -2; }
.hero-art img { object-fit: cover; object-position: 50% 40%; }
.hero::after { content: ""; position: absolute; inset: 0; z-index: -1;
  background: linear-gradient(180deg, rgba(10,11,13,0) 30%, rgba(10,11,13,.55) 60%, rgba(10,11,13,.95) 100%); }
.hero-txt { padding: clamp(20px, 4vw, 40px); display: grid; gap: 10px; justify-items: start; }
.new { color: var(--gold-2); font-weight: 600; font-size: .95rem; }
.hero h2 { font-size: clamp(2.2rem, 6vw, 4.2rem); text-shadow: 0 2px 18px rgba(0,0,0,.6); }
.cd { font: 700 1.25rem/1.2 var(--font-display); letter-spacing: .03em; font-variant-numeric: tabular-nums; }
.hero-cta { margin-top: 6px; padding: 12px 22px; border-radius: 8px; background: var(--gold); color: var(--gold-ink);
  font-weight: 600; text-decoration: none; transition: background .2s; }
.hero-cta:hover { background: var(--gold-2); }
.sections, .news { margin-top: 44px; display: grid; gap: 16px; }
.sections h2, .news h2 { font-size: clamp(1.5rem, 3vw, 2.1rem); }
.frame { border: 1px solid var(--pline); border-radius: 10px; background: var(--panel); box-shadow: 0 18px 48px rgba(0,0,0,.35); min-width: 0; }
.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; padding: 14px; }
.tile { position: relative; isolation: isolate; overflow: hidden; height: 168px; padding: 0 14px 14px; display: grid; align-content: end;
  border: 1px solid rgba(255,255,255,.1); border-radius: 7px; background: #0b0d12; color: #f3efe6; text-decoration: none; transition: border-color .2s; }
.tile picture, .tile img { position: absolute; inset: 0; width: 100%; height: 100%; }
.tile picture { z-index: -2; }
.tile img { object-fit: cover; object-position: 50% 22%; filter: saturate(.85) brightness(.78); transition: filter .3s, transform .6s var(--ease); }
.tile::after { content: ""; position: absolute; inset: 0; z-index: -1; background: linear-gradient(180deg, rgba(6,8,12,0) 25%, rgba(6,8,12,.9) 100%); }
.tile:hover { border-color: rgba(224,194,122,.6); }
.tile:hover img { filter: none; transform: scale(1.04); }
.tile b { font: 700 1.12rem/1.2 var(--font-display); letter-spacing: .03em; text-shadow: 0 1px 8px rgba(0,0,0,.7); }
.news ul { list-style: none; margin: 0; padding: 6px 18px; }
.news li { display: grid; grid-template-columns: 6.5em 1fr; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--pline); }
.news time { color: var(--muted); font-variant-numeric: tabular-nums; }
.news li a { text-decoration: none; }
.news li a:hover { color: var(--gold-2); }
#news-all { display: inline-block; margin: 12px 18px 16px; color: var(--gold); text-decoration: none; font-weight: 600; }
.foot { margin-top: 64px; padding: 24px 0 40px; border-top: 1px solid var(--pline); display: grid; gap: 10px; color: var(--muted); font-size: .92rem; }
.foot p { margin: 0; }
.foot .tm { font-size: .8rem; opacity: .8; }
:focus-visible { outline: 2px solid var(--gold-2); outline-offset: 2px; }
@media (max-width: 1023px) {
  .tiles { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: 46%; overflow-x: auto; scroll-snap-type: x mandatory; overscroll-behavior-x: contain; }
  .tile { scroll-snap-align: start; }
}
@media (max-width: 719px) {
  .tiles { grid-auto-columns: 68%; }
  .hero { min-height: 440px; }
  .news li { grid-template-columns: none; gap: 2px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
'''


def css():
    return font_faces() + CSS


def render(lang):
    if len(C.GAMES) != 1:
        sys.exit('build.py: в GAMES больше одной игры — сначала нужна сетка игр (спека, «Следующая игра»)')
    t = C.T[lang]
    with open(os.path.join(ROOT, 'index.src.html'), encoding='utf-8') as f:
        page = f.read()
    alt_loc = '\n'.join(f'<meta property="og:locale:alternate" content="{C.LOCALE[l]}">' for l in C.LANGS if l != lang)
    subs = {
        '/*@@JS@@*/': js(),
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
