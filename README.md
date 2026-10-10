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

24 种类型,按用途分组(多词类型用 kebab-case):

| 用途     | 类型                                                                                                                                                                  |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 类目构成 | `bar` 柱状图 / `pie` 饼图 / `donut` 环形图 / `rose` 玫瑰图 / `treemap` 矩形树图 / `waterfall` 瀑布图 / `pareto` 帕累托图 / `funnel` 漏斗图 / `bar-multi` 多系列柱状图 |
| 趋势     | `line` 折线图 / `line-multi` 多系列折线 / `area` 面积图 / `combo` 双轴组合图                                                                                          |
| 分布     | `hist` 直方图 / `box` 箱线图 / `violin` 小提琴图                                                                                                                      |
| 相关     | `scatter` 散点图 / `bubble` 气泡图 / `heatmap` 热力图                                                                                                                 |
| 关系     | `radar` 雷达图 / `gantt` 甘特图 / `dumbbell` 哑铃图 / `sankey` 桑基图 / `sunburst` 旭日图                                                                             |

`chartmove --help` 看总览,`chartmove bar --help` 看单类型全部参数。

**数据的四种写法**(按类型任选其一,`--file` 优先级最高):

| 方式                 | 适用类型                                                                                                                              | 示例                                                                  |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| 内联 `类目=值`       | 单系列类目型                                                                                                                          | `chartmove bar "季度产量" Q1=120 Q2=200`                              |
| `--data` JSON        | 单系列(仅单图命令)                                                                                                                    | `--data '{"categories":["Q1"],"values":[120]}'` 或 `--data data.json` |
| `--series` JSON      | 多系列:`line-multi` / `bar-multi` / `radar` / `area` / `dumbbell`(配 `--categories`);`box` / `violin` 只要 `--series`(每系列一组样本) | `--series '[["销售额",[1,2]],...]'`(也接受 `{名称: [值...]}`)         |
| `--file` CSV / Excel | 全部类型除 `sunburst`                                                                                                                 | `--file sales.csv --cat-col 基金名称 --col "盈亏率(%)"`               |

**通用参数**(单图与 batch 都有;标"仅单图"的除外):

| 参数                  | 说明                                                                                                                                               |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `--style`             | 15 套主题,默认 business;`chartmove themes` 列出全部                                                                                                |
| `--animate`           | 出"数据生长"动画(默认 GIF)                                                                                                                         |
| `--loop`              | 让 GIF 无限循环，仅对 GIF 有效，必须与 --animate 同用                                                                                              |
| `--fmt`               | `png`(静态默认)/ `pdf` 矢量 / `tif` 600dpi / `gif`(动画默认)/ `mp4`(需 ffmpeg)                                                                     |
| `--out-dir`           | 输出目录(默认 `CHARTMOVE_OUT_DIR` 或 `./Results/`)                                                                                                 |
| `--dpi` / `--figsize` | 分辨率(可填写任意正值) / 画幅 `宽x高`                                                                                                              |
| `--numfmt`            | 数值格式:`auto` 万/亿(默认)/ `plain`(原样数据) / `percent`(仅追加 %,不做比例换算，切勿与专属参数 --percent 一起混用)                               |
| `--note`              | 底部脚注(数据来源 / 备注)                                                                                                                          |
| 仅单图                | `--out` 输出文件名(默认 `类型_标题`;batch 走 `--title` 模板)、`--data` JSON 入参、`--file` CSV / Excel 直读                                        |
| `--file` 配套         | `--cat-col` 类目列 / `--col` 数值列 / `--sheet` Excel 工作表;`--cat-col` / `--col` 仅对"第 1 列类目 + 数值列"布局的类型生效,其余类型的列约定见下节 |

**类型专属参数**:

| 类型                                 | 参数                                                                                    |
|--------------------------------------|-----------------------------------------------------------------------------------------|
| `bar`                                | `--horizontal` 横向条形                                                                 |
| `pie` / `donut` / `rose` / `treemap` | `--percent` 标签追加占合计 %(原始数据自动归一,如 `120 (31%)`)                           |
| `bar-multi`                          | `--stacked` 堆积、`--percent` 百分比堆积(<4% 小段不标占比)                              |
| `area`                               | `--series` 多系列、`--stacked` / `--percent` 堆积(堆积折线图 = `area --stacked`)        |
| `combo`                              | `--line` 折线值、`--bar-name` / `--line-name` 图例名                                    |
| `line-multi`                         | `--no-value-labels` 关闭数值标注                                                        |
| `line` / `area` / `line-multi`       | `--sample N` LTTB 保形降采样(数千行 CSV)                                                |
| `line`                               | `--lower` / `--upper` 预测 / 置信区间带                                                 |
| `gantt`                              | `--categories` / `--starts` / `--ends`(或 `--file` 两数值列 = 起止)                     |
| `dumbbell`                           | `--slope` 坡度图、`--series` 恰好 2 个系列                                              |
| `scatter` / `bubble`                 | `--x` / `--y`、`--trend` 趋势线、`--labels` 逐点标注、bubble 加 `--sizes`               |
| `hist`                               | `--bins` 整数 / `auto` / 逗号分隔边界                                                   |
| `waterfall`                          | `--no-total` 不追加合计柱                                                               |
| `heatmap`                            | `--no-annotate` 不在格子标数值                                                          |
| `sunburst`                           | `--data` 两级层级 JSON `{"父类目": {"子类目": 数值}}`、`--percent` 外环标签追加占合计 % |

