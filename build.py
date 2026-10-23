"""Сборка хаба gabella.site: python build.py"""
import html as H
import json
import os
import re
import sys

import content as C

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = {l: f'{C.PREFIX[l]}index.html' for l in C.LANGS}
OUT_404 = {l: f'{C.PREFIX[l]}404.html' for l in C.LANGS}
CF_BEACON_TOKEN = 'ee1d216e690040389063e8d72384c2c7'   # Cloudflare Web Analytics сайта gabella.site — тот же, что в гиде (wfpages/seo.py)

# Подтверждение прав в поисковиках (Яндекс не используем — решение 23.10): значение content= из метатега кабинета; пусто — метатег не вставляется.
# Те же значения — в гиде (wfpages/seo.py VERIFY). Bing подключён импортом из Search Console, msvalidate.01 — запасной путь.
VERIFY = {
    'msvalidate.01': '',         # Bing Webmaster Tools → Settings → Verification → HTML Meta Tag
}
# IndexNow: ключ публичный по замыслу протокола; файл <ключ>.txt в корне домена подтверждает его для всего gabella.site.
# Отправка — tools/indexnow.py (.github/workflows/indexnow.yml), тот же ключ в гиде wfpages/tools/indexnow.py.
INDEXNOW_KEY = '99c3c672b2e834d250d8c7b1dc0c34b9'


def url(lang):
    return f'{C.SITE}/{C.PREFIX[lang]}'


def guide(lang):
    return C.GAMES[0]['path'] + C.PREFIX[lang]


def esc(s):
    return H.escape(s, quote=True)


def hreflang():
    links = [f'<link rel="alternate" hreflang="{C.HREFLANG[l]}" href="{url(l)}">' for l in C.LANGS]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{C.SITE}/">')
    return '\n'.join(links)


