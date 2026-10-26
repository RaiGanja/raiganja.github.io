"""Сборка хаба gabella.site: python build.py"""
import hashlib
import html as H
import json
import os
import re
import sys

import content as C
from guide_path import guide_dir

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = {l: f'{C.PREFIX[l]}index.html' for l in C.LANGS}
OUT_404 = {l: f'{C.PREFIX[l]}404.html' for l in C.LANGS}
CF_BEACON_TOKEN = 'ee1d216e690040389063e8d72384c2c7'   # Cloudflare Web Analytics сайта gabella.site — тот же, что в гиде (wow/seo.py)

# Подтверждение прав в поисковиках (Яндекс не используем — решение 23.10): значение content= из метатега кабинета; пусто — метатег не вставляется.
# Те же значения — в гиде (wow/seo.py VERIFY). Bing подключён импортом из Search Console, msvalidate.01 — запасной путь.
VERIFY = {
    'msvalidate.01': '',         # Bing Webmaster Tools → Settings → Verification → HTML Meta Tag
}
# IndexNow: ключ публичный по замыслу протокола; файл <ключ>.txt в корне домена подтверждает его для всего gabella.site.
# Отправка — tools/indexnow.py (.github/workflows/indexnow.yml), тот же ключ в гиде wow/tools/indexnow.py.
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

  // Свои записи гида (updates.json), язык страницы; нет записи на языке — en. Ссылки только на gabella.site, ведут на страницу гида этого языка.
  const box = document.getElementById('news'), lang = document.documentElement.lang.split('-')[0], gl = lang === 'ru' ? '/wow/' : `/wow/${lang}/`;
  const pick = o => o && typeof o === 'object' ? (typeof o[lang] === 'string' && o[lang] ? o[lang] : typeof o.en === 'string' ? o.en : '') : '';
  fetch('/wow/updates.json').then(r => r.ok ? r.json() : null).then(data => {
    const list = data && data.updates;
    if (!Array.isArray(list)) return;
    const row = box.querySelector('.row3');
    list.map(n => n && typeof n.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(n.date) && { date: n.date, title: pick(n.title), text: pick(n.text), url: pick(n.url) || '', own: !!(n.url && n.url[lang]) })
      .filter(n => n && n.title && /^https:\/\/gabella\.site\//.test(n.url))
      .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3).forEach(n => {   // three cards, as «Fresh» on the guide's home
        const a = document.createElement('a'), t = document.createElement('time'), b = document.createElement('b'), u = new URL(n.url);
        a.className = 'nc'; a.href = (n.own ? u.pathname : u.pathname.replace(/^\/wow\/(en\/)?/, gl)) + u.hash;
        t.dateTime = n.date; t.textContent = n.date.split('-').reverse().slice(0, 2).join('.');
        b.textContent = n.title; a.append(t, b);
        if (n.text) { const p = document.createElement('span'); p.textContent = n.text; a.append(p); }
        row.append(a);
      });
    if (row.children.length) box.hidden = false;
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


GUIDE_ART = os.path.join(guide_dir(), 'assets', 'art')


def art(name):
    """Адрес арта гида с ?v=<хэш файла>: перерисованная сцена не залипает в кэше на 7 дней (так же, как в гиде)."""
    with open(os.path.join(GUIDE_ART, name), 'rb') as f:
        return f'{ART}{name}?v={hashlib.sha1(f.read()).hexdigest()[:8]}'


def pic(name, alt='', lazy=True):
    """Плитка: сцена раздела из гида (шапка 960) или портрет 360."""
    w, h = (960, 536) if name.startswith('hero_') else (360, 482)
    load = ' loading="lazy"' if lazy else ''
    return (f'<picture><source type="image/avif" srcset="{art(f"{name}-{w}.avif")}">'
            f'<img src="{art(f"{name}-{w}.webp")}" alt="{esc(alt)}" width="{w}" height="{h}"{load} decoding="async"></picture>')


def hero_pic(name):
    """Full-width scene as on the guide's home: the guide's cuts (phone 600-1000, wide 960-3840) and, for the ultrawide
    sides, the same scene small and blurred (.hero-amb)."""
    def m(ext):
        return ', '.join(f'{art(f"{name}-m-{w}.{ext}")} {w}w' for w in (600, 800, 1000))

    def d(ext):
        return ', '.join(f'{art(f"{name}-{w}.{ext}")} {w}w' for w in (960, 1440, 1920, 2560, 3840))
    sizes = '(max-aspect-ratio: 21/10) 210vh, 100vw'
    return (f'<img class="hero-amb" src="{art(f"{name}-960.webp")}" alt="" width="960" height="536" aria-hidden="true" decoding="async">'
            '<picture class="hero-art">'
            f'<source media="(max-width: 719px)" type="image/avif" srcset="{m("avif")}" sizes="100vw">'
            f'<source media="(max-width: 719px)" type="image/webp" srcset="{m("webp")}" sizes="100vw">'
            f'<source type="image/avif" srcset="{d("avif")}" sizes="{sizes}">'
            f'<source type="image/webp" srcset="{d("webp")}" sizes="{sizes}">'
            f'<img src="{art(f"{name}-1920.webp")}" alt="" width="1920" height="1072" fetchpriority="high" decoding="async"></picture>')


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
    return f'''<header class="top"><div class="wrap">
<a class="logo" href="/{C.PREFIX[lang]}"><img class="mark" src="/wow/assets/brand/mark.webp" alt="" width="40" height="40"><span>Gabella</span></a>
{lang_switch(lang)}
</div></header>
<main>
<section class="hero" aria-labelledby="g-{g["id"]}">
{hero_pic(g["art"])}
<div class="wrap hero-in">
<div class="intro"><h1>{esc(h1)}</h1><p>{esc(lead)}</p></div>
<div class="hero-txt">
<h2 id="g-{g["id"]}">{esc(g["name"][lang])}</h2>
<p class="meta"><span id="cd" class="cd" data-at="{C.RELEASE}" data-left="{esc(t["rel_left"])}" data-done="{esc(t["rel_done"])}">{esc(t["rel_static"])}</span></p>
<a href="{guide(lang)}" class="hero-cta">{esc(t["open"])}</a>
</div>
</div>
</section>
<section class="sections wrap" aria-labelledby="sec-h">
<h2 id="sec-h">{esc(t["sections_h"])}</h2>
<div class="tiles">{tiles(lang)}</div>
</section>
<section id="news" class="news wrap" hidden aria-labelledby="news-h">
<div class="hh"><h2 id="news-h">{esc(t["news_h"])}</h2><a href="{guide(lang)}guides/news/" id="news-all">{esc(t["news_all"])} →</a></div>
<div class="row3"></div>
</section>
</main>
<footer class="foot wrap">
<p>© Gabella · <a href="{guide(lang)}">{esc(t["guide_link"])}</a> · <a href="{C.DISCORD}" target="_blank" rel="noopener">Discord</a> · <a href="{C.TELEGRAM}" target="_blank" rel="noopener">Telegram</a></p>
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
    rows = [('Spectral SC', '400 700', 'spectral-sc-cyrillic', CYR),
            ('Spectral SC', '400 700', 'spectral-sc-latin-ext', LATX),
            ('Spectral SC', '400 700', 'spectral-sc-latin', LAT),
            ('Golos Text', '400 600', 'golos-text-cyrillic', CYR),
            ('Golos Text', '400 600', 'golos-text-latin-ext', LATX),
            ('Golos Text', '400 600', 'golos-text-latin', LAT)]
    return '\n'.join(f'@font-face {{ font-family: "{f}"; font-style: normal; font-weight: {w}; font-display: swap; '
                     f'src: url({FONTS}{n}.woff2) format("woff2"); unicode-range: {r}; }}' for f, w, n, r in rows)


CSS = '''
:root { --bg: #050505; --fg: #ece6d8; --muted: #a8a8a8; --gold: #c9a54a; --gold-2: #e0c27a; --gold-ink: #15110a;
  --panel: rgba(8,8,8,.94); --panel-2: #141414; --pline: rgba(255,255,255,.08); --wrap: 1240px; --ease: cubic-bezier(.2,.7,.2,1);
  --font-display: "Spectral SC", Georgia, "Times New Roman", serif; --font-body: "Golos Text", "Segoe UI", system-ui, sans-serif;
  color-scheme: dark; }
/* Ultrawide, as in the guide: the column and the type grow a step from 2200 px; up to 2199 px nothing changes. */
@media (min-width: 2200px) { :root { --wrap: 1560px; } html { font-size: 17px; } }
@media (min-width: 3000px) { :root { --wrap: 1720px; } html { font-size: 18px; } }
/* Светлая тема — как в гиде: localStorage wf-theme, без выбора — системная (prefers-color-scheme). Палитра как у светлой темы гида.
   Арт и текст на нём остаются ночными, как в гиде. */
:root[data-theme="light"] { --bg: #f3f2ee; --fg: #17161a; --muted: #595650; --gold: #7d5c12; --gold-2: #7d5c12; --gold-ink: #ffffff;
  --panel: rgba(255,255,255,.95); --panel-2: #f6f4ef; --pline: #e2ddd2; color-scheme: light; }
:root[data-theme="light"] .hero-txt { color: #ece6d8; --gold: #c9a54a; --gold-2: #e0c27a; --gold-ink: #15110a; }
:root[data-theme="light"] .frame { box-shadow: 0 10px 30px rgba(40,32,16,.08); }
:root[data-theme="light"] .langlist, :root[data-theme="light"] .langhint { box-shadow: 0 10px 30px rgba(40,32,16,.16); }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 1rem/1.55 var(--font-body); -webkit-font-smoothing: antialiased; }
a { color: inherit; }
img { display: block; max-width: 100%; }
h1, h2 { font-family: var(--font-display); font-weight: 600; letter-spacing: .03em; line-height: 1.1; margin: 0; text-wrap: balance; }
.wrap { width: min(var(--wrap), 100% - 32px); margin-inline: auto; }
/* Top bar as in the guide: the emblem in a gold hairline, the name in the display face, over the scene */
.top { position: absolute; inset: 0 0 auto 0; z-index: 30; height: 64px; color: #f1ece0; background: linear-gradient(rgba(5,6,8,.62), rgba(5,6,8,0)); }
.top .wrap { height: 100%; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.logo { display: inline-flex; align-items: center; gap: 12px; min-height: 44px; text-decoration: none; color: inherit; font: 600 1.375rem/1 var(--font-display); letter-spacing: .02em; }
.mark { width: 40px; height: 40px; flex: none; border-radius: 8px; box-shadow: 0 0 0 1px rgba(201,165,74,.35); }
@media (min-width: 2200px) { .top { height: 68px; } .mark { width: 43px; height: 43px; } .langbtn { min-width: 47px; min-height: 47px; } }
@media (min-width: 3000px) { .top { height: 72px; } .mark { width: 45px; height: 45px; } .langbtn { min-width: 50px; min-height: 50px; } }
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
/* Hero: the full-width scene of the guide's home, text on its dark left side, the bottom melting into the page */
.hero { --hh: clamp(560px, 88svh, 1000px); position: relative; isolation: isolate; overflow: hidden; min-height: var(--hh); display: grid; color: #ece6d8; background: #050505; }
.hero-art, .hero-art img { position: absolute; inset: 0; width: 100%; height: 100%; }
.hero-art { z-index: -2; }
.hero-art img { object-fit: cover; object-position: 62% 50%; }
.hero-amb { display: none; }
/* past 21:10 the scene stops growing: it keeps to the right, its left edge melts into a blurred copy (as /wow/) */
@media (min-width: 720px) {
  .hero-art { left: auto; width: min(100%, calc(var(--hh) * 2.1)); -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 18%); mask-image: linear-gradient(90deg, transparent 0, #000 18%); }
  .hero-amb { display: block; position: absolute; inset: 0; z-index: -3; width: 100%; height: 100%; object-fit: cover; object-position: 62% 50%; filter: blur(32px) brightness(.5) saturate(1.15); clip-path: inset(0); }
}
.hero::before { content: ""; position: absolute; inset: 0; z-index: -1; background:
  linear-gradient(90deg, rgb(5 5 5 / .5) calc(50% - 800px), rgb(5 5 5 / .46) calc(50% - 420px), rgb(5 5 5 / .3) calc(50% + 100px), rgb(5 5 5 / .06) calc(50% + 500px)),
  linear-gradient(180deg, rgb(5 5 5 / .42) 0%, rgb(5 5 5 / 0) 24%, rgb(5 5 5 / 0) 56%, rgb(5 5 5 / .9) 90%, var(--bg) 100%); }
.hero-in { display: grid; align-content: space-between; gap: 40px; padding: calc(64px + clamp(32px, 8vh, 96px)) 0 clamp(40px, 7vh, 80px); }
.intro { display: grid; gap: 12px; max-width: 40rem; text-shadow: 0 1px 2px rgba(5,5,5,.7), 0 2px 22px rgba(5,5,5,.55); }
.intro h1 { font-size: clamp(2.6rem, 1.6rem + 3vw, 4.6rem); line-height: 1; color: #f1ece0; }
.intro p { margin: 0; color: #e8e2d4; font-size: 1.125rem; max-width: 34rem; }
.hero-txt { display: grid; gap: 12px; justify-items: start; }
.meta { margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; column-gap: .5em; row-gap: 2px; }
.hero h2 { font-size: clamp(2.2rem, 1.4rem + 2.6vw, 3.8rem); color: #e0c27a; text-shadow: 0 2px 18px rgba(0,0,0,.6); }
.cd { font: 600 1.25rem/1.2 var(--font-display); letter-spacing: .03em; font-variant-numeric: tabular-nums lining-nums; text-shadow: 0 1px 8px rgba(0,0,0,.7); }
.hero-cta { margin-top: 6px; min-height: 52px; display: inline-flex; align-items: center; padding: 0 26px; border-radius: 7px; background: #c9a54a; color: #15110a;
  font-weight: 600; text-decoration: none; transition: background .2s; }
.hero-cta:hover { background: #e0c27a; }
.sections, .news { margin-top: 56px; display: grid; gap: 18px; }
.sections h2, .news h2 { font-size: clamp(1.5rem, 3vw, 2.1rem); }
.frame { border: 1px solid var(--pline); border-radius: 10px; background: var(--panel); box-shadow: 0 18px 48px rgba(0,0,0,.35); min-width: 0; }
.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.tile { position: relative; isolation: isolate; overflow: hidden; height: 210px; padding: 0 14px 14px; display: grid; align-content: end;
  border: 1px solid rgba(255,255,255,.1); border-radius: 7px; background: #0a0a0a; color: #f3efe6; text-decoration: none; transition: border-color .2s; }
.tile picture, .tile img { position: absolute; inset: 0; width: 100%; height: 100%; }
.tile picture { z-index: -2; }
.tile img { object-fit: cover; object-position: 50% 22%; filter: saturate(.85) brightness(.78); transition: filter .3s, transform .6s var(--ease); }
.tile::after { content: ""; position: absolute; inset: 0; z-index: -1; background: linear-gradient(180deg, rgba(5,5,5,0) 25%, rgba(5,5,5,.9) 100%); }
.tile:hover { border-color: rgba(224,194,122,.6); }
.tile:hover img { filter: none; transform: scale(1.04); }
.tile b { font-weight: 700; font-size: 1.125rem; line-height: 1.2; text-shadow: 0 1px 8px rgba(0,0,0,.7); }   /* the guide's tile titles */
@media (min-width: 2200px) { .tile { height: 260px; } }
/* News as the guide's «Fresh» cards */
.news .hh { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
#news-all { min-height: 44px; display: inline-flex; align-items: center; color: var(--gold-2); font-weight: 600; text-decoration: none; }
#news-all:hover { text-decoration: underline; text-underline-offset: 3px; }
.row3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.nc { display: grid; gap: 4px; align-content: start; padding: 14px 18px 16px; border: 1px solid var(--pline); border-radius: 10px; background: var(--panel-2); color: var(--fg); text-decoration: none; transition: border-color .2s; }
.nc:hover { border-color: var(--gold-2); }
.nc time { font-size: .8125rem; color: var(--muted); font-variant-numeric: lining-nums tabular-nums; }
.nc b { font-weight: 600; line-height: 1.3; }
.nc span { font-size: .875rem; color: var(--muted); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.foot { margin-top: 64px; padding: 24px 0 40px; border-top: 1px solid var(--pline); display: grid; gap: 10px; color: var(--muted); font-size: .92rem; }
.foot p { margin: 0; }
.foot .tm { font-size: .8rem; opacity: .8; }
:focus-visible { outline: 2px solid var(--gold-2); outline-offset: 2px; }
@media (max-width: 1023px) {
  .tiles { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: 46%; overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding-inline: 14px; overscroll-behavior-x: contain; }
  .tile { scroll-snap-align: start; }
}
@media (max-width: 719px) {
  .tiles { grid-auto-columns: 68%; }
  .row3 { grid-template-columns: minmax(0, 1fr); }
  .hero { --hh: max(560px, 92svh); }
  .hero-art img { object-position: 78% 50%; }
  .hero::before { background: linear-gradient(180deg, rgb(5 5 5 / .5) 0%, rgb(5 5 5 / .1) 22%, rgb(5 5 5 / .2) 45%, rgb(5 5 5 / .88) 72%, var(--bg) 100%); }
  .hero-in { padding-top: calc(64px + 24px); align-content: end; gap: 26px; }
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
        'publisher': {'@type': 'Organization', 'name': 'Gabella', 'url': C.SITE + '/', 'logo': C.SITE + '/wow/assets/icons/icon-512.png',
                      'sameAs': [C.DISCORD, C.TELEGRAM]},
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


# Файлы под /assets/ и /wow/assets/ Cloudflare держит 30 дней, браузер 7: адрес без ?v= у посетителей остаётся старым.
# Последний проход по готовой странице (в том числе картинки в JS и JSON-LD): ?v=<sha1 файла, 8 знаков> — как в гиде
# (build.py гида: font_version, brand_version), поэтому шрифт и иконка в хабе и в гиде имеют один адрес и один кэш.
ASSET = re.compile(r'((?:https://gabella\.site)?)(/(?:wow/)?assets/[\w./-]+\.(?:png|jpe?g|webp|avif|woff2|ico|svg)|/favicon\.ico)(?![\w.]|\?v=)')


def asset_file(path):
    return os.path.join(guide_dir() if path.startswith('/wow/') else ROOT, path[len('/wow/'):] if path.startswith('/wow/') else path.lstrip('/'))


def versioned(page):
    def tag(m):
        f = asset_file(m[2])
        if not os.path.isfile(f):
            sys.exit(f'build.py: нет файла {m[2]} ({f})')
        with open(f, 'rb') as fh:
            return f'{m[1]}{m[2]}?v={hashlib.sha1(fh.read()).hexdigest()[:8]}'
    return ASSET.sub(tag, page)


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
        '@@OG_TITLE@@': esc(t['og_title']),
        '@@OG_DESC@@': esc(t['og_desc']),
        '@@OG_ALT@@': esc(t['og_title']),
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
    return versioned(page)


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
