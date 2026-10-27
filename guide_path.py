"""Папка гида wow рядом с хабом: projects/gabella/wow. Из worktree хаба (hub/.claude/worktrees/<имя>) она выше по дереву."""
import os
import sys

HUB = os.path.dirname(os.path.abspath(__file__))


def guide_dir():
    e = os.environ.get('GABELLA_GUIDE_DIR')   # an explicit guide checkout (a worktree of wow at the live main)
    if e and os.path.isdir(os.path.join(e, 'assets', 'art')):
        return e
    d = HUB
    while True:
        p = os.path.join(d, 'wow')
        if os.path.isdir(os.path.join(p, 'assets', 'art')):
            return p
        if os.path.dirname(d) == d:
            sys.exit('не найдена папка гида wow (с assets/art) выше хаба: хаб берёт из неё арт и страницы /wow/')
        d = os.path.dirname(d)
