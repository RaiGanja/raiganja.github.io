"""Превью ссылок хаба: python tools/make_og.py [--langs=de,fr] -> assets/og-<lang>.jpg (1200x630); без --langs — все языки"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
import content as C  # noqa: E402

GUIDE = os.path.join(os.path.dirname(HUB), 'wfpages', 'assets')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


def f(rel):
    return 'file:///' + os.path.join(GUIDE, rel).replace('\\', '/')


def page(lang):
    return f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:"Bona Nova SC";font-weight:700;src:url({f("fonts/bona-nova-sc-cyrillic.woff2")});unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:"Bona Nova SC";font-weight:700;src:url({f("fonts/bona-nova-sc-latin.woff2")});unicode-range:U+0000-00FF,U+2000-206F}}
@font-face{{font-family:"Bona Nova SC";font-weight:700;src:url({f("fonts/bona-nova-sc-latin-ext.woff2")});unicode-range:U+0100-024F}}
@font-face{{font-family:"Golos Text";src:url({f("fonts/golos-text-cyrillic.woff2")});unicode-range:U+0400-045F,U+0490-0491}}
@font-face{{font-family:"Golos Text";src:url({f("fonts/golos-text-latin.woff2")});unicode-range:U+0000-00FF,U+2000-206F}}
@font-face{{font-family:"Golos Text";src:url({f("fonts/golos-text-latin-ext.woff2")});unicode-range:U+0100-024F}}
*{{margin:0;box-sizing:border-box}}
body{{width:1200px;height:630px;position:relative;overflow:hidden;background:#0a0b0d;color:#ece6d8;font-family:"Golos Text"}}
img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 40%}}
.shade{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,11,13,.92) 0%,rgba(10,11,13,.6) 55%,rgba(10,11,13,.15) 100%)}}
.txt{{position:absolute;left:72px;bottom:72px;display:grid;gap:18px}}
.brand{{display:flex;align-items:center;gap:16px;font:700 96px/1 "Bona Nova SC";letter-spacing:.04em;color:#c9a54a}}
.brand img{{position:static;width:72px;height:72px;border-radius:14px}}
p{{font-size:36px;color:#ece6d8}}
</style><body><img src="{f("art/hero_dawn-1440.webp")}" alt=""><div class="shade"></div>
<div class="txt"><div class="brand"><img src="{f("icons/icon-192.png")}" alt="">Gabella</div><p>{C.T[lang]["og_sub"]}</p></div></body>'''


def shoot(html, out):
    with tempfile.TemporaryDirectory() as tmp:
        src, png = os.path.join(tmp, 'c.html'), os.path.join(tmp, 'c.png')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write(html)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                        '--force-device-scale-factor=1', '--window-size=1200,630', '--virtual-time-budget=3000',
                        f'--screenshot={png}', 'file:///' + src.replace('\\', '/')], check=True, capture_output=True)
        Image.open(png).convert('RGB').save(out, quality=82, optimize=True, progressive=True)


def main():
    os.makedirs(os.path.join(HUB, 'assets'), exist_ok=True)
    arg = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--langs=')), '')
    for lang in arg.split(',') if arg else C.LANGS:
        shoot(page(lang), os.path.join(HUB, 'assets', f'og-{lang}.jpg'))
        print('og', lang, 'ok')


if __name__ == '__main__':
    main()
