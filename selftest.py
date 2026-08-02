#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""教材の自己検査。全テーマ×全問題で、模範解答と別解が「正解」と判定されるか確かめる。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drill import content, judge, cli, themes

fail = 0; total = 0
for theme in themes.BUILDERS:
    data_dir, manifest = cli.ensure_data(theme)
    for p in content.load_all(manifest):
        cands = [p["solution"]] + (p.get("alt_solutions") or [])
        for c in cands:
            total += 1
            if (p.get("judge") or {}).get("mode") == "text":
                v = judge.judge_text(c, p)
            else:
                v = judge.judge(c, p, data_dir)
            if not v.passed:
                fail += 1
                print("NG [%s/%s] %r -> %s %s %s" % (theme, p["id"], c, v.code, v.message, v.detail))
print("%d/%d ok" % (total-fail, total))
sys.exit(1 if fail else 0)
