# ChartGen(chartgen)

**数据图表生成器** 
matplotlib 内核,16 种图表 × 13 主题(4 风格包),输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)

## 目录结构

```
├─ src/chartgen/     # 包:core 内核 + themes / fonts / output + cli / mcp_server(待 M3)
├─ tests/            # 16 图 × 3 输出 smoke test 矩阵 + CLI / 单元测试
├─ examples/         # make_all.py:一条命令生成全部 16 种示例图,兼任用法文档
└─ docs/plan.md      # 开发方案
```

## CLI

命令结构:**`chartgen <类型> "标题" [数据] [通用参数] [类型专属参数]`**,输出文件绝对路径,默认写入 `./Results/`。

16 种类型:`bar` / `line` / `line-multi` / `area` / `pie` / `donut` / `combo` / `bar-multi` / `radar` / `scatter` / `bubble` / `hist` / `box` / `heatmap` / `waterfall` / `funnel`(多词类型用 kebab-case;`chartgen --help` 看总览,`chartgen bar --help` 看单类型全部参数)。

**数据的四种写法**(按类型任选其一,`--file` 优先级最高):

| 方式 | 适用类型 | 示例 |
|---|---|---|
| 内联 `类目=值` | 单系列类目型 | `chartgen bar "季度产量" Q1=120 Q2=200` |
| `--data` JSON(内联字符串或文件路径) | 单系列 | `--data '{"categories":["Q1"],"values":[120]}'` 或 `--data data.json` |
| `--series` JSON + `--categories` | 多系列:`line-multi` / `bar-multi` / `radar` / `box` | `--series '[["销售额",[1,2]],...]'`(也接受 `{名称: [值...]}`) |
| `--file` CSV / Excel | 全部类型 | `--file sales.csv --cat-col 基金名称 --col "盈亏率(%)"` |

**通用参数**:

| 参数 | 说明 |
|---|---|
| `--style` | 13 主题 × 4 风格包,默认 business;`chartgen themes` 列出全部 |
| `--animate` | 出"数据生长"动画(默认 GIF,`--fmt mp4` 可出 MP4) |
| `--loop` | 配合 `--animate`:GIF 无限循环(默认播一遍停在末帧;MP4 循环由播放器决定,不支持) |
| `--fmt` | `png`(静态默认)/ `pdf` 矢量 / `tif` 600dpi / `gif`(动画默认)/ `mp4` |
| `--out-dir` / `--out` | 输出目录(默认 `./Results/`)/ 输出文件名(默认 `类型_标题`) |
| `--dpi` / `--figsize` | 分辨率 / 画幅 `宽x高`(如 `12.8x7.2`) |
| `--file` | CSV / Excel(.csv/.xlsx,首行为表头;CSV 兼容 UTF-8 与 GBK) |
| `--cat-col` / `--col` | 配合 `--file`:指定类目列 / 挑选数值列(表头名或从 1 数的序号) |

**类型专属参数**:

| 类型 | 参数 |
|---|---|
| `bar` | `--horizontal` 横向条形(排名场景) |
| `combo` | `--line` 折线值(逗号分隔)、`--bar-name` / `--line-name` 图例名 |
| `line-multi` | `--no-value-labels` 关闭数值标注 |
| `scatter` / `bubble` | `--x` `--y` 数值列表(逗号分隔)、`--trend` 趋势线、`--labels` 逐点标注、bubble 加 `--sizes` 气泡大小 |
| `hist` | `--bins` 分箱数(整数或 `auto`) |
| `waterfall` | `--no-total` 不追加合计柱 |
| `heatmap` | `--no-annotate` 不在格子标数值 |

**`--file` 列约定**(CSV / Excel,首行表头;CSV 兼容 UTF-8 与 GBK):默认第 1 列类目、其余列数值,多数值列时 bar/line 自动转多系列图(系列名 = 表头);combo 取类目列后两列(柱、线);box 每列一组(表头 = 组名);scatter/bubble 按 x, y(, sizes)(, labels) 取列;heatmap 类目列 = 行名、表头 = 列名;hist 第 1 列为原始样本;宽表用 `--cat-col` / `--col` 选列。

