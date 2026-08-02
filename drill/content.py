# -*- coding: utf-8 -*-
"""問題とレッスンの読み込み。役割プレースホルダをテーマの実ファイル名へ置換する。"""

import glob
import os
import re

from . import miniyaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEM_DIR = os.path.join(ROOT, "content", "problems")
LESSON_DIR = os.path.join(ROOT, "content", "lessons")

_FIELDS = ["title", "scenario", "prompt", "solution", "explain", "platform_note"]


def _sub(text, mapping):
    if not isinstance(text, str):
        return text
    def rep(m):
        key = m.group(1)
        return str(mapping.get(key, m.group(0)))
    return re.sub(r"\{([a-zA-Z_]+)\}", rep, text)


def apply_theme(problem, manifest):
    mapping = {}
    mapping.update(manifest["files"])
    mapping.update(manifest["terms"])
    p = dict(problem)
    for f in _FIELDS:
        if p.get(f):
            p[f] = _sub(p[f], mapping)
    for f in ("hints", "alt_solutions", "accept", "choices"):
        if p.get(f):
            p[f] = [_sub(x, mapping) for x in p[f]]
    return p


def load_all(manifest=None):
    """全問題を id 順に並べたリストで返す。"""
    problems = []
    for path in sorted(glob.glob(os.path.join(PROBLEM_DIR, "*.yaml"))):
        doc = miniyaml.load_file(path)
        chapter = doc.get("chapter")
        ctitle = doc.get("title", "")
        for p in doc.get("problems") or []:
            p = dict(p)
            p["chapter"] = chapter
            p["chapter_title"] = ctitle
            if manifest:
                p = apply_theme(p, manifest)
            problems.append(p)
    return problems


def chapters():
    out = []
    for path in sorted(glob.glob(os.path.join(PROBLEM_DIR, "*.yaml"))):
        doc = miniyaml.load_file(path)
        out.append((doc.get("chapter"), doc.get("title", ""),
                    len(doc.get("problems") or [])))
    return out


def lesson(chapter):
    path = os.path.join(LESSON_DIR, "ch%02d.md" % int(chapter))
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()
