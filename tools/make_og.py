"""Превью ссылок хаба: python tools/make_og.py [--langs=de,fr] -> assets/og-<lang>.jpg (1200x630); без --langs — все языки"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
import content as C  # noqa: E402
from guide_path import guide_dir  # noqa: E402

GUIDE = os.path.join(guide_dir(), 'assets')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


def f(rel):
    return 'file:///' + os.path.join(GUIDE, rel).replace('\\', '/')


def page(lang):
    fonts = ''.join(
        f'@font-face{{font-family:"{fam}";font-weight:400 700;src:url({f("fonts/" + name)});unicode-range:{rng}}}'
        for fam, base in (('Spectral SC', 'spectral-sc'), ('Golos Text', 'golos-text'))
        for name, rng in ((base + '-cyrillic.woff2', 'U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116'),
                          (base + '-latin-ext.woff2', 'U+0100-02BA,U+1E00-1E9F'), (base + '-latin.woff2', 'U+0000-00FF,U+2000-206F')))
    return f'''<!doctype html><meta charset="utf-8"><style>{fonts}
*{{margin:0;box-sizing:border-box}}
body{{width:1200px;height:630px;position:relative;overflow:hidden;background:#050505;color:#efe9da;font-family:"Golos Text";font-variant-numeric:lining-nums}}
.art{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:70% 50%}}
.shade{{position:absolute;inset:0;background:linear-gradient(90deg,#050505 0%,rgba(5,5,5,.92) 34%,rgba(5,5,5,.35) 62%,rgba(5,5,5,0) 80%),
  linear-gradient(0deg,rgba(5,5,5,.85) 0%,rgba(5,5,5,0) 36%)}}
.brand{{position:absolute;left:72px;top:56px;display:flex;align-items:center;gap:16px;font:600 30px/1 "Spectral SC";letter-spacing:.04em}}
.brand img{{width:56px;height:56px;border-radius:10px;box-shadow:0 0 0 1px rgba(201,165,74,.45)}}
.txt{{position:absolute;left:72px;top:0;bottom:0;width:600px;display:flex;flex-direction:column;justify-content:center;gap:24px}}
h1{{font:600 92px/1.02 "Spectral SC";letter-spacing:.02em}}
p{{font-size:34px;line-height:1.3;color:#c9c2b0;text-wrap:balance}}
.start{{position:absolute;left:72px;bottom:56px;font:600 28px/1 "Spectral SC";letter-spacing:.03em;color:#c9a54a;font-variant-numeric:lining-nums}}
</style><body><img class="art" src="{f("art/hero_dawn-1440.webp")}" alt=""><div class="shade"></div>
<div class="brand"><img src="{f("logo.png")}" alt="">Gabella</div>
<div class="txt"><h1>WoW Forever</h1><p>{C.T[lang]["og_sub"]}</p></div>
<div class="start">{C.T[lang]["og_start"]}</div></body>'''


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