```bash
chartgen bar "季度产量" Q1=120 Q2=200 Q3=90 --style mckinsey                  # 内联数据
chartgen line "盈亏率" --file 基金.csv --cat-col 基金名称 --col "盈亏率(%)" --style cyberpunk   # 表格选列
chartgen themes                                  # 查看 13 主题 × 4 风格包
```

## MCP Server(AI / agent 接入)

stdio 传输,工具面收敛为 2 个;工具描述为英文(LLM 选工具靠它),数据校验错误以中文 `ToolError` 返回:

| 工具 | 参数 | 返回 |
|---|---|---|
| `make_chart` | `type`(16 种枚举)、`title`、`categories` / `values`(单系列)、`series`(多系列)、`x` / `y` / `sizes`(散点 / 气泡)、`rows` / `cols` / `matrix`(热力图)、`style`(默认 business)、`animate`(默认 false,出 GIF)、`loop`(默认 false,GIF 无限循环;仅 GIF 生效)、`fmt`(png/pdf/tif/gif/mp4)、`out` / `out_dir` | JSON:`{path(绝对路径,即交付物), file_size, type, style, animated}` |
| `list_themes` | 无 | 13 主题 × 4 风格包:名称 + 中文标签 + 一句话描述 |

## 开发环境

```bash
py -3.13 -m venv .venv                              # Python >=3.10
.venv/Scripts/python.exe -m pip install -e ".[dev]" # 可编辑安装 + pytest/ruff
.venv/Scripts/python.exe -m pytest                  # smoke test(全量约 1.5 分钟)
.venv/Scripts/python.exe -m ruff check src tests examples
python examples/make_all.py                         # 9 张示例图写入 ~/ChartGen/
winget install Gyan.FFmpeg                          # 可选,仅 MP4 动画需要
```

CI:push / PR 自动跑 ruff lint + pytest smoke test,见 `.github/workflows/ci.yml`。

## 图表能力

- 16 种类型:`bar`(支持 `horizontal=True` 横向条形)/ `line` / `line_multi` / `area` / `pie` / `donut` / `combo` / `bar_multi` / `radar` / `scatter`(可选趋势线)/ `bubble` / `hist` / `box` / `heatmap` / `waterfall` / `funnel`(自动逐级转化率)
- 13 套主题 × 4 风格包(默认 `business` 商务极简):
  - **学术包**:`academic` 学术Ticks标准风 / `grayscale` 灰度单色学术 / `ggplot` 复古统计 / `colorblind` 色盲无障碍(Okabe-Ito)
  - **商务包**:`business` 商务极简 / `mckinsey` 麦肯锡 / `dashboard` 深色看板
  - **简约演示包**:`whitegrid` 白底网格 / `minimal` 纯极简无脊线 / `morandi` 莫兰迪低饱和
  - **其他风格包**:`sketch` 手绘草图(xkcd 式) / `terminal` 暗黑程序员 / `cyberpunk` 赛博朋克霓虹
  - 主题元数据 `THEME_PACKS` / `THEME_LABELS` / `THEME_DESCS` 供 CLI `themes` 子命令与 MCP `list_themes` 使用
- 输出:PNG / PDF(矢量)/ TIF(600dpi,期刊投稿)/ GIF("数据生长"动画,默认播一遍停末帧适配 PPT 放映与聊天窗,`--loop` / `loop=true` 可无限循环)/ MP4(需 ffmpeg,循环由播放器决定);`figsize` / `dpi` 参数化,默认 16:9 / 150dpi(1920×1080)
- 差异化:最大/最小值自动高亮、y 轴智能从 0 起、中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK,见 fonts.py)
- 输出目录:默认项目内 `./Results/`(持久,不做 TTL 清理);优先级 `out_dir=` / `--out-dir` 参数 > 环境变量 `CHARTGEN_OUT_DIR` > 默认
- 表格直读:CLI `--file` 支持 CSV(UTF-8 / GBK)与 Excel(.xlsx),见 table.py

依赖:matplotlib、mcp(官方 SDK,2.x 起 API 为 `MCPServer`)、pillow、openpyxl(Excel 读取)、pywin32(Windows)。
