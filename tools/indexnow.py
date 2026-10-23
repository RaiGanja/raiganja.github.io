"""IndexNow: сообщает Bing, Яндексу и другим поисковикам об изменённых страницах сразу после выкатки.
Зовёт его .github/workflows/indexnow.yml после сборки GitHub Pages; тот же файл лежит в хабе (gabella-hub).
Ключ публичный по замыслу IndexNow: файл https://gabella.site/<KEY>.txt лежит в корне хаба.
  python tools/indexnow.py <база> <старый коммит> <новый коммит>   — только страницы, где поменялось содержимое
  python tools/indexnow.py <база> --all                            — весь sitemap.xml (первый раз или вручную)
  --dry — показать адреса, ничего не отправлять.
<база> — адрес корня репо на сайте: https://gabella.site/wow/ (гид) или https://gabella.site/ (хаб).
В отправку попадают только адреса из sitemap.xml этого репо (noindex-страниц там нет)."""
import json, re, subprocess, sys, urllib.request

KEY = '99c3c672b2e834d250d8c7b1dc0c34b9'
HOST = 'gabella.site'
ENDPOINT = 'https://api.indexnow.org/indexnow'   # общий узел: передаёт Bing, Яндексу, Seznam, Naver и др.


def sitemap_urls():
    return re.findall(r'<loc>([^<]+)</loc>', open('sitemap.xml', encoding='utf-8').read())


def show(rev, path):
    r = subprocess.run(['git', 'show', f'{rev}:{path}'], capture_output=True)
    return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None


def norm(html):
    """Content without asset version stamps (?v=<hash>, sw VERSION): a rebuild that only bumps them is not a change."""
    return re.sub(r'\?v=[0-9a-f]+', '', html or '')


def changed_urls(base, old, new):
    names = subprocess.run(['git', 'diff', '--name-only', old, new, '--', '*.html'],
                           capture_output=True, text=True, check=True).stdout.split()
    out = []
    for p in names:
        if not (p == 'index.html' or p.endswith('/index.html')):
            continue
        if norm(show(old, p)) != norm(show(new, p)):
            out.append(base + p[:-len('index.html')])
    return out


def submit(urls):
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'https://{HOST}/{KEY}.txt', 'urlList': urls}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={'Content-Type': 'application/json; charset=utf-8',
                                                               'User-Agent': 'gabella-indexnow'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main(argv):
    dry = '--dry' in argv
    args = [a for a in argv if a != '--dry']
    base = args[0]
    known = set(sitemap_urls())
    if args[1:] == ['--all']:
        urls = sorted(known)
    else:
        old, new = args[1], args[2]
        if subprocess.run(['git', 'cat-file', '-e', old + '^{commit}']).returncode:
            print(f'indexnow: нет коммита {old} (первый пуш или переписанная история) — пропуск; весь сайт: --all')
            return 0
        urls = [u for u in changed_urls(base, old, new) if u in known]
    print(f'indexnow: {len(urls)} адресов')
    for u in urls:
        print(' ', u)
    if not urls or dry:
        return 0
    for i in range(0, len(urls), 10000):
        status = submit(urls[i:i + 10000])
        print('indexnow: ответ', status)          # 200 — принято, 202 — принято, ключ ещё проверяется
        if status not in (200, 202):
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