注:`--percent` 一词两义——饼家族(`pie` / `donut` / `rose` / `treemap` / `sunburst`)是标签追加占比,`bar-multi` / `area` 是百分比堆积;若数据本身已是百分数,用通用的 `--numfmt percent` 只做格式化即可。

**`--file` 列约定**(CSV 兼容 UTF-8 / GBK):首行表头,第 1 列类目、其余列数值——bar / line / area 多数值列自动升级多系列(系列名 = 表头),combo 取前两数值列(柱、线),box / violin 每列一组,sankey 取 3 列(源、目标、数值),scatter / bubble 按 x, y(, sizes)(, labels),heatmap 第 1 列行名,hist 第 1 列样本。

```bash
chartmove bar "季度产量" Q1=120 Q2=200 --style mckinsey                        # 内联数据
chartmove pie "品类占比" 线上=55 门店=30 批发=15 --percent                      # 标签自动算占比
chartmove line "营收预测" 1月=120 2月=135 --lower 112,125 --upper 128,145      # 区间带
chartmove line "盈亏率" --file 基金.csv --cat-col 基金名称 --col "盈亏率(%)" --style cyberpunk   # 表格选列
chartmove sunburst "销售构成" --data '{"水果": {"苹果": 30}}'                   # 层级 JSON
chartmove themes --preview                                     # 主题预览拼版图
```

**批量出图**:`chartmove batch <类型> "文件或通配符"`,每份 CSV / Excel 各出一张同类型图表,`--style` / `--fmt` / `--animate` / `--cat-col` / `--col` / `--sheet` / `--stacked` / `--percent` 等参数与单图一致、作用于每一张(`--data` / `--file` / `--out` 仅单图有,batch 的数据源是位置文件、产物名走 `--title` 模板);标题默认取文件名,`--title` 模板可用 `{name}`(文件名)与 `{i}`(序号)。逐张打印进度,单份失败不拖累其余,结束汇总 `批量完成:成功 X / 失败 Y`(有失败退出码 1,`--fail-fast` 遇错即停);`sunburst` 需层级 JSON,不适用批量。

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

| 工具          | 要点                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make_chart`  | `type`(24 种)+ `title`;数据参数按类型:`categories`/`values`、`series`、`links`(sankey)、`hierarchy`(sunburst)、`x`/`y`/`sizes`、`rows`/`cols`/`matrix`、`starts`/`ends`、`lower`/`upper`、`line_values`、`bins`;形态:`stacked`/`percent`/`horizontal`/`trend`/`labels`/`total`/`slope`;输出:`style`/`animate`/`loop`/`sample`/`numfmt`/`note`/`fmt`/`out`/`out_dir`;表格直读:`file`/`cat_col`/`col`/`sheet`(优先于内联数据,列约定同 CLI `--file`)。返回 `{path, file_size, ...}`,`path` 即交付物 |
| `list_themes` | 15 套主题(4 风格包)名称 + 中文描述;`preview=true` 附拼版图路径                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## 图表能力

- 24 种类型按用途分 5 组(类目构成 / 趋势 / 分布 / 相关 / 关系,见 CLI 节的类型总表;逐类型语义看 `--help` 与类型专属参数表)
- 15 套主题分 4 包(默认 business):学术 `academic` / `grayscale` / `ggplot` / `colorblind`;商务 `business` / `mckinsey` / `dashboard` / `sunset`;简约演示 `whitegrid` / `minimal` / `morandi` / `harvest`;其他 `sketch`(xkcd 手绘)/ `terminal` / `cyberpunk`
- 输出:PNG(16:9,1920×1080)/ PDF 矢量 / TIF 600dpi / GIF"数据生长"动画(播一遍停末帧,可 `--loop`)/ MP4(需 ffmpeg);`figsize` / `dpi` 参数化
- 体验:中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK)、数值默认中文单位(`numfmt='auto'`:≥1e4 万、≥1e8 亿)、最大 / 最小值自动高亮、y 轴智能从 0 起、类目 >25 刻度自动抽稀
- 占比一键出:原始数据自动归一——`pie` / `donut` / `rose` / `treemap` / `sunburst` 加 `--percent` 标签追加占比,`bar-multi` / `area` 加 `--percent` 出百分比堆积,`pareto` 自动算累计占比线(数据本身是百分数时用 `--numfmt percent` 只做格式)
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