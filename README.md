# ChartMove

**中文数据图表生成器**:matplotlib 内核,24 种图表,15 套主题分属 4 个风格包,输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)。

## 目录结构

```
├─ src/chartmove/     # 图表内核 + themes / fonts / output + cli / mcp_server
├─ tests/            # 24 图 smoke test 矩阵 + CLI / 单元测试
└─ examples/         # make_all.py:一条命令生成全部类型示例图
```

## CLI

命令结构:**`chartmove <类型> "标题" [数据] [参数]`**,产物默认写入 `./Results/`(同名自动加序号,不覆盖)。

24 种类型:`bar` / `line` / `line-multi` / `area` / `pie` / `donut` / `rose` / `treemap` / `combo` / `bar-multi` / `radar` / `scatter` / `bubble` / `hist` / `box` / `violin` / `heatmap` / `waterfall` / `pareto` / `funnel` / `gantt` / `dumbbell` / `sankey` / `sunburst`(多词类型用 kebab-case;`chartmove --help` 看总览,`chartmove bar --help` 看单类型全部参数)。

**数据的四种写法**(按类型任选其一,`--file` 优先级最高):

| 方式 | 适用类型 | 示例 |
|---|---|---|
| 内联 `类目=值` | 单系列类目型 | `chartmove bar "季度产量" Q1=120 Q2=200` |
| `--data` JSON | 单系列 | `--data '{"categories":["Q1"],"values":[120]}'` 或 `--data data.json` |
| `--series` JSON + `--categories` | 多系列:`line-multi` / `bar-multi` / `radar` / `box` / `violin` | `--series '[["销售额",[1,2]],...]'`(也接受 `{名称: [值...]}`) |
| `--file` CSV / Excel | 全部类型 | `--file sales.csv --cat-col 基金名称 --col "盈亏率(%)"` |

**通用参数**:

| 参数 | 说明 |
|---|---|
| `--style` | 15 套主题,默认 business;`chartmove themes` 列出全部 |
| `--animate` / `--loop` | 出"数据生长"动画(默认 GIF)/ GIF 无限循环 |
| `--fmt` | `png`(静态默认)/ `pdf` 矢量 / `tif` 600dpi / `gif`(动画默认)/ `mp4`(需 ffmpeg) |
| `--out-dir` / `--out` | 输出目录 / 输出文件名(默认 `类型_标题`) |
| `--dpi` / `--figsize` | 分辨率 / 画幅 `宽x高` |
| `--numfmt` | 数值格式:`auto` 万/亿(默认)/ `plain` / `percent` |
| `--note` | 底部脚注(数据来源 / 备注) |
| `--file` / `--cat-col` / `--col` / `--sheet` | 表格直读:文件 / 类目列 / 数值列 / Excel 工作表 |

**类型专属参数**:

| 类型 | 参数 |
|---|---|
| `bar` | `--horizontal` 横向条形 |
| `bar-multi` | `--stacked` 堆积、`--percent` 百分比堆积(<4% 小段不标占比) |
| `area` | `--series` 多系列、`--stacked` / `--percent` 堆积(堆积折线图 = `area --stacked`) |
| `combo` | `--line` 折线值、`--bar-name` / `--line-name` 图例名 |
| `line-multi` | `--no-value-labels` 关闭数值标注 |
| `line` / `area` / `line-multi` | `--sample N` LTTB 保形降采样(数千行 CSV) |
| `line` | `--lower` / `--upper` 预测 / 置信区间带 |
| `gantt` | `--categories` / `--starts` / `--ends`(或 `--file` 两数值列 = 起止) |
| `dumbbell` | `--slope` 坡度图、`--series` 恰好 2 个系列 |
| `scatter` / `bubble` | `--x` / `--y`、`--trend` 趋势线、`--labels` 逐点标注、bubble 加 `--sizes` |
| `hist` | `--bins` 整数 / `auto` / 逗号分隔边界 |
| `waterfall` | `--no-total` 不追加合计柱 |
| `heatmap` | `--no-annotate` 不在格子标数值 |
| `sunburst` | `--data` 两级层级 JSON `{"父类目": {"子类目": 数值}}` |

**`--file` 列约定**(CSV 兼容 UTF-8 / GBK):首行表头,第 1 列类目、其余列数值——bar / line / area 多数值列自动升级多系列(系列名 = 表头),combo 取前两数值列(柱、线),box / violin 每列一组,sankey 取 3 列(源、目标、数值),scatter / bubble 按 x, y(, sizes)(, labels),heatmap 第 1 列行名,hist 第 1 列样本。

```bash
chartmove bar "季度产量" Q1=120 Q2=200 --style mckinsey                        # 内联数据
chartmove line "营收预测" 1月=120 2月=135 --lower 112,125 --upper 128,145      # 区间带
chartmove line "盈亏率" --file 基金.csv --cat-col 基金名称 --col "盈亏率(%)" --style cyberpunk   # 表格选列
chartmove sunburst "销售构成" --data '{"水果": {"苹果": 30}}'                   # 层级 JSON
chartmove themes --preview                                     # 主题预览拼版图
```

