# -*- coding: utf-8 -*-
"""練習用データを生成する。

テーマを差し替えても問題文が壊れないよう、ファイルは「役割 (role)」で参照する。
問題定義では {table} {bigtext} {log} … と書き、実行時に実ファイル名へ置換される。

役割一覧:
  list      重複を含む短い一覧 (sort / uniq 用)
  table     ヘッダー付きタブ区切り表、数百行
  bigtext   数千行の行指向テキスト (head / less / wc の必要性を体感する)
  records   ヘッダー付き CSV
  log       INFO / WARNING / ERROR が混じるログ
  fileA     連結用の小さいファイル その1
  fileB     連結用の小さいファイル その2
  notesdir  サブディレクトリ (隠しファイルを含む)
  notesfile notesdir の中のテキスト
用語 (terms):
  item  1 行が表す物の呼び名 (遺伝子 / リクエスト / 本)
  unit  bigtext の 1 かたまりの呼び名
"""

import os
import random


def _w(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


PATTERN_LINES = [
    "ACGT", "ACT", "AT", "AGT", "ACGGCT", "AAT", "CGT", "ACGCGT",
    "ATT", "ACGTT", "TACGT", "GATTACA", "A", "T", "ATTT", "ACATGT",
    "cat", "catalog", "concat", "dog", "bird",
    "ID-001", "ID-42", "id-7", "ID-",
    "AB12", "XY9",
    "2026-05-01", "2026-5-1", "20260501",
    "hello world",
]


def _build_common(root):
    """どのテーマでも内容が同じファイル。正規表現の練習に使う。"""
    _w(os.path.join(root, "patterns.txt"), PATTERN_LINES)


# ---------------------------------------------------------------- bio
def _build_bio(root, rnd):
    genes = ["TP53", "BRCA1", "BRCA2", "EGFR", "MYC", "GAPDH", "ACTB", "KRAS",
             "PTEN", "RB1", "APC", "VHL", "MLH1", "MSH2", "CDKN2A", "NOTCH1",
             "PIK3CA", "SMAD4", "STK11", "ATM"]

    # list: 重複ありの遺伝子名一覧
    lst = []
    for _ in range(40):
        lst.append(rnd.choice(genes[:10]))
    _w(os.path.join(root, "genelist.txt"), lst)

    # table: 発現量テーブル 500 行
    rows = ["gene_id\tsymbol\tbaseMean\tlog2FC\tpvalue\tchromosome"]
    for i in range(500):
        sym = rnd.choice(genes) + str(rnd.randint(1, 9))
        rows.append("ENSG%08d\t%s\t%.2f\t%.3f\t%.5f\tchr%s" % (
            i + 1, sym, rnd.uniform(1, 5000), rnd.uniform(-6, 6),
            rnd.random() ** 3, rnd.choice(list(range(1, 23)) + ["X", "Y"])))
    _w(os.path.join(root, "expression.tsv"), rows)

    # bigtext: FASTQ 1000 リード = 4000 行
    fq = []
    for i in range(1000):
        seq = "".join(rnd.choice("ACGT") for _ in range(60))
        qual = "".join(chr(33 + rnd.randint(20, 40)) for _ in range(60))
        fq += ["@READ%05d/1" % (i + 1), seq, "+", qual]
    _w(os.path.join(root, "reads.fastq"), fq)

    # records: 検体 CSV
    rec = ["sample_id,age,sex,tissue,diagnosis,biomarker"]
    for i in range(120):
        rec.append("S%03d,%d,%s,%s,%s,%.1f" % (
            i + 1, rnd.randint(28, 88), rnd.choice("MF"),
            rnd.choice(["lung", "liver", "breast", "colon", "brain"]),
            rnd.choice(["control", "stage1", "stage2", "stage3"]),
            rnd.uniform(0.1, 99.9)))
    _w(os.path.join(root, "samples.csv"), rec)

    # log
    _w(os.path.join(root, "pipeline.log"), _gen_log(rnd, 3000,
        ["align", "sort", "markdup", "callvar", "annotate"]))

    # fileA / fileB
    _w(os.path.join(root, "seqA.fasta"),
       [">geneA_%d" % i for i in range(1)] +
       ["ATGCGTACGTTAGCCTAGGCTA", "CCGTAGCTAGCTAGCTAGCTAA"])
    _w(os.path.join(root, "seqB.fasta"),
       [">geneB_1", "ATGAAACCCGGGTTTACGTACG", "TTGACGTAGCTTACGGATCCAA"])

    # notes
    _w(os.path.join(root, "notes", "memo.txt"),
       ["2026-04-01 シーケンス受領", "2026-04-02 QC 実施", "担当: 中村"])
    _w(os.path.join(root, "notes", ".hidden_protocol.txt"),
       ["非公開プロトコル", "PCR サイクル数: 32"])

    return {
        "files": {
            "list": "genelist.txt", "table": "expression.tsv",
            "bigtext": "reads.fastq", "records": "samples.csv",
            "log": "pipeline.log", "fileA": "seqA.fasta", "fileB": "seqB.fasta",
            "notesdir": "notes", "notesfile": "notes/memo.txt",
            "strings": "patterns.txt",
        },
        "terms": {"item": "遺伝子", "unit": "リード", "dataset": "RNA-seq 解析結果",
                  "listitem": "遺伝子名",
                  "namecol": "2", "numcol": "3", "catcol": "6", "agecol": "2",
                  "headword": "gene_id", "namelabel": "symbol",
                  "numlabel": "baseMean", "catlabel": "chromosome",
                  "numthr": "1000"},
    }


# ---------------------------------------------------------------- logs
def _build_logs(root, rnd):
    paths = ["/", "/login", "/api/user", "/api/order", "/static/app.js",
             "/health", "/admin", "/search", "/cart", "/logout"]

    _w(os.path.join(root, "endpoints.txt"),
       [rnd.choice(paths[:6]) for _ in range(40)])

    rows = ["date\tendpoint\thits\tavg_ms\terrors\tregion"]
    for i in range(500):
        rows.append("2026-%02d-%02d\t%s\t%d\t%.1f\t%d\t%s" % (
            rnd.randint(1, 6), rnd.randint(1, 28), rnd.choice(paths),
            rnd.randint(1, 90000), rnd.uniform(3, 900), rnd.randint(0, 300),
            rnd.choice(["ap-northeast", "us-east", "eu-west"])))
    _w(os.path.join(root, "traffic.tsv"), rows)

    acc = []
    for _ in range(4000):
        acc.append('%d.%d.%d.%d - [2026-05-%02d:%02d:%02d:%02d] "GET %s" %s %d' % (
            rnd.randint(10, 220), rnd.randint(0, 255), rnd.randint(0, 255),
            rnd.randint(1, 254), rnd.randint(1, 28), rnd.randint(0, 23),
            rnd.randint(0, 59), rnd.randint(0, 59), rnd.choice(paths),
            rnd.choice([200, 200, 200, 301, 404, 500]), rnd.randint(120, 90000)))
    _w(os.path.join(root, "access.log"), acc)

    rec = ["user_id,age,plan,country,signup,active_days"]
    for i in range(120):
        rec.append("U%03d,%d,%s,%s,2026-%02d-%02d,%d" % (
            i + 1, rnd.randint(18, 75),
            rnd.choice(["free", "pro", "team", "enterprise"]),
            rnd.choice(["JP", "US", "DE", "IN"]),
            rnd.randint(1, 6), rnd.randint(1, 28), rnd.randint(0, 400)))
    _w(os.path.join(root, "users.csv"), rec)

    _w(os.path.join(root, "app.log"), _gen_log(rnd, 3000,
        ["auth", "db", "cache", "worker", "mailer"]))

    _w(os.path.join(root, "partA.txt"), ["alpha サーバ設定", "port = 8080"])
    _w(os.path.join(root, "partB.txt"), ["beta サーバ設定", "port = 9090"])

    _w(os.path.join(root, "notes", "memo.txt"),
       ["2026-05-01 障害調査開始", "2026-05-02 原因特定", "担当: 佐藤"])
    _w(os.path.join(root, "notes", ".hidden_credentials.txt"),
       ["非公開メモ", "staging の URL は社内 wiki 参照"])

    return {
        "files": {
            "list": "endpoints.txt", "table": "traffic.tsv",
            "bigtext": "access.log", "records": "users.csv",
            "log": "app.log", "fileA": "partA.txt", "fileB": "partB.txt",
            "notesdir": "notes", "notesfile": "notes/memo.txt",
            "strings": "patterns.txt",
        },
        "terms": {"item": "エンドポイント", "unit": "アクセス", "dataset": "アクセス解析",
                  "listitem": "パス名",
                  "namecol": "2", "numcol": "3", "catcol": "6", "agecol": "2",
                  "headword": "date", "namelabel": "endpoint",
                  "numlabel": "hits", "catlabel": "region",
                  "numthr": "1000"},
    }


# ---------------------------------------------------------------- general
def _build_general(root, rnd):
    fruits = ["りんご", "みかん", "ぶどう", "もも", "いちご", "なし", "かき", "びわ"]
    authors = ["夏目漱石", "宮沢賢治", "太宰治", "森鴎外", "樋口一葉", "芥川龍之介"]

    _w(os.path.join(root, "kaimono.txt"), [rnd.choice(fruits) for _ in range(40)])

    rows = ["book_id\ttitle\tauthor\tyear\tpages\tgenre"]
    for i in range(500):
        rows.append("%d\t作品%03d\t%s\t%d\t%d\t%s" % (
            i + 1, i + 1, rnd.choice(authors), rnd.randint(1890, 2025),
            rnd.randint(80, 900),
            rnd.choice(["小説", "随筆", "詩集", "評論", "児童"])))
    _w(os.path.join(root, "books.tsv"), rows)

    diary = []
    for i in range(3500):
        diary.append("2026-%02d-%02d %02d:%02d %s" % (
            rnd.randint(1, 6), rnd.randint(1, 28), rnd.randint(6, 23),
            rnd.randint(0, 59),
            rnd.choice(["読書 30分", "散歩した", "コーヒーを淹れた",
                        "写経した", "早く寝た", "映画を観た"])))
    _w(os.path.join(root, "diary.txt"), diary)

    rec = ["member_id,age,name,city,joined,points"]
    for i in range(120):
        rec.append("M%03d,%d,会員%03d,%s,2026-%02d-%02d,%d" % (
            i + 1, rnd.randint(15, 80), i + 1,
            rnd.choice(["東京", "大阪", "札幌", "福岡"]),
            rnd.randint(1, 6), rnd.randint(1, 28), rnd.randint(0, 5000)))
    _w(os.path.join(root, "members.csv"), rec)

    _w(os.path.join(root, "system.log"), _gen_log(rnd, 3000,
        ["backup", "index", "sync", "cleanup", "report"]))

    _w(os.path.join(root, "zenhan.txt"), ["第一章 はじめに", "ここから始まる。"])
    _w(os.path.join(root, "kohan.txt"), ["第二章 おわりに", "ここで終わる。"])

    _w(os.path.join(root, "notes", "memo.txt"),
       ["2026-03-01 蔵書整理を開始", "2026-03-05 目録を作成", "担当: 田中"])
    _w(os.path.join(root, "notes", ".hidden_wishlist.txt"),
       ["非公開の欲しい物リスト", "全集 第3巻"])

    return {
        "files": {
            "list": "kaimono.txt", "table": "books.tsv",
            "bigtext": "diary.txt", "records": "members.csv",
            "log": "system.log", "fileA": "zenhan.txt", "fileB": "kohan.txt",
            "notesdir": "notes", "notesfile": "notes/memo.txt",
            "strings": "patterns.txt",
        },
        "terms": {"item": "本", "unit": "日記の行", "dataset": "蔵書と日記の記録",
                  "listitem": "品名",
                  "namecol": "2", "numcol": "5", "catcol": "6", "agecol": "2",
                  "headword": "book_id", "namelabel": "title",
                  "numlabel": "pages", "catlabel": "genre",
                  "numthr": "500"},
    }


def _gen_log(rnd, n, mods):
    out = []
    for i in range(n):
        lvl = rnd.choice(["INFO"] * 8 + ["WARNING"] * 2 + ["ERROR"])
        out.append("2026-05-%02d %02d:%02d:%02d %s [%s] step %d %s" % (
            rnd.randint(1, 28), rnd.randint(0, 23), rnd.randint(0, 59),
            rnd.randint(0, 59), lvl, rnd.choice(mods), i,
            {"INFO": "completed", "WARNING": "retrying",
             "ERROR": "failed"}[lvl]))
    return out


BUILDERS = {"bio": _build_bio, "logs": _build_logs, "general": _build_general}
THEME_LABELS = {"bio": "生命科学データ", "logs": "サーバーログ", "general": "蔵書と日記"}


def build(theme, root, seed=20260802):
    if theme not in BUILDERS:
        raise ValueError("未知のテーマ: %s" % theme)
    os.makedirs(root, exist_ok=True)
    manifest = BUILDERS[theme](root, random.Random(seed))
    _build_common(root)
    return manifest
