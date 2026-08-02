# -*- coding: utf-8 -*-
"""コマンドライン。

  python3 drill.py                 ドリルモード（対話）
  python3 drill.py play 2          第2章だけ練習
  python3 drill.py review          間違えた問題だけ復習
  python3 drill.py exam            模擬試験（ランダム10問・ヒントなし・最後に採点）
  python3 drill.py setup           フィールドモード用の playground/ を作る
  python3 drill.py check 1-03 'ls -a'   本物のシェルで練習して答え合わせ
  python3 drill.py lesson 3        章の解説を読む
  python3 drill.py progress        進捗
  python3 drill.py theme logs      題材を切り替える
"""

import os
import shutil
import sys

from . import content, judge, progress, sandbox, themes

ROOT = content.ROOT
DATA_ROOT = os.path.join(ROOT, ".data")
PLAYGROUND = os.path.join(ROOT, "playground")

# input() に行編集（←→ でのカーソル移動、↑↓ での履歴、Ctrl+A / Ctrl+E）を与える。
# readline を読み込まないと、矢印キーが ^[[A のような文字として入ってしまう。
HISTFILE = os.path.join(ROOT, ".history")
try:
    import atexit
    import readline

    readline.set_history_length(500)
    # 既定のファイル名補完は、コマンドを打つ練習の邪魔になりにくいので残す。
    # ただし補完の区切り文字は控えめにしておく。
    try:
        readline.set_completer_delims(" \t\n")
    except (AttributeError, ValueError):
        pass
    try:
        readline.read_history_file(HISTFILE)
    except OSError:
        pass

    def _save_history():
        try:
            readline.write_history_file(HISTFILE)
        except OSError:
            pass

    atexit.register(_save_history)
    HAS_READLINE = True
except ImportError:  # readline のない環境（一部の Windows など）
    HAS_READLINE = False

_C = sys.stdout.isatty()
def _c(code, s):
    return "\033[%sm%s\033[0m" % (code, s) if _C else s
BOLD = lambda s: _c("1", s)
GREEN = lambda s: _c("32", s)
RED = lambda s: _c("31", s)
YEL = lambda s: _c("33", s)
DIM = lambda s: _c("2", s)
CYAN = lambda s: _c("36", s)

LINE = "─" * 60


# ------------------------------------------------------------ データ
def ensure_data(theme):
    """テーマごとの原本データを用意し、そのパスと役割表を返す。"""
    d = os.path.join(DATA_ROOT, theme)
    stamp = os.path.join(d, ".built")
    manifest = None
    if not os.path.exists(stamp):
        shutil.rmtree(d, ignore_errors=True)
        manifest = themes.build(theme, d)
        with open(stamp, "w") as f:
            f.write("ok\n")
        _write_manifest(d, manifest)
    else:
        manifest = _read_manifest(d)
        if manifest is None:
            shutil.rmtree(d, ignore_errors=True)
            manifest = themes.build(theme, d)
            with open(stamp, "w") as f:
                f.write("ok\n")
            _write_manifest(d, manifest)
    return d, manifest


def _mpath(d):
    return os.path.join(d, ".manifest.json")


def _write_manifest(d, manifest):
    import json
    with open(_mpath(d), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)