JS = r'''
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
    list.filter(n => n && typeof n.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(n.date) && typeof n.title === 'string' && n.title && typeof n.url === 'string' && /^https:/.test(n.url))
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

# Выбор языка и подсказка по языку браузера — как в гиде; ключ localStorage общий, закрыл на хабе — не всплывёт и в гиде
LANG_JS = r'''
(() => {
  const KEY = 'gabella-lang-hint', store = l => { try { localStorage.setItem(KEY, '1'); if (l) localStorage.setItem('gabella-lang', l); } catch (e) {} };
  document.querySelectorAll('.langlist a, .langfoot a').forEach(a => a.addEventListener('click', () => store(a.dataset.lang)));
  const sel = document.querySelector('.langsel'), btn = sel.querySelector('.langbtn'), list = sel.querySelector('.langlist');
  const links = [...list.querySelectorAll('a')];
  const shut = focus => { if (list.hidden) return; list.hidden = true; btn.setAttribute('aria-expanded', 'false'); if (focus) btn.focus(); };
  btn.addEventListener('click', e => {
    e.stopPropagation();
    list.hidden = !list.hidden; btn.setAttribute('aria-expanded', String(!list.hidden));
    if (!list.hidden) (list.querySelector('[aria-current]') || links[0]).focus();
  });
  document.addEventListener('click', e => { if (!sel.contains(e.target)) shut(); });
  sel.addEventListener('keydown', e => {
    if (e.key === 'Escape') return shut(true);
    const i = links.indexOf(document.activeElement);
    if (i < 0 || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const n = e.key === 'Home' ? 0 : e.key === 'End' ? links.length - 1 : (i + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
    links[n].focus();
  });
  sel.addEventListener('focusout', e => { if (!sel.contains(e.relatedTarget)) shut(); });

  let seen = '1';
  try { seen = localStorage.getItem(KEY); } catch (e) {}
  if (seen) return;
  const H = @@HINT@@, cur = document.documentElement.lang.split('-')[0];
  const want = (navigator.languages || [navigator.language]).map(x => String(x || '').toLowerCase().split('-')[0]).find(x => x in H);
  const to = want && want !== cur && list.querySelector(`a[data-lang="${want}"]`);
  if (!to) return;
  const bar = document.createElement('div'), span = document.createElement('span'), a = document.createElement('a'), x = document.createElement('button');
  bar.className = 'langhint'; bar.lang = to.lang; bar.setAttribute('role', 'status');
  span.textContent = H[want][0];
  a.href = to.getAttribute('href'); a.hreflang = to.hreflang; a.textContent = H[want][1]; a.addEventListener('click', () => store(want));
  x.type = 'button'; x.setAttribute('aria-label', H[want][2]); x.textContent = '×';
  x.addEventListener('click', () => { store(); bar.remove(); });
  bar.append(span, a, x);
  document.body.append(bar);
})();
'''

# Корень / (русский): язык посетителя до отрисовки — как в гиде (build.py гида, AUTO_JS). Сохранённый выбор gabella-lang
# (меню языков здесь и в гиде) главнее; иначе языки браузера, остальным английский. Боты, переходы из поиска
# и со своего сайта остаются на русской странице — поисковики индексируют её как есть.
AUTO_JS = r'''<script>
(function () {
  if (/bot|crawl|spider|slurp|lighthouse|headless|google-|preview/i.test(navigator.userAgent) || navigator.webdriver) return;
  var P = @@PATHS@@, A = { be: 'ru', kk: 'ru' }, w = null, r = document.referrer;
  try { w = localStorage.getItem('gabella-lang'); } catch (e) {}
  if (!(w in P)) {
    if (r && (r.indexOf(location.origin + '/') === 0 || /^https?:\/\/([^\/]*\.)?(google|bing|yandex|ya|duckduckgo|yahoo|baidu|ecosia|naver|qwant|seznam)\.[^\/]+\//.test(r))) return;
    var L = navigator.languages || [navigator.language];
    for (var i = 0; i < L.length && !w; i++) { var b = String(L[i] || '').toLowerCase().split('-')[0]; b = A[b] || b; if (b in P) w = b; }
    w = w || 'en';
  }
  if (w !== 'ru') location.replace(P[w] + location.search + location.hash);
})();
</script>
'''


def auto_lang():
    return AUTO_JS.replace('@@PATHS@@', json.dumps({l: '/' + C.PREFIX[l] for l in C.LANGS}))


def js():
    hint = json.dumps({l: C.HINT[l] for l in C.LANGS}, ensure_ascii=False)
    return JS + LANG_JS.replace('@@HINT@@', hint)


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


def lang_link(l, lang, inner):
    cur = ' aria-current="page"' if l == lang else ''
    hl = C.HREFLANG[l]
    return f'<a href="/{C.PREFIX[l]}" data-lang="{l}" hreflang="{hl}" lang="{hl}"{cur}>{inner}</a>'


def lang_switch(lang):
    """Шапка: кнопка с кодом языка и выпадающий список самоназваний (как в гиде)."""
    label = esc(C.T[lang]['lang_nav'])
    items = ''.join(f'<li>{lang_link(l, lang, f"<span>{C.AUTONYM[l]}</span><small>{l.upper()}</small>")}</li>' for l in C.LANGS)
    return (f'<div class="langsel"><button type="button" class="langbtn" aria-haspopup="true" aria-expanded="false" '
            f'aria-label="{label}: {C.AUTONYM[lang]}">{lang.upper()}</button><ul class="langlist" hidden>{items}</ul></div>')


def lang_foot(lang):
    """Подвал: все языки строкой — видны без JS и поисковикам."""
    links = ''.join(lang_link(l, lang, C.AUTONYM[l]) for l in C.LANGS)
    return f'<nav class="langfoot" aria-label="{esc(C.T[lang]["lang_nav"])}">{links}</nav>'


def tiles(lang):
    g = C.GAMES[0]
    out = []
    for s in g['sections']:
        name = esc(s['name'][lang])
        out.append(f'<a class="tile" href="{guide(lang)}{s["path"]}">{pic(s["art"])}<b>{name}</b></a>')
    return ''.join(out)


def body(lang, nf=False):
    t, g = C.T[lang], C.GAMES[0]
    h1, lead = (t['nf_h'], t['nf_lead']) if nf else (t['h1'], t['lead'])
    return f'''<header class="top wrap">
<a class="logo" href="/{C.PREFIX[lang]}"><img src="/wow/assets/icons/icon-192.png" alt="" width="32" height="32"><span>Gabella</span></a>
{lang_switch(lang)}
</header>
<main>
<div class="intro wrap"><h1>{esc(h1)}</h1><p>{esc(lead)}</p></div>
<section class="hero wrap" aria-labelledby="g-{g["id"]}">
{hero_pic(g["art"])}
<div class="hero-txt">
<h2 id="g-{g["id"]}">{esc(g["name"][lang])}</h2>
<p class="meta"><span class="new">{esc(t["new"])}</span><span aria-hidden="true" class="dot">·</span><span id="cd" class="cd" data-at="{C.RELEASE}" data-left="{esc(t["rel_left"])}" data-done="{esc(t["rel_done"])}">{esc(t["rel_static"])}</span></p>
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
{lang_foot(lang)}
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
            ('Golos Text', '400 600', 'golos-text-latin-ext', LATX),
            ('Golos Text', '400 600', 'golos-text-latin', LAT)]
    return '\n'.join(f'@font-face {{ font-family: "{f}"; font-style: normal; font-weight: {w}; font-display: swap; '
                     f'src: url({FONTS}{n}.woff2) format("woff2"); unicode-range: {r}; }}' for f, w, n, r in rows)


CSS = '''
:root { --bg: #0a0b0d; --fg: #ece6d8; --muted: #a3a7ae; --gold: #c9a54a; --gold-2: #e0c27a; --gold-ink: #15110a;
  --panel: rgba(15,18,26,.9); --panel-2: #12151d; --pline: rgba(255,255,255,.08); --wrap: 1240px; --ease: cubic-bezier(.2,.7,.2,1);
  --font-display: "Bona Nova SC", Georgia, "Times New Roman", serif; --font-body: "Golos Text", "Segoe UI", system-ui, sans-serif;
  color-scheme: dark; }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.55 var(--font-body); -webkit-font-smoothing: antialiased; }
a { color: inherit; }
img { display: block; max-width: 100%; }
h1, h2 { font-family: var(--font-display); font-weight: 700; letter-spacing: .03em; line-height: 1.1; margin: 0; text-wrap: balance; }
.wrap { width: min(var(--wrap), 100% - 32px); margin-inline: auto; }
.top { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 0; }
.logo { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; font: 700 1.35rem/1 var(--font-display); letter-spacing: .04em; color: var(--gold); }
.logo img { border-radius: 8px; }
.langsel { position: relative; }
.langbtn { min-width: 44px; min-height: 44px; display: inline-flex; align-items: center; gap: 8px; padding: 0 12px; border: 1px solid color-mix(in srgb, currentColor 30%, transparent); border-radius: 8px; background: transparent; color: inherit; font: inherit; font-weight: 600; font-size: .8rem; letter-spacing: .04em; cursor: pointer; }
.langbtn::after { content: ""; width: 6px; height: 6px; border-right: 1.5px solid; border-bottom: 1.5px solid; transform: translateY(-2px) rotate(45deg); opacity: .7; }
.langbtn[aria-expanded="true"]::after { transform: translateY(2px) rotate(-135deg); }
.langlist { position: absolute; right: 0; top: calc(100% + 8px); z-index: 60; min-width: 230px; margin: 0; padding: 6px; list-style: none; border: 1px solid var(--pline); border-radius: 10px; background: var(--panel-2); color: var(--fg); box-shadow: 0 18px 48px rgba(0,0,0,.35); }
.langlist a { display: flex; justify-content: space-between; align-items: center; gap: 16px; min-height: 40px; padding: 0 12px; border-radius: 7px; color: inherit; text-decoration: none; font-size: .92rem; }
.langlist a small { opacity: .55; font-size: .72rem; font-weight: 600; letter-spacing: .06em; }
.langlist a:hover, .langlist a:focus-visible { background: color-mix(in srgb, var(--gold) 12%, transparent); }
.langlist a[aria-current="page"] { color: var(--gold-2); font-weight: 600; }
.langfoot { display: flex; flex-wrap: wrap; gap: 4px 14px; }
.langfoot a { text-decoration: none; padding: 4px 0; }
.langfoot a:hover { color: var(--fg); }
.langfoot a[aria-current] { color: var(--gold-2); font-weight: 600; }
.langhint { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); z-index: 70; display: flex; align-items: center; gap: 12px; width: max-content; max-width: calc(100% - 32px); padding: 6px 6px 6px 16px; border: 1px solid var(--pline); border-radius: 10px; background: var(--panel-2); color: var(--fg); box-shadow: 0 18px 48px rgba(0,0,0,.35); font-size: .9rem; }
.langhint a { color: var(--gold-2); font-weight: 600; white-space: nowrap; }
.langhint button { flex: none; width: 36px; height: 36px; display: grid; place-items: center; border: 0; border-radius: 7px; background: transparent; color: inherit; font-size: 1.3rem; line-height: 1; cursor: pointer; }
.langhint button:hover { background: color-mix(in srgb, currentColor 10%, transparent); }
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
.meta { margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; column-gap: .5em; row-gap: 2px; }
.new { color: var(--gold-2); font-weight: 600; font-size: 1.05rem; }
.dot { color: var(--muted); }
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
@media (max-width: 719px) { .meta .dot { display: none; } }
@media (max-width: 1023px) {
  .tiles { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: 46%; overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding-inline: 14px; overscroll-behavior-x: contain; }
  .tile { scroll-snap-align: start; }
}
@media (max-width: 719px) {
  .meta { flex-direction: column; align-items: flex-start; }
  .tiles { grid-auto-columns: 68%; }
  .hero { min-height: 440px; }
  .news li { grid-template-columns: none; gap: 2px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
'''


def css():
    return font_faces() + CSS


def json_ld(lang):
    g = C.GAMES[0]
    data = {
        '@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Gabella',
        'url': url(lang), 'inLanguage': C.HREFLANG[lang], 'description': C.T[lang]['desc'],
        'hasPart': [{'@type': 'WebSite', 'name': g['name'][lang], 'url': C.SITE + guide(lang)}],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'


def beacon():
    if not CF_BEACON_TOKEN:
        return ''
    b = json.dumps({'token': CF_BEACON_TOKEN})
    return f'<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{b}\'></script>'


def sitemap():
    alts = ''.join(f'<xhtml:link rel="alternate" hreflang="{C.HREFLANG[l]}" href="{url(l)}"/>' for l in C.LANGS)
    alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{C.SITE}/"/>'
    urls = ''.join(f'<url><loc>{url(l)}</loc>{alts}</url>\n' for l in C.LANGS)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + urls + '</urlset>\n')


def robots():
    return f'User-agent: *\nAllow: /\n\nSitemap: {C.SITE}/sitemap.xml\nSitemap: {C.SITE}/wow/sitemap.xml\n'


def render(lang, nf=False):
    if len(C.GAMES) != 1:
        sys.exit('build.py: в GAMES больше одной игры — сначала нужна сетка игр (спека, «Следующая игра»)')
    t = C.T[lang]
    with open(os.path.join(ROOT, 'index.src.html'), encoding='utf-8') as f:
        page = f.read()
    alt_loc = '\n'.join(f'<meta property="og:locale:alternate" content="{C.LOCALE[l]}">' for l in C.LANGS if l != lang)
    subs = {
        '/*@@JS@@*/': js(),
        '/*@@CSS@@*/': css(),
        '@@BODY@@': body(lang, nf),
        '@@LD@@': json_ld(lang),
        '@@HREFLANG@@': hreflang(),
        '@@OG_ALTLOC@@': alt_loc,
        '@@LANG@@': C.HREFLANG[lang],
        '@@TITLE@@': esc(t['title']),
        '@@DESC@@': esc(t['desc']),
        '@@URL@@': url(lang),
        '@@OG@@': f'{C.SITE}/assets/og-{lang}.jpg',
        '@@OG_ALT@@': esc(t['og_alt']),
        '@@LOCALE@@': C.LOCALE[lang],
    }
    for k, v in subs.items():
        page = page.replace(k, v)
    page = page.replace('</body>', beacon() + '</body>', 1)
    verify = ''.join(f'<meta name="{k}" content="{esc(v)}">\n' for k, v in VERIFY.items() if v)
    page = page.replace('</head>', verify + '</head>', 1)
    if lang == 'ru' and not nf:
        page = page.replace('<meta name="viewport"', auto_lang() + '<meta name="viewport"', 1)
    if '@@' in page:
        sys.exit(f'build.py: в странице {lang} остались плейсхолдеры @@')
    return page


NF_JS = r'''<script>
(function () {
  if (/bot|crawl|spider|slurp|lighthouse|headless|google-|preview/i.test(navigator.userAgent) || navigator.webdriver) return;
  var P = @@LANGS@@, A = { be: 'ru', kk: 'ru' }, m = location.pathname.match(/^\/([a-z]{2})\//), w = m && m[1];
  if (P.indexOf(w) < 0) {
    w = null;
    try { w = localStorage.getItem('gabella-lang'); } catch (e) {}
    var L = navigator.languages || [navigator.language];
    for (var i = 0; i < L.length && P.indexOf(w) < 0 && w !== 'ru'; i++) { w = String(L[i] || '').toLowerCase().split('-')[0]; w = A[w] || w; }
    if (P.indexOf(w) < 0 && w !== 'ru') w = 'en';
  }
  if (P.indexOf(w) < 0) return;
  document.documentElement.style.visibility = 'hidden';
  fetch('/' + w + '/404.html').then(function (r) { if (!r.ok) throw r; return r.text(); })
    .then(function (h) { document.open(); document.write(h); document.close(); })
    .catch(function () { document.documentElement.style.visibility = ''; });
})();
</script>
'''


def render_404(lang):
    """404.html: главная хаба с заголовком «Страница не найдена» — не индексируется и не каноническая.
    Корневая (русская) до отрисовки подменяет себя страницей языка из адреса, выбора в меню или браузера."""
    page = render(lang, nf=True)
    page = re.sub(r'<link rel="(canonical|alternate)"[^>]*>\n', '', page)
    page = re.sub(r'<meta property="og:(url|locale:alternate)"[^>]*>\n', '', page)
    page = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', '', page, flags=re.S)
    page = page.replace(f'<title>{esc(C.T[lang]["title"])}</title>', f'<title>{esc(C.T[lang]["nf_h"])} · Gabella</title>', 1)
    js = NF_JS.replace('@@LANGS@@', json.dumps([l for l in C.LANGS if l != 'ru'])) if lang == 'ru' else ''
    return page.replace('<meta charset="utf-8">\n', '<meta charset="utf-8">\n' + js + '<meta name="robots" content="noindex">\n', 1)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def main():
    for lang in C.LANGS:
        write(OUT[lang], render(lang))
        write(OUT_404[lang], render_404(lang))
    write('sitemap.xml', sitemap())
    write('robots.txt', robots())
    write(f'{INDEXNOW_KEY}.txt', INDEXNOW_KEY)
    print('hub: собрано', ', '.join(OUT.values()))


if __name__ == '__main__':
    main()
