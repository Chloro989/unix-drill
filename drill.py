#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UNIX コマンド練習ドリル — 入口。

    python3 drill.py            ドリルモードを始める
    python3 drill.py help       使い方
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drill.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