**批量出图**:`chartmove batch <类型> "文件或通配符"`,每份 CSV / Excel 各出一张同类型图表,`--style` / `--fmt` / `--animate` / `--col` / `--sheet` / `--stacked` 等参数与单图一致、作用于每一张;标题默认取文件名,`--title` 模板可用 `{name}`(文件名)与 `{i}`(序号)。逐张打印进度,单份失败不拖累其余,结束汇总 `批量完成:成功 X / 失败 Y`(有失败退出码 1,`--fail-fast` 遇错即停);`sunburst` 需层级 JSON,不适用批量。

```bash
chartmove batch bar "月报/*.csv" --col 销售额                     # 通配符批量(工具内部匹配,cmd/PowerShell 无需展开)
chartmove batch area "数据/*.xlsx" --sheet 2025 --stacked --animate --style academic   # Excel 批量出堆积 GIF(堆积折线 = area --stacked)
chartmove batch bar "月报/*.csv" --title "{i}_{name}" --fmt pdf  # 标题模板 + 逐张矢量 PDF
```

## MCP Server(AI / agent 接入)

stdio 传输,2 个工具;工具描述为英文,校验错误以中文 `ToolError` 返回。启动命令 `chartmove-mcp`(或 `python -m chartmove.mcp_server`),各 host 配置统一填 `command: chartmove-mcp`、`args: []`:

```json
{ "mcpServers": { "chartmove": { "command": "chartmove-mcp", "args": [] } } }
```

(TOML / YAML 系 host 按各自格式写同样两项;Windows 报中文编码错时在 `env` 加 `PYTHONUTF8=1`。)

| 工具 | 要点 |
|---|---|
| `make_chart` | `type`(24 种)+ `title`;数据参数按类型:`categories`/`values`、`series`、`links`(sankey)、`hierarchy`(sunburst)、`x`/`y`/`sizes`、`rows`/`cols`/`matrix`、`starts`/`ends`、`lower`/`upper`、`line_values`、`bins`;形态:`stacked`/`percent`/`horizontal`/`trend`/`labels`/`total`/`slope`;输出:`style`/`animate`/`loop`/`sample`/`numfmt`/`note`/`fmt`/`out`/`out_dir`;表格直读:`file`/`cat_col`/`col`/`sheet`(优先于内联数据,列约定同 CLI `--file`)。返回 `{path, file_size, ...}`,`path` 即交付物 |
| `list_themes` | 15 套主题(4 风格包)名称 + 中文描述;`preview=true` 附拼版图路径 |

## 图表能力

- 24 种类型,按用途:类目构成 `bar` / `pie` / `donut` / `rose` / `treemap` / `waterfall` / `pareto` / `funnel`;趋势 `line` / `line-multi` / `area` / `combo`;分布 `hist` / `box` / `violin`;相关 `scatter` / `bubble` / `heatmap`;关系 `radar` / `gantt` / `dumbbell` / `sankey` / `sunburst`(逐类型语义看 `--help` 与类型专属参数表)
- 15 套主题分 4 包(默认 business):学术 `academic` / `grayscale` / `ggplot` / `colorblind`;商务 `business` / `mckinsey` / `dashboard` / `sunset`;简约演示 `whitegrid` / `minimal` / `morandi` / `harvest`;其他 `sketch`(xkcd 手绘)/ `terminal` / `cyberpunk`
- 输出:PNG(16:9,1920×1080)/ PDF 矢量 / TIF 600dpi / GIF"数据生长"动画(播一遍停末帧,可 `--loop`)/ MP4(需 ffmpeg);`figsize` / `dpi` 参数化
- 体验:中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK)、数值默认中文单位(`numfmt='auto'`:≥1e4 万、≥1e8 亿)、最大 / 最小值自动高亮、y 轴智能从 0 起、类目 >25 刻度自动抽稀
- 校验:柱 / 饼类 `values` 需 ≥0(负值提示改用 waterfall;瀑布 / 直方 / 折线类不受限),nan / inf 拒绝,错误均为中文
- 产物持久:默认 `./Results/`,不清理不覆盖;输出目录优先级 `--out-dir` / `out_dir=` > 环境变量 `CHARTMOVE_OUT_DIR` > 默认

## 开发环境

```bash
py -3.13 -m venv .venv                              # Python >=3.10
.venv/Scripts/python.exe -m pip install -e ".[dev]" # 可编辑安装 + pytest/ruff
.venv/Scripts/python.exe -m pytest -n auto          # 全量约 30 秒
.venv/Scripts/python.exe -m ruff check src tests examples
.venv/Scripts/python.exe examples/make_all.py        # 一次生成全部 27 张示例
winget install Gyan.FFmpeg                           # 可选,仅 MP4 需要
```

依赖:matplotlib、mcp(官方 SDK)、pillow、openpyxl(Excel 读取)。CI:push / PR 自动跑 ruff + pytest,见 `.github/workflows/ci.yml`。

## LICENSE
Apache 2.0