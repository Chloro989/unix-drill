# -*- coding: utf-8 -*-
"""使い捨てのサンドボックス。

採点のたびにデータ一式を一時ディレクトリへコピーし、そこでコマンドを実行して
終わったら捨てる。利用者は何をやっても元データを壊せないので、
`rm` や `>` を含む問題も安心して出題できる。
"""

import os
import shutil
import subprocess
import tempfile

TIMEOUT = 15
MAX_SNAPSHOT_BYTES = 2_000_000


class RunResult:
    def __init__(self, stdout="", stderr="", returncode=0, cwd="", files=None,
                 timeout=False, error=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.cwd = cwd
        self.files = files or {}
        self.timeout = timeout
        self.error = error


def snapshot(root):
    """ディレクトリ内のファイル内容を {相対パス: 内容} で返す。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            try:
                if os.path.getsize(full) > MAX_SNAPSHOT_BYTES:
                    out[rel] = "<large:%d>" % os.path.getsize(full)
                    continue
                with open(full, "rb") as f:
                    raw = f.read()
                out[rel] = raw.decode("utf-8", "replace")
            except OSError:
                out[rel] = "<unreadable>"
    return out


def run(command, data_dir, capture_cwd=False):
    """data_dir のコピーを作り、その中で command を実行する。"""
    tmp = tempfile.mkdtemp(prefix="unixdrill_")
    work = os.path.join(tmp, "playground")
    try:
        shutil.copytree(data_dir, work)
        before = snapshot(work)
        script = command
        marker = "___DRILL_CWD___"
        if capture_cwd:
            script = "{\n%s\n}\nprintf '\\n%s%%s' \"$PWD\"" % (command, marker)
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        env["LANG"] = "C.UTF-8"
        try:
            proc = subprocess.run(
                ["bash", "-c", script], cwd=work, env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return RunResult(timeout=True, error="時間切れ (%d 秒)" % TIMEOUT)
        stdout = proc.stdout
        cwd = ""
        # macOS では /var が /private/var へのシンボリックリンクなので、
        # bash が報告する $PWD と Python が持つパスの表記が食い違う。
        # 両方を実体パスに揃えてから比べる。
        work_real = os.path.realpath(work)
        if capture_cwd and marker in stdout:
            stdout, _, tail = stdout.rpartition(marker)
            stdout = stdout.rstrip("\n")
            tail = tail.strip()
            if tail:
                try:
                    cwd = os.path.relpath(os.path.realpath(tail), work_real)
                except ValueError:
                    cwd = tail
        # 一時ディレクトリのパスは実行ごとに変わるので、固定の名前に置き換える
        stderr = proc.stderr
        for path in (work_real, work):
            stdout = stdout.replace(path, "/playground")
            stderr = stderr.replace(path, "/playground")
        after = snapshot(work)
        changed = {k: v for k, v in after.items()
                   if k not in before or before[k] != v}
        removed = sorted(set(before) - set(after))
        for k in removed:
            changed["!deleted:" + k] = ""
        return RunResult(stdout=stdout, stderr=stderr,
                         returncode=proc.returncode, cwd=cwd, files=changed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
