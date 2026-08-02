#!/usr/bin/env bash
# UNIX コマンド練習ドリル — セットアップ
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 が見つかりません。先に Python 3 を入れてください。" >&2
  exit 1
fi

python3 drill.py setup
echo
echo "準備できました。次のどちらかで始めてください。"
echo
echo "  python3 drill.py          ← ドリルモード（問題が出て、その場で採点）"
echo "  cd playground             ← フィールドモード（本物のシェルで自由に練習）"
echo
