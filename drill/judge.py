# -*- coding: utf-8 -*-
"""三層判定。

  第1層 静的チェック  … 危険なコマンド / 答えの覗き見 / 狙いのコマンドを使っているか
  第2層 出力の比較    … 模範解答を同じサンドボックスで実行し、標準出力を突き合わせる
  第3層 ファイル差分  … `>` などで作られたファイルの中身と、最終カレントディレクトリ

模範解答の期待値はハードコードしない。採点のたびに模範解答を実行して求めるので、
データ生成器を変えても期待値が自動で追随する。
"""

import re
import unicodedata

from . import sandbox

# 判定結果コード
OK = "OK"
PARTIAL = "PARTIAL"      # 出力は合っているが狙いのコマンドを使っていない
WRONG = "WRONG"
BLOCKED = "BLOCKED"      # 実行前に止めた
ERROR = "ERROR"          # 実行時エラー / 時間切れ

DANGEROUS = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*/(\s|$)", "ルートディレクトリの削除"),
    (r":\s*\(\s*\)\s*\{", "フォークボム"),
    (r"\b(sudo|su)\b", "権限昇格は練習に不要"),
    (r"\b(curl|wget|nc|ssh|scp)\b", "ネットワーク接続は練習に不要"),
    (r"\bmkfs|dd\s+if=", "ディスク操作"),
    (r"\bshutdown|reboot\b", "システム操作"),
]

PEEK = [
    (r"(解答|answer|solution)s?\.(md|txt|ya?ml|json)", "解答ファイルの直接参照"),
    (r"content/problems", "問題定義ファイルの直接参照"),
]


class Verdict:
    def __init__(self, code, message, detail="", expected=None, actual=None):
        self.code = code
        self.message = message
        self.detail = detail
        self.expected = expected
        self.actual = actual

    @property
    def passed(self):
        return self.code == OK


# ------------------------------------------------------------ 正規化
def _nfkc(s):
    """全角スペース・全角引用符などを半角に寄せる。日本語環境での事故防止。"""
    s = s.replace("\u3000", " ").replace("“", '"').replace("”", '"')
    s = s.replace("‘", "'").replace("’", "'").replace("｜", "|")
    return unicodedata.normalize("NFKC", s)


def normalize_output(text, rules):
    rules = rules or []
    lines = text.replace("\r\n", "\n").split("\n")
    lines = [ln.rstrip() for ln in lines]
    while lines and lines[-1] == "":
        lines.pop()
    if "ignore_case" in rules:
        lines = [ln.lower() for ln in lines]
    if "squeeze_space" in rules:
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in lines]
    if "sort_lines" in rules:
        lines = sorted(lines)
    if "numeric_only" in rules:
        nums = re.findall(r"-?\d+(?:\.\d+)?", "\n".join(lines))
        return "\n".join(nums)
    return "\n".join(lines)


# ------------------------------------------------------------ 第1層
def static_check(command, problem):
    cmd = _nfkc(command).strip()
    if not cmd:
        return Verdict(BLOCKED, "コマンドが空です。")
    for pat, why in DANGEROUS:
        if re.search(pat, cmd):
            return Verdict(BLOCKED, "このコマンドは実行できません（%s）。" % why,
                           "練習に必要のない操作です。別の方法を考えてみましょう。")
    for pat, why in PEEK:
        if re.search(pat, cmd, re.I):
            return Verdict(BLOCKED, "それは %s です。" % why,
                           "答えを見たいときは hint を 3 回使ってください。")
    return None


def _uses(cmd, name):
    return re.search(r"(^|[\s|;&(])%s([\s|;&)]|$)" % re.escape(name), cmd) is not None


# ------------------------------------------------------------ 判定本体
def judge(command, problem, data_dir):
    v = static_check(command, problem)
    if v:
        return v

    cmd = _nfkc(command).strip()
    mode = (problem.get("judge") or {}).get("mode", "stdout")
    rules = (problem.get("judge") or {}).get("normalize") or []
    need_cwd = mode in ("cwd", "cwd+stdout")

    got = sandbox.run(cmd, data_dir, capture_cwd=need_cwd)
    if got.timeout:
        return Verdict(ERROR, "時間切れです。",
                       "対話的なコマンド（less, vi など）は採点できません。"
                       "終了するには q または Ctrl+C です。")
    exp = sandbox.run(problem["solution"], data_dir, capture_cwd=need_cwd)

    ok = True
    detail = []

    if mode in ("stdout", "both", "cwd+stdout"):
        a = normalize_output(got.stdout, rules)
        e = normalize_output(exp.stdout, rules)
        if a != e:
            ok = False
            detail.append("標準出力が一致しません。")

    if mode in ("files", "both"):
        a = {k: normalize_output(v, rules) for k, v in got.files.items()}
        e = {k: normalize_output(v, rules) for k, v in exp.files.items()}
        if a != e:
            ok = False
            missing = sorted(set(e) - set(a))
            extra = sorted(set(a) - set(e))
            if missing:
                detail.append("できているはずのファイルがありません: " + ", ".join(missing))
            elif extra:
                detail.append("余分なファイルができています: " + ", ".join(extra))
            else:
                detail.append("ファイルの中身が違います。")

    if need_cwd:
        if got.cwd != exp.cwd:
            ok = False
            detail.append("移動先が違います。")

    if not ok:
        if not got.stdout.strip() and exp.stdout.strip():
            detail.append(
                "出力が空でした。ファイル名を書き忘れていませんか。"
                "cut・sort・grep などはファイル名がないと"
                "「キーボードからの入力」を待つ動きになります。")
        if got.returncode != 0 and got.stderr.strip():
            detail.append("エラー出力: " + got.stderr.strip().split("\n")[0])
        return Verdict(WRONG, "残念、まだ違うようです。", " ".join(detail),
                       expected=exp.stdout, actual=got.stdout)

    # 出力は合っている。狙いのコマンドを使ったか。
    require = problem.get("require_any") or []
    if require and not any(_uses(cmd, r) for r in require):
        return Verdict(
            PARTIAL, "出力は正しいのですが、この章で練習したい道具を使っていません。",
            "%s を使う書き方も考えてみてください。（結果としては正解なので先へ進めます）"
            % " か ".join("`%s`" % r for r in require))

    return Verdict(OK, "正解です。")


# ------------------------------------------------------------ 紙の問題
def judge_text(answer, problem):
    """実行せずに文字列で照合する問題（less など、紙に書く形式）。"""
    a = _nfkc(answer).strip().lower()
    a = re.sub(r"\s+", " ", a)
    for pat in problem.get("accept") or []:
        if re.fullmatch(_nfkc(str(pat)).strip().lower(), a):
            return Verdict(OK, "正解です。")
    return Verdict(WRONG, "残念、まだ違うようです。")
