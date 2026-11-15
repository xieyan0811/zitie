#!/usr/bin/env python3
"""米字格练字帖生成器（按笔顺拆字版）

字形不依赖任何字体文件：按字从 hanzi-writer-data（makemeahanzi 数据）取笔画 SVG 路径，
解析后直接画进 PDF，所以每一笔都能单独控制，可以逐笔累加展示笔顺。

版面：每个字占两行，每行 cols 格。
  第一行：首格黑字字头 -> 之后逐笔累加（第 1 笔、前 2 笔…）-> 余下淡灰整字描红
  第二行：首格黑字字头 -> 余下全部空白，孩子自己写
"""

import argparse
import json
import os
import re
import urllib.parse
import urllib.request

import fitz

MM = 72 / 25.4
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "hanzi")
CDN = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/{}.json"

BLACK = (0, 0, 0)
TRACE = (0.76, 0.76, 0.76)
GRID = (0.32, 0.32, 0.32)
DASH = (0.55, 0.55, 0.55)

TOKEN = re.compile(r"[MLQCZ]|-?\d*\.?\d+")
ARGC = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}


# ---------------------------------------------------------------- 数据
def load_char(ch):
    path = os.path.join(CACHE, ch + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    os.makedirs(CACHE, exist_ok=True)
    url = CDN.format(urllib.parse.quote(ch))
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise SystemExit("取不到 {} 的笔画数据：{}（检查网络或该字是否不在数据集中）".format(ch, e))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def parse_path(d):
    segs, cmd, nums = [], None, []

    def flush():
        if cmd is None:
            return
        n = ARGC[cmd]
        if n == 0:
            segs.append(("Z", []))
            return
        for i in range(0, len(nums) - n + 1, n):
            vals = nums[i : i + n]
            segs.append((cmd, [(vals[j], vals[j + 1]) for j in range(0, n, 2)]))

    for m in TOKEN.finditer(d):
        s = m.group(0)
        if s.isalpha():
            flush()
            cmd, nums = s, []
        else:
            nums.append(float(s))
    flush()
    return segs


# ---------------------------------------------------------------- 绘制
def stroke_shape(sh, segs, tx):
    cur = start = None
    for cmd, pts in segs:
        if cmd == "M":
            cur = start = pts[0]
        elif cmd == "L":
            sh.draw_line(tx(cur), tx(pts[0]))
            cur = pts[0]
        elif cmd == "Q":
            c, p = pts[0], pts[1]
            c1 = (cur[0] + 2 / 3 * (c[0] - cur[0]), cur[1] + 2 / 3 * (c[1] - cur[1]))
            c2 = (p[0] + 2 / 3 * (c[0] - p[0]), p[1] + 2 / 3 * (c[1] - p[1]))
            sh.draw_bezier(tx(cur), tx(c1), tx(c2), tx(p))
            cur = p
        elif cmd == "C":
            sh.draw_bezier(tx(cur), tx(pts[0]), tx(pts[1]), tx(pts[2]))
            cur = pts[2]
        elif cmd == "Z":
            sh.draw_line(tx(cur), tx(start))
            cur = start


EM_W, EM_H = 870.0, 745.0  # 常用字在笔画数据里的平均字身宽高
XC, YC = 517.0, 406.0  # 字身在 1024 框里的平均中心，用来把字摆到格子正中


def draw_char(page, data, left, bot, size, color, upto=None, fill_ratio=0.76):
    """在左下角为 (left, bot) 的格子里画字；upto 只画前 upto 笔，用于笔顺。"""
    pad = size * 0.02
    scale = (size - 2 * pad) / 1024.0
    k = fill_ratio * 1024.0 / EM_W  # 让字宽占到格子的 fill_ratio

    def tx(p):
        x = 512 + (p[0] - XC) * k
        y = 512 + (p[1] - YC) * k
        return (left + pad + x * scale, bot - pad - y * scale)

    strokes = data["strokes"]
    if upto is not None:
        strokes = strokes[:upto]
    for d in strokes:
        sh = page.new_shape()
        stroke_shape(sh, parse_path(d), tx)
        sh.finish(color=None, fill=color, closePath=True)
        sh.commit()


def draw_grid(page, left, bot, size):
    x0, y0, x1, y1 = left, bot - size, left + size, bot
    sh = page.new_shape()
    sh.draw_rect(fitz.Rect(x0, y0, x1, y1))
    sh.finish(color=GRID, width=0.7)
    sh.commit()

    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    sh = page.new_shape()
    for a, b in [
        ((mx, y0), (mx, y1)),
        ((x0, my), (x1, my)),
        ((x0, y1), (x1, y0)),
        ((x0, y0), (x1, y1)),
    ]:
        sh.draw_line(a, b)
    sh.finish(color=DASH, width=0.5, dashes="[2.2 2.2] 0")
    sh.commit()


# ---------------------------------------------------------------- 版面
def layout(per_page, size, margin_top, inner_gap, group_gap):
    """返回每页每字块的顶边 y（fitz 坐标，y 向下）。块高 = 2*size + inner_gap。"""
    block = 2 * size + inner_gap
    return [margin_top + i * (block + group_gap) for i in range(per_page)]


def draw_double_row(page, ch, cols, size, margin_x, block_top, inner_gap, fill_ratio):
    data = load_char(ch)
    n = len(data["strokes"])

    # 第一行：笔顺
    bot = block_top + size
    for c in range(cols):
        left = margin_x + c * size
        draw_grid(page, left, bot, size)
        if c == 0:
            draw_char(page, data, left, bot, size, BLACK, fill_ratio=fill_ratio)
        elif c - 1 < n:
            draw_char(page, data, left, bot, size, TRACE, upto=c, fill_ratio=fill_ratio)
        else:
            draw_char(page, data, left, bot, size, TRACE, fill_ratio=fill_ratio)

    # 第二行：首字示例 + 空白
    bot = block_top + 2 * size + inner_gap
    for c in range(cols):
        left = margin_x + c * size
        draw_grid(page, left, bot, size)
        if c == 0:
            draw_char(page, data, left, bot, size, BLACK, fill_ratio=fill_ratio)


def build(chars, cols, per_page, size_mm, margin_mm, inner_gap_mm, group_gap_mm, fill_ratio, out, preview):
    size = size_mm * MM
    margin = margin_mm * MM
    inner_gap = inner_gap_mm * MM
    group_gap = group_gap_mm * MM
    page_w, page_h = 210 * MM, 297 * MM
    margin_x = (page_w - cols * size) / 2

    doc = fitz.open()
    groups = [chars[i : i + per_page] for i in range(0, len(chars), per_page)] or [""]

    for group in groups:
        page = doc.new_page(width=page_w, height=page_h)
        tops = layout(len(group), size, margin, inner_gap, group_gap)
        for i, ch in enumerate(group):
            if ch.strip():
                draw_double_row(page, ch, cols, size, margin_x, tops[i], inner_gap, fill_ratio)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    doc.save(out)
    doc.close()

    if preview:
        d = fitz.open(out)
        d[0].get_pixmap(dpi=110).save(preview)
        d.close()


def main():
    ap = argparse.ArgumentParser(description="生成米字格练字帖（带笔顺拆字）")
    ap.add_argument("--chars", default="天地人你我", help="要练的字，按顺序；也可写 @文件名")
    ap.add_argument("--cols", type=int, default=10, help="每行格子数")
    ap.add_argument("--per-page", type=int, default=5, help="每页几个字（每个字占两行）")
    ap.add_argument("--size-mm", type=float, default=19.0, help="格子边长（mm）")
    ap.add_argument("--margin-mm", type=float, default=12.0, help="上下页边距（mm）")
    ap.add_argument("--inner-gap-mm", type=float, default=0.0, help="同一字的笔顺行与练习行之间留缝")
    ap.add_argument("--group-gap-mm", type=float, default=7.0, help="不同字之间的间距")
    ap.add_argument("--fill-ratio", type=float, default=0.76, help="字宽占格子的比例，越小字越小")
    ap.add_argument(
        "-o", "--out", default=os.path.join(ROOT, "output", "zitie.pdf"), help="输出 PDF 的路径"
    )
    ap.add_argument("--preview", default=os.path.join(ROOT, "output", "zitie.png"))
    a = ap.parse_args()

    chars = a.chars
    if chars.startswith("@"):
        with open(chars[1:], encoding="utf-8") as f:
            chars = f.read()
    chars = re.sub(r"\s+", "", chars)

    build(
        chars,
        a.cols,
        a.per_page,
        a.size_mm,
        a.margin_mm,
        a.inner_gap_mm,
        a.group_gap_mm,
        a.fill_ratio,
        a.out,
        a.preview,
    )
    print("done:", a.out, "共", len(chars), "字")


if __name__ == "__main__":
    main()
