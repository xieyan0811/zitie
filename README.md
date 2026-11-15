# zitie

![在 WorkBuddy 里安装这个 skill 并生成字帖](assets/preview.png)

米字格练字帖生成 Skill。输入一串汉字，直接输出可打印的 A4 PDF。

每个字占两行：第一行第 1 格是黑色字头，后面按笔顺逐笔累加（浅灰），剩余格放完整浅灰字供描红；第二行第 1 格是黑色字头，其余 9 格留空供练习。

## 安装 Skill

直接把仓库地址发给你的 Agent：

```text
帮我安装一个 skill：github.com/xieyan0811/zitie
```

也可以手动克隆到对应 Agent 的 skills 目录（如 `~/.claude/skills/zitie`、`~/.workbuddy/skills/zitie`、`~/.codebuddy/skills/zitie`、`~/.copilot/skills/zitie`），并安装唯一依赖：

```bash
pip install pymupdf
```

## 怎么用

装好后直接跟 Agent 说需求就行，不用记命令参数：

- 给一年级出个字帖，字是「人不在我是」
- 帮我生成米字格字帖练名字，名字是「张一鸣」，重复三遍
- 按生字表出一份字帖，每页 5 个字

也可以直接跑命令行：

```bash
python3 src/make_zitie.py --chars 天地人你我 -o output/zitie.pdf
```

默认每行 10 格（最多展示 9 笔）。遇到 10 画以上的字，Agent 会自动按 `SKILL.md` 里的规则调整列数和格宽；手动调参可查看 `SKILL.md`。

## 原理与许可

字形笔画数据按需从 `hanzi-writer-data`（源自 makemeahanzi）抓取并缓存在本地 `data/hanzi/`，把 SVG 路径换算成贝塞尔曲线后由 PyMuPDF 直接绘制到 PDF。

- 代码按 MIT 协议开源，见 `LICENSE`。
- 笔画数据归原作者所有，遵循 Arphic Public License。

