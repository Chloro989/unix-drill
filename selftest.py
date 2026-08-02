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
                # 失敗の原因を追えるように、実際に得られたものを出す
                from drill import sandbox
                mode = (p.get("judge") or {}).get("mode", "stdout")
                need_cwd = mode in ("cwd", "cwd+stdout")
                got = sandbox.run(c, data_dir, capture_cwd=need_cwd)
                exp = sandbox.run(p["solution"], data_dir, capture_cwd=need_cwd)
                print("    mode=%s" % mode)
                print("    cwd    got=%r exp=%r" % (got.cwd, exp.cwd))
                print("    stdout got=%r" % got.stdout[:120])
                print("    stdout exp=%r" % exp.stdout[:120])
                if got.stderr.strip():
                    print("    stderr got=%r" % got.stderr[:120])
print("%d/%d ok" % (total-fail, total))
sys.exit(1 if fail else 0)
