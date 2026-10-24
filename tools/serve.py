"""Превью хаба: python tools/serve.py -> http://127.0.0.1:8766/ (/wow/ отдаётся из ../wow)"""
import functools
import http.server
import os
import sys

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HUB)
from guide_path import guide_dir  # noqa: E402

GUIDE = guide_dir()


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == '/wow' or path.startswith('/wow/'):
            rel = path[len('/wow'):] or '/'
            return http.server.SimpleHTTPRequestHandler.translate_path(self, rel).replace(HUB, GUIDE, 1)
        return super().translate_path(path)


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(Handler, directory=HUB)).serve_forever()
