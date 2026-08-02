# -*- coding: utf-8 -*-
"""進捗の保存。間違えた問題を資産として残し、次回の復習に回す。"""

import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, ".progress.json")


def load():
    if os.path.exists(PATH):
        try:
            with open(PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {"theme": "bio", "records": {}, "started": time.time()}


def save(state):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def record(state, pid, passed, hints_used=0):
    r = state["records"].setdefault(
        pid, {"attempts": 0, "misses": 0, "cleared": False, "hints": 0})
    r["attempts"] += 1
    r["hints"] = max(r["hints"], hints_used)
    if passed:
        r["cleared"] = True
    else:
        r["misses"] += 1
    r["last"] = time.time()
    save(state)


def is_cleared(state, pid):
    return state["records"].get(pid, {}).get("cleared", False)


def review_queue(state, problems):
    """一度は間違えた（またはヒントを使った）問題を、間違いの多い順に返す。"""
    scored = []
    for p in problems:
        r = state["records"].get(p["id"])
        if not r or not r["cleared"]:
            continue
        weight = r["misses"] * 2 + r["hints"]
        if weight > 0:
            scored.append((weight, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored]


def summary(state, problems):
    total = len(problems)
    cleared = sum(1 for p in problems if is_cleared(state, p["id"]))
    perfect = sum(1 for p in problems
                  if is_cleared(state, p["id"])
                  and state["records"][p["id"]]["misses"] == 0
                  and state["records"][p["id"]]["hints"] == 0)
    return {"total": total, "cleared": cleared, "perfect": perfect}
