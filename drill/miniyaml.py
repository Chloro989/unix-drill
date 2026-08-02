# -*- coding: utf-8 -*-
"""YAML のごく一部だけを解釈する最小パーサ。

外部ライブラリを一切使わないためのもの。対応するのは以下だけ:
  - マッピング (key: value)
  - ネストしたマッピング / リスト
  - リスト (- item), マッピングを要素に持つリスト
  - ブロックスカラー (key: |)
  - 引用符付きスカラー ("..." / '...')
  - 行頭 # のコメント行、空行

タブによるインデントは使えない。値の中の # はコメントとして扱わない。
"""


import re


class YamlError(Exception):
    pass


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


class _Parser:
    def __init__(self, text):
        self.lines = text.replace("\t", "    ").split("\n")
        self.i = 0

    # --- 低レベル ---
    def _skip_blank(self):
        while self.i < len(self.lines):
            s = self.lines[self.i].strip()
            if s == "" or s.startswith("#"):
                self.i += 1
            else:
                return

    def _peek(self):
        self._skip_blank()
        if self.i >= len(self.lines):
            return None, None
        line = self.lines[self.i]
        return _indent_of(line), line.strip()

    # --- スカラー ---
    @staticmethod
    def _scalar(raw):
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            return raw[1:-1]
        if raw in ("true", "True"):
            return True
        if raw in ("false", "False"):
            return False
        if raw in ("null", "~", ""):
            return None
        try:
            return int(raw)
        except ValueError:
            pass
        return raw

    def _block_scalar(self, parent_indent):
        """key: | の続きを読む。"""
        buf = []
        base = None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() == "":
                buf.append("")
                self.i += 1
                continue
            ind = _indent_of(line)
            if ind <= parent_indent:
                break
            if base is None:
                base = ind
            buf.append(line[base:] if len(line) >= base else line.strip())
            self.i += 1
        while buf and buf[-1] == "":
            buf.pop()
        return "\n".join(buf)

    # --- 構造 ---
    def parse_value_after_key(self, key_indent, inline):
        """key: の右側 inline を解釈する。空なら次のブロックを読む。"""
        if inline == "|":
            return self._block_scalar(key_indent)
        if inline != "":
            if inline.startswith("[") and inline.endswith("]"):
                body = inline[1:-1].strip()
                if not body:
                    return []
                return [self._scalar(p) for p in body.split(",")]
            return self._scalar(inline)
        # ブロック
        ind, _ = self._peek()
        if ind is None or ind <= key_indent:
            return None
        return self.parse_block(ind)

    def parse_block(self, indent):
        ind, text = self._peek()
        if ind is None:
            return None
        if text.startswith("- "):
            return self.parse_list(indent)
        return self.parse_map(indent)

    def parse_list(self, indent):
        out = []
        while True:
            ind, text = self._peek()
            if ind is None or ind != indent or not text.startswith("- "):
                break
            content = text[2:]
            # マッピングを要素に持つリストか判定
            key, sep, rest = content.partition(":")
            is_map = (sep == ":" and (rest == "" or rest.startswith(" "))
                      and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key.strip())
                      is not None)
            if is_map:
                # "- key: v" を "  key: v" に書き換えて通常のマッピングとして読む
                self.lines[self.i] = " " * (indent + 2) + content
                out.append(self.parse_map(indent + 2))
            else:
                self.i += 1
                out.append(self._scalar(content))
        return out

    def parse_map(self, indent):
        out = {}
        while True:
            ind, text = self._peek()
            if ind is None or ind != indent or text.startswith("- "):
                break
            key, sep, rest = text.partition(":")
            if sep != ":":
                raise YamlError("解釈できない行: %r" % text)
            key = key.strip()
            self.i += 1
            out[key] = self.parse_value_after_key(indent, rest.strip())
        return out


def loads(text):
    p = _Parser(text)
    ind, _ = p._peek()
    if ind is None:
        return None
    return p.parse_block(ind)


def load_file(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())