def _read_manifest(d):
    import json
    try:
        with open(_mpath(d), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_context():
    st = progress.load()
    theme = st.get("theme", "bio")
    data_dir, manifest = ensure_data(theme)
    problems = content.load_all(manifest)
    return st, theme, data_dir, manifest, problems


# ------------------------------------------------------------ 表示
def show_problem(p, index=None, total=None, exam=False):
    head = "問題 %s" % p["id"]
    if index is not None:
        head += "  (%d/%d)" % (index, total)
    print()
    print(BOLD(head) + DIM("  第%s章 %s" % (p["chapter"], p["chapter_title"])))
    print(LINE)
    if p.get("scenario"):
        for ln in p["scenario"].strip().split("\n"):
            print(CYAN("│ " + ln))
    print(BOLD(p["prompt"]))
    if p.get("choices"):
        for i, ch in enumerate(p["choices"], 1):
            print("   %d) %s" % (i, ch))
    if p.get("platform_note"):
        print(DIM("※ " + p["platform_note"]))
    print(LINE)
    if exam:
        keys = "skip=とばす  quit=中断  （ヒントはありません）"
    else:
        keys = "hint=ヒント  skip=とばす  files=ファイル一覧  quit=終了"
    if HAS_READLINE:
        keys += "   （↑↓ 履歴 / ←→ 編集）"
    print(DIM(keys))


def show_files(data_dir):
    print(DIM("練習ディレクトリの中身:"))
    for dirpath, dirnames, filenames in os.walk(data_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel = os.path.relpath(dirpath, data_dir)
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            shown = name if rel == "." else os.path.join(rel, name)
            try:
                n = sum(1 for _ in open(full, "rb"))
            except OSError:
                n = 0
            print("   %-22s %6d 行  %7d バイト"
                  % (shown, n, os.path.getsize(full)))


def feedback(v, p, hints_used):
    if v.code == judge.OK:
        print(GREEN("✓ " + v.message))
    elif v.code == judge.PARTIAL:
        print(YEL("△ " + v.message))
        print(DIM("  " + v.detail))
    elif v.code == judge.BLOCKED:
        print(YEL("! " + v.message))
        if v.detail:
            print(DIM("  " + v.detail))
    elif v.code == judge.ERROR:
        print(YEL("! " + v.message))
        print(DIM("  " + v.detail))
    else:
        print(RED("✗ " + v.message))
        if v.detail:
            print(DIM("  " + v.detail))
        if v.expected is not None and hints_used >= 2:
            e = v.expected.strip().split("\n")[:3]
            a = (v.actual or "").strip().split("\n")[:3]
            print(DIM("  期待した出力の先頭: " + " / ".join(e)))
            print(DIM("  あなたの出力の先頭: " + " / ".join(a)))


def show_answer(p):
    print(GREEN("模範解答: ") + BOLD(p["solution"]))
    for alt in p.get("alt_solutions") or []:
        print(DIM("  別解: " + alt))
    if p.get("explain"):
        print()
        for ln in p["explain"].strip().split("\n"):
            print("  " + ln)


# ------------------------------------------------------------ ドリルモード
def _ask(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return "quit"


def solve(p, data_dir, st, index=None, total=None):
    """1 問を対話で解く。True=クリア, False=スキップ, None=終了"""
    show_problem(p, index, total)
    hints = p.get("hints") or []
    is_text = (p.get("judge") or {}).get("mode") == "text"
    used = 0
    while True:
        ans = _ask("\n$ ").strip()
        low = ans.lower()

        # 紙の問題では、正解そのものが quit や q と重なることがある。
        # 操作用の言葉として解釈する前に、まず答えとして照合する。
        if is_text and judge.judge_text(ans, p).passed:
            feedback(judge.judge_text(ans, p), p, used)
            progress.record(st, p["id"], True, used)
            if p.get("explain"):
                print()
                for ln in p["explain"].strip().split("\n"):
                    print(DIM("  " + ln))
            return True

        if low in ("quit", "exit", ":q"):
            return None
        if low in ("skip", "next"):
            print(DIM("とばしました。"))
            return False
        if low == "files":
            show_files(data_dir)
            continue
        if low == "hint":
            if used < len(hints):
                label = ["ヒント1（どの道具を使うか）", "ヒント2（必要なオプション）",
                         "ヒント3（答え）"][min(used, 2)]
                print(YEL(label + ": ") + hints[used])
                used += 1
            else:
                print(DIM("これ以上のヒントはありません。answer で答えを見られます。"))
            continue
        if low == "answer":
            show_answer(p)
            progress.record(st, p["id"], False, used)
            return False
        if not ans:
            continue

        if (p.get("judge") or {}).get("mode") == "text":
            v = judge.judge_text(ans, p)
        else:
            v = judge.judge(ans, p, data_dir)
        feedback(v, p, used)
        if v.code in (judge.OK, judge.PARTIAL):
            progress.record(st, p["id"], True, used)
            if p.get("explain"):
                print()
                for ln in p["explain"].strip().split("\n"):
                    print(DIM("  " + ln))
            if v.code == judge.PARTIAL:
                print(DIM("  模範解答: " + p["solution"]))
            return True
        progress.record(st, p["id"], False, used)


def cmd_play(args):
    st, theme, data_dir, manifest, problems = load_context()
    chap = None
    if args:
        try:
            chap = int(args[0])
        except ValueError:
            pass
    queue = [p for p in problems if chap is None or p["chapter"] == chap]
    if chap is not None:
        les = content.lesson(chap)
        if les:
            print()
            print(les.strip())
            print()
            _ask(DIM("Enter で問題へ進みます…"))
    todo = [p for p in queue if not progress.is_cleared(st, p["id"])]
    if not todo:
        print(GREEN("この範囲はすべてクリア済みです。"))
        print(DIM("復習は `review`、進捗は `progress` で見られます。"))
        return
    print(BOLD("テーマ: %s / 未クリア %d 問" % (themes.THEME_LABELS[theme], len(todo))))
    if not HAS_READLINE:
        print(YEL("※ 行編集が使えません（readline がありません）。"))
        print(DIM("   矢印キーが ^[[A のように表示されます。"
                  "pip install gnureadline で直ることがあります。"))
    for i, p in enumerate(todo, 1):
        r = solve(p, data_dir, st, i, len(todo))
        if r is None:
            break
    s = progress.summary(st, problems)
    print("\n" + BOLD("進捗: %d/%d 問クリア" % (s["cleared"], s["total"])))


def cmd_review(args):
    st, theme, data_dir, manifest, problems = load_context()
    q = progress.review_queue(st, problems)
    if not q:
        print(DIM("復習が必要な問題はまだありません。"))
        return
    print(BOLD("間違えた・ヒントを使った %d 問を復習します。" % len(q)))
    for i, p in enumerate(q, 1):
        if solve(p, data_dir, st, i, len(q)) is None:
            break


def cmd_check(args):
    """フィールドモード: python3 drill.py check 1-03 'ls -a'"""
    if len(args) < 2:
        print("使い方: python3 drill.py check <問題ID> '<コマンド>'")
        return 1
    pid, cmd = args[0], " ".join(args[1:])
    st, theme, data_dir, manifest, problems = load_context()
    p = next((x for x in problems if x["id"] == pid), None)
    if p is None:
        print(RED("問題 %s が見つかりません。" % pid))
        return 1
    if (p.get("judge") or {}).get("mode") == "text":
        v = judge.judge_text(cmd, p)
    else:
        v = judge.judge(cmd, p, data_dir)
    feedback(v, p, 0)
    progress.record(st, pid, v.code in (judge.OK, judge.PARTIAL))
    return 0 if v.passed else 1


def cmd_exam(args):
    """模擬試験: ランダムに 10 問、ヒントなし、最後にまとめて採点。"""
    import random as _random
    st, theme, data_dir, manifest, problems = load_context()
    n = 10
    if args:
        try:
            n = max(1, min(30, int(args[0])))
        except ValueError:
            pass
    pool = _random.sample(problems, min(n, len(problems)))
    print(BOLD("模擬試験  %d 問  ヒントなし" % len(pool)))
    print(DIM("答えを 1 行で書いてください。skip でとばせます。quit で中断。"))
    print(DIM("実行して確かめられない本番のつもりで、一度で書ききること。"))
    results = []
    for i, p in enumerate(pool, 1):
        show_problem(p, i, len(pool), exam=True)
        while True:
            ans = _ask("\n答え> ").strip()
            if not ans:
                continue
            break
        if ans.lower() in ("quit", "exit"):
            print(DIM("中断しました。"))
            break
        if ans.lower() == "skip":
            results.append((p, ans, None))
            continue
        if (p.get("judge") or {}).get("mode") == "text":
            v = judge.judge_text(ans, p)
        else:
            v = judge.judge(ans, p, data_dir)
        results.append((p, ans, v))
        print(DIM("記録しました。"))

    if not results:
        return
    ok = sum(1 for _, _, v in results if v and v.code in (judge.OK, judge.PARTIAL))
    print("\n" + LINE)
    print(BOLD("結果  %d / %d 問正解" % (ok, len(results))))
    print(LINE)
    for p, ans, v in results:
        if v and v.code in (judge.OK, judge.PARTIAL):
            print(GREEN("✓ ") + "%-6s %s" % (p["id"], p["title"]))
            continue
        print(RED("✗ ") + "%-6s %s" % (p["id"], p["title"]))
        print(DIM("   あなたの答え: " + (ans if ans.lower() != "skip" else "（とばした）")))
        print("   " + GREEN("模範解答: ") + p["solution"])
        progress.record(st, p["id"], False)
    print()
    print(DIM("間違えた問題は python3 drill.py review で解き直せます。"))


def cmd_show(args):
    st, theme, data_dir, manifest, problems = load_context()
    if not args:
        print("使い方: python3 drill.py show <問題ID>")
        return 1
    p = next((x for x in problems if x["id"] == args[0]), None)
    if p is None:
        print(RED("見つかりません。"))
        return 1
    show_problem(p)
    return 0


def cmd_setup(args):
    st, theme, data_dir, manifest, problems = load_context()
    shutil.rmtree(PLAYGROUND, ignore_errors=True)
    shutil.copytree(data_dir, PLAYGROUND)
    for junk in (".built", ".manifest.json"):
        j = os.path.join(PLAYGROUND, junk)
        if os.path.exists(j):
            os.remove(j)
    print(GREEN("playground/ を作りました。") +
          DIM("（テーマ: %s）" % themes.THEME_LABELS[theme]))
    print()
    print("本物のシェルで練習する手順:")
    print("  cd playground")
    print("  ls")
    print("  ... 好きなだけ試す（壊しても `python3 drill.py setup` で作り直せます）")
    print("  cd ..")
    print("  python3 drill.py show 1-01")
    print("  python3 drill.py check 1-01 'pwd'")
    print()
    show_files(data_dir)


def cmd_list(args):
    st, theme, data_dir, manifest, problems = load_context()
    cur = None
    for p in problems:
        if p["chapter"] != cur:
            cur = p["chapter"]
            print()
            print(BOLD("第%s章 %s" % (p["chapter"], p["chapter_title"])))
        mark = GREEN("✓") if progress.is_cleared(st, p["id"]) else DIM("・")
        print("  %s %-6s %s" % (mark, p["id"], p["title"]))


def cmd_progress(args):
    st, theme, data_dir, manifest, problems = load_context()
    s = progress.summary(st, problems)
    print(BOLD("テーマ: %s" % themes.THEME_LABELS[theme]))
    print("クリア    : %d / %d" % (s["cleared"], s["total"]))
    print("ノーヒント: %d" % s["perfect"])
    q = progress.review_queue(st, problems)
    if q:
        print("\n" + YEL("復習したい問題:"))
        for p in q[:8]:
            r = st["records"][p["id"]]
            print("  %-6s %s  (誤答 %d 回 / ヒント %d)"
                  % (p["id"], p["title"], r["misses"], r["hints"]))
        print(DIM("  → python3 drill.py review"))


def cmd_lesson(args):
    if not args:
        for ch, title, n in content.chapters():
            print("  第%s章 %s (%d 問)" % (ch, title, n))
        return
    les = content.lesson(args[0])
    print(les.strip() if les else RED("その章の解説はありません。"))


def cmd_theme(args):
    st = progress.load()
    if not args:
        print("現在のテーマ: %s" % themes.THEME_LABELS[st.get("theme", "bio")])
        for k, v in themes.THEME_LABELS.items():
            print("  %-8s %s" % (k, v))
        print(DIM("切り替え: python3 drill.py theme logs"))
        return
    t = args[0]
    if t not in themes.BUILDERS:
        print(RED("未知のテーマです。"))
        return 1
    st["theme"] = t
    progress.save(st)
    ensure_data(t)
    print(GREEN("テーマを %s に切り替えました。" % themes.THEME_LABELS[t]))
    print(DIM("進捗はそのまま引き継がれます。同じ問題を別の題材で解き直せます。"))


def cmd_reset(args):
    if os.path.exists(progress.PATH):
        os.remove(progress.PATH)
    print(GREEN("進捗を消しました。"))


def cmd_help(args=None):
    print(__doc__.strip())


COMMANDS = {
    "play": cmd_play, "review": cmd_review, "check": cmd_check,
    "setup": cmd_setup, "list": cmd_list, "progress": cmd_progress,
    "exam": cmd_exam,
    "lesson": cmd_lesson, "theme": cmd_theme, "reset": cmd_reset,
    "show": cmd_show, "help": cmd_help,
}


def main(argv):
    if not argv:
        return cmd_play([])
    cmd, args = argv[0], argv[1:]
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(RED("未知のコマンド: %s\n" % cmd))
        cmd_help()
        return 1
    return fn(args) or 0
