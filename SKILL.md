---
name: zitie
description: 生成中文米字格练字帖 PDF，按笔顺逐笔拆字（Chinese handwriting practice sheet generator）。当用户要给小朋友出字帖、练字纸、打印生字表、练写名字，或提到米字格、笔顺、描红、田字格时使用。输入一串汉字，输出可直接打印的 A4 PDF。
---

# 米字格笔顺字帖

输入一串汉字，输出 A4 练字帖 PDF。每个字占两行：第一行把字按笔顺逐笔拆开，第二行留白给孩子自己写。

## 环境

只需 Python 3 和 pymupdf。缺依赖时报 `ModuleNotFoundError: No module named 'fitz'`，装一下即可：

```bash
pip install pymupdf
```

## 一条命令

```bash
python3 <skill目录>/src/make_zitie.py --chars 天地人你我 -o 字帖.pdf
```

`<skill目录>` 换成这个 SKILL.md 所在目录的绝对路径，例如 `~/.claude/skills/zitie`。不想指定 -o 时默认写到 `output/zitie.pdf`。

## 版面规则

每行 10 格，每个字两行。

第一行第 1 格是黑色完整字头，第 2 格起按笔顺逐笔累加，全部浅灰；笔画画完后剩下的格子放浅灰整字，供描红。

第二行第 1 格还是黑色字头，其余 9 格空白。

## 参数

`--chars` 要练的字，按顺序连写。也可以写 `@生字表.txt`，文件里可以换行。

`--cols` 每行格子数，默认 10。

`--per-page` 每页几个字，默认 5。

`--size-mm` 格子边长，默认 19。

`--margin-mm` 上下页边距，默认 12。

`--inner-gap-mm` 同一个字两行之间的缝，默认 0。

`--group-gap-mm` 不同字之间的间距，默认 7。

`--fill-ratio` 字宽占格子的比例，默认 0.76，嫌字大就往下调。

`-o` / `--out` 输出 PDF 路径。

`--preview` 预览 PNG 路径，批量出片时传空串可以跳过。

## 出多课生字表

一课一页，用循环批量出：

```bash
while IFS='|' read -r name chars; do
  python3 <skill目录>/src/make_zitie.py --chars "$chars" -o "${name}_${chars}.pdf" --preview ""
done <<'EOF'
第一课|人不在我是
第二课|们有来他这
EOF
```

## 笔画多的字要改列数

每行 10 格、第 1 格是字头，笔顺最多只能画 9 笔。10 画及以上的字会在第 9 笔截断，最后一格不是完整的字。

遇到这种字（例如「就」「着」「家」「得」「起」「都」），把这一页换成 13 列、格子 14.6mm，笔顺就能画完：

```bash
python3 <skill目录>/src/make_zitie.py --chars 的就把好还 --cols 13 --size-mm 14.6 -o 第八课.pdf
```

## 硬约束

10 列乘 19mm 等于 190mm，正好是 A4 去掉 10mm 左右边距后的可用宽度，`--size-mm` 再大就会横向溢出纸张。

19mm 格子下一页最舒服是 5 个字，再多会挤出页面高度。

首次生成某个字要联网抓一次笔画数据（来自 jsdelivr 上的 hanzi-writer-data），之后缓存在本目录 `data/hanzi/`，离线可用。生僻字抓不到会直接报错退出，不会静默画个空字。

预览图会自动裁掉页面下半部分的空白。
