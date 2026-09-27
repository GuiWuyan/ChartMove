# ChartGen(chartgen)

**中文数据图表生成器 —— 人可用、AI 可调。** matplotlib 内核,16 种图表 × 13 主题(4 风格包),输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)两个,未来作为桌宠 agent 的出图插件。原 PPT / PDF / Word 文档生成能力已移除;GUI 入口已取消(2026-09-27),PPT 由独立的 PPT Master 项目承担。

## 目录结构

```
├─ src/chartgen/     # 包:core 内核 + themes / fonts / output + cli / mcp_server(待 M3)
├─ tests/            # 16 图 × 3 输出 smoke test 矩阵 + CLI / 单元测试
├─ examples/         # make_all.py:一条命令生成全部 16 种示例图,兼任用法文档
└─ docs/plan.md      # 开发方案
```

## CLI

```bash
chartgen bar "季度产量" Q1=120 Q2=200 Q3=90 --style mckinsey
chartgen line "月度增长" --data data.json        # {"categories": [...], "values": [...]}
chartgen line-multi "对比" --categories 1月,2月,3月 --series series.json
chartgen combo "销量与客单价" Q1=120 Q2=200 --line 86,92,78,105
chartgen scatter "分布" --x 1,2,3 --y 5,7,6 --trend
chartgen hist "响应时长" 12 15 18 22 --bins 8
chartgen box "A/B 测试" --series samples.json    # [["对照组", [3.1, ...]], ...]
chartgen heatmap "热力" --data heat.json         # {"rows": [...], "cols": [...], "values": [[...]]}
chartgen bar "Top 城市" 上海=30 北京=25 --horizontal
chartgen themes                                  # 13 主题 × 4 风格包
```

**表格文件直接出图**(`--file`,支持 .csv 与 .xlsx,首行为表头;`--style` 等通用参数照常可用):

```bash
chartgen bar "季度销量" --file sales.csv --style cyberpunk   # 第 1 列类目,其余列数值
chartgen line "趋势" --file sales.xlsx --style academic      # 多数值列时 bar/line 自动转多系列图
chartgen combo "双轴" --file dual.csv                        # 第 2 列柱值、第 3 列折线值
chartgen box "分布" --file samples.csv                       # 每列一组,表头 = 组名
chartgen scatter "相关" --file xy.csv                        # 列顺序 x, y(, sizes)(, labels)
chartgen heatmap "热力" --file matrix.csv --style terminal   # 首列为行名,首行为列表头
chartgen hist "分布" --file samples.csv                      # 第 1 列为原始样本
```

通用参数:`--style` / `--animate`(默认 GIF)/ `--fmt png|gif|mp4|pdf|tif` / `--out-dir` / `--out` / `--dpi` / `--figsize 宽x高`;`--data` / `--series` 接内联 JSON 字符串或文件路径。CSV 兼容 UTF-8 与 GBK 编码。

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
- 输出:PNG / PDF(矢量)/ TIF(600dpi,期刊投稿)/ GIF("数据生长"动画,播一遍停末帧,适配 PPT 放映与聊天窗)/ MP4(需 ffmpeg);`figsize` / `dpi` 参数化,默认 16:9 / 150dpi(1920×1080)
- 差异化:最大/最小值自动高亮、y 轴智能从 0 起、中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK,见 fonts.py)
- 输出目录:默认项目内 `./Results/`(持久,不做 TTL 清理);优先级 `out_dir=` / `--out-dir` 参数 > 环境变量 `CHARTGEN_OUT_DIR` > 默认
- 表格直读:CLI `--file` 支持 CSV(UTF-8 / GBK)与 Excel(.xlsx),见 table.py

依赖:matplotlib、mcp(官方 SDK,2.x 起 API 为 `MCPServer`)、pillow、openpyxl(Excel 读取)、pywin32(Windows)。
