# Chartmove(chartmove)

**数据图表生成工具** 
matplotlib 内核,20 种图表 × 13 主题(4 风格包),输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)

## 目录结构

```
├─ src/chartmove/     # 包:core 内核 + themes / fonts / output + cli / mcp_server
├─ tests/            # 20 图 × 3 输出 smoke test 矩阵 + CLI / 单元测试
└─ examples/         # make_all.py:一条命令生成全部 20 种示例图,兼任用法文档
```

## CLI

命令结构:**`chartmove <类型> "标题" [数据] [通用参数] [类型专属参数]`**,输出文件绝对路径,默认写入 `./Results/`。

20 种类型:`bar` / `line` / `line-multi` / `area` / `pie` / `donut` / `rose` / `treemap` / `combo` / `bar-multi` / `radar` / `scatter` / `bubble` / `hist` / `box` / `heatmap` / `waterfall` / `funnel` / `gantt` / `dumbbell`(多词类型用 kebab-case;`chartmove --help` 看总览,`chartmove bar --help` 看单类型全部参数)。

**数据的四种写法**(按类型任选其一,`--file` 优先级最高):

| 方式 | 适用类型 | 示例 |
|---|---|---|
| 内联 `类目=值` | 单系列类目型 | `chartmove bar "季度产量" Q1=120 Q2=200` |
| `--data` JSON(内联字符串或文件路径) | 单系列 | `--data '{"categories":["Q1"],"values":[120]}'` 或 `--data data.json` |
| `--series` JSON + `--categories` | 多系列:`line-multi` / `bar-multi` / `radar` / `box` | `--series '[["销售额",[1,2]],...]'`(也接受 `{名称: [值...]}`) |
| `--file` CSV / Excel | 全部类型 | `--file sales.csv --cat-col 基金名称 --col "盈亏率(%)"` |

**通用参数**:

| 参数 | 说明 |
|---|---|
| `--style` | 13 主题 × 4 风格包,默认 business;`chartmove themes` 列出全部 |
| `--animate` | 出"数据生长"动画(默认 GIF,`--fmt mp4` 可出 MP4) |
| `--loop` | 配合 `--animate`:GIF 无限循环(默认播一遍停在末帧;MP4 循环由播放器决定,不支持) |
| `--fmt` | `png`(静态默认)/ `pdf` 矢量 / `tif` 600dpi / `gif`(动画默认)/ `mp4` |
| `--out-dir` / `--out` | 输出目录(默认 `./Results/`)/ 输出文件名(默认 `类型_标题`) |
| `--dpi` / `--figsize` | 分辨率 / 画幅 `宽x高`(如 `12.8x7.2`) |
| `--numfmt` | 数值标签/刻度格式:`auto` 中文单位 万/亿(默认)/ `plain` 原样 / `percent` 追加 %(数值本身即百分数) |
| `--note` | 底部脚注(数据来源 / 备注,图左下角小字) |
| `--file` | CSV / Excel(.csv/.xlsx,首行为表头;CSV 兼容 UTF-8 与 GBK) |
| `--cat-col` / `--col` | 配合 `--file`:指定类目列 / 挑选数值列(表头名或从 1 数的序号) |
| `--sheet` | 配合 `--file`:Excel 工作表(名称或从 1 数的序号,默认第一个;CSV 不适用) |

**类型专属参数**:

| 类型 | 参数 |
|---|---|
| `bar` | `--horizontal` 横向条形(排名场景) |
| `combo` | `--line` 折线值(逗号分隔)、`--bar-name` / `--line-name` 图例名 |
| `line-multi` | `--no-value-labels` 关闭数值标注 |
| `line` / `area` / `line-multi` | `--sample N` 大数据 LTTB 保形降采样到 ~N 点(数千行 CSV 出图;多系列取各系列保留点并集) |
| `line` | `--lower` / `--upper` 预测/置信区间带(成对给出、与数据等长且 upper ≥ lower,逗号分隔) |
| `gantt` | `--categories` 任务名、`--starts` / `--ends` 起止(逗号分隔;或 `--file` 取 2 个数值列=开始/结束) |
| `dumbbell` | `--slope` 出坡度图、`--series` 恰好 2 个系列=期初/期末(或 `--file` 取 2 个数值列) |
| `scatter` / `bubble` | `--x` `--y` 数值列表(逗号分隔)、`--trend` 趋势线、`--labels` 逐点标注、bubble 加 `--sizes` 气泡大小 |
| `hist` | `--bins` 分箱:整数 / `auto` / 逗号分隔边界(如 `1,10,20`) |
| `waterfall` | `--no-total` 不追加合计柱 |
| `heatmap` | `--no-annotate` 不在格子标数值 |

**`--file` 列约定**(CSV / Excel,首行表头;CSV 兼容 UTF-8 与 GBK):默认第 1 列类目、其余列数值,多数值列时 bar/line 自动转多系列图(系列名 = 表头);combo 取类目列后两列(柱、线);box 每列一组(表头 = 组名);scatter/bubble 按 x, y(, sizes)(, labels) 取列;heatmap 类目列 = 行名、表头 = 列名;hist 第 1 列为原始样本;宽表用 `--cat-col` / `--col` 选列,Excel 多工作表用 `--sheet` 选(名称或从 1 数的序号)。

```bash
chartmove bar "季度产量" Q1=120 Q2=200 Q3=90 --style mckinsey                  # 内联数据
chartmove line "营收预测" 1月=120 2月=135 3月=128 --lower 112,125,116 --upper 128,145,140      # 折线区间带
chartmove line "盈亏率" --file 基金.csv --cat-col 基金名称 --col "盈亏率(%)" --style cyberpunk   # 表格选列
chartmove rose "品类销量" --file 销量.xlsx --sheet 2024          # 玫瑰图,读指定工作表
chartmove themes                                  # 查看 13 主题 × 4 风格包
chartmove themes --preview                        # 另出主题预览拼版图(PNG)
```

## MCP Server(AI / agent 接入)

stdio 传输,工具面收敛为 2 个;工具描述为英文(LLM 选工具靠它),数据校验错误以中文 `ToolError` 返回。

### 启动

```bash
chartmove-mcp                   # pip install 后可直接用(见 pyproject [project.scripts])
python -m chartmove.mcp_server  # 或不经控制台脚本
```

各 host 的配置文件格式不一(JSON / TOML / YAML),但写入的启动信息相同:`command` = `chartmove-mcp`、`args` = `[]`,按所用 host 对号入座:

JSON 系(Claude Desktop / ZCode / Cursor / Cline 等,`mcpServers` 字段):

```json
{
  "mcpServers": {
    "chartmove": { "command": "chartmove-mcp", "args": [] }
  }
}
```

TOML 系(Codex CLI,`~/.codex/config.toml`):

```toml
[mcp_servers.chartmove]
command = "chartmove-mcp"
args = []
```

YAML 系(DeepSeek Harness,每条 `insert` 注册一个 MCP client):

```yaml
- insert:
    - id: mcp-chartmove
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: chartmove
        transport: stdio
        command: chartmove-mcp
        args: []                   # 此时改为 ['-m', 'chartmove.mcp_server']
```

Windows host 报中文编码错时,可在 `env` 里加 `PYTHONUTF8 = "1"`(TOML)或 `PYTHONUTF8: '1'`(YAML)。


| 工具 | 参数 | 返回 |
|---|---|---|
| `make_chart` | `type`(20 种枚举)、`title`、`categories` / `values`(单系列)、`series`(多系列;gantt 用 `starts` / `ends`,dumbbell 恰好 2 个系列)、`x` / `y` / `sizes`(散点 / 气泡)、`rows` / `cols` / `matrix`(热力图)、`lower` / `upper`(折线区间带)、`line_values`(combo 折线值)、`horizontal`(bar 横向)、`trend`(散点趋势线)、`labels`(散点 / 气泡逐点标注)、`total`(waterfall 合计柱,默认 true)、`bins`(hist:整数 / 'auto' / 严格递增边界数组)、`slope`(dumbbell 坡度图)、`style`(默认 business)、`animate`(默认 false,出 GIF)、`loop`(默认 false,GIF 无限循环;仅 GIF 生效)、`sample`(默认 null,仅折线类,LTTB 降采样目标点数)、`numfmt`(auto / plain / percent,默认 auto 万/亿)、`note`(底部脚注)、`fmt`(png/pdf/tif/gif/mp4)、`out` / `out_dir`、`file` / `cat_col` / `col` / `sheet`(CSV / Excel 直读,见下) | JSON:`{path(绝对路径,即交付物), file_size, type, style, animated}` |
| `list_themes` | `preview`(可选,生成主题预览拼版图)、`out_dir`(可选,指定拼版图输出目录) | 13 主题 × 4 风格包:名称 + 中文标签 + 一句话描述;`preview=true` 时附拼版图路径 |

**`file` 数据**:agent 手头有 CSV / Excel 时传 `file` 路径即可,优先于内联数据,不必把整表内联进参数;`cat_col` / `col` 选类目列 / 挑 1 个数值列(表头名或从 1 数的序号),`sheet` 选 Excel 工作表。列约定与 CLI `--file` 相同(见上文):bar / line 多数值列自动升级多系列(返回 `type` 如实报告),combo 取两列(柱、线),box 每列一组,scatter/bubble 按 x, y(, sizes)(, labels) 取列,hist 第 1 列为样本,heatmap 第 1 列为行名。

## 开发环境

```bash
py -3.13 -m venv .venv                              # Python >=3.10
.venv/Scripts/python.exe -m pip install -e ".[dev]" # 可编辑安装 + pytest/ruff
.venv/Scripts/python.exe -m pytest -n auto         # smoke test(pytest-xdist 并行,全量约 30 秒)
.venv/Scripts/python.exe -m ruff check src tests examples
.venv/Scripts/python.exe examples/make_all.py        # 一次生成全部 20 张,默认写入 ./Results/
winget install Gyan.FFmpeg                          # 可选,仅 MP4 动画需要
```

CI:push / PR 自动跑 ruff lint + pytest smoke test,见 `.github/workflows/ci.yml`。

## 图表能力

- 20 种类型:`bar`(支持 `horizontal=True` 横向条形)/ `line`(可加 `lower` / `upper` 预测区间带)/ `line_multi` / `area` / `pie` / `donut` / `rose`(Nightingale 极坐标柱状,半径即数值)/ `treemap`(矩形树图,面积即占比)/ `combo` / `bar_multi` / `radar` / `scatter`(可选趋势线)/ `bubble` / `hist` / `box` / `heatmap` / `waterfall` / `funnel`(自动逐级转化率)/ `gantt`(甘特图,数值轴起止)/ `dumbbell`(哑铃图,两期对比,`slope=True` 出坡度图)
- 13 套主题 × 4 风格包(默认 `business` 商务极简):
  - **学术包**:`academic` 学术Ticks标准风 / `grayscale` 灰度单色学术 / `ggplot` 复古统计 / `colorblind` 色盲无障碍(Okabe-Ito)
  - **商务包**:`business` 商务极简 / `mckinsey` 麦肯锡 / `dashboard` 深色看板
  - **简约演示包**:`whitegrid` 白底网格 / `minimal` 纯极简无脊线 / `morandi` 莫兰迪低饱和
  - **其他风格包**:`sketch` 手绘草图(xkcd 式) / `terminal` 暗黑程序员 / `cyberpunk` 赛博朋克霓虹
  - 主题元数据 `THEME_PACKS` / `THEME_LABELS` / `THEME_DESCS` 供 CLI `themes` 子命令与 MCP `list_themes` 使用
- 输出:PNG / PDF(矢量)/ TIF(600dpi,期刊投稿)/ GIF("数据生长"动画,默认播一遍停末帧适配 PPT 放映与聊天窗,`--loop` / `loop=true` 可无限循环)/ MP4(需 ffmpeg,循环由播放器决定);`figsize` / `dpi` 参数化,默认 16:9 / 150dpi(1920×1080)
- 差异化:最大/最小值自动高亮、y 轴智能从 0 起、中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK,见 fonts.py);数值标签/刻度默认中文单位(`numfmt='auto'`:≥1e4 万、≥1e8 亿,percent 追加 %,plain 原样);`note` 参数出底部脚注(数据来源 / 备注)
- 柱类 / 饼类图 values 需 >=0,负值直接报中文错误(bar 会提示改用 waterfall;瀑布图 / 直方图 / 折线类不受限);nan / inf 同样报错
- 大数据:类目 >25 刻度自动抽稀、折线标记超 50 个隔点绘制;`line` / `area` / `line-multi` 支持 `--sample` / `sample=` LTTB 保形降采样(数千行 CSV 出图)
- 输出目录:默认项目内 `./Results/`(持久,不做 TTL 清理;同名文件自动加序号 `_2`/`_3`,不覆盖已有产物);优先级 `out_dir=` / `--out-dir` 参数 > 环境变量 `CHARTMOVE_OUT_DIR` > 默认
- 表格直读:CLI `--file` 支持 CSV(UTF-8 / GBK)与 Excel(.xlsx / .xlsm),`--sheet` / `sheet=` 选 Excel 工作表(名称或从 1 数的序号),见 table.py

依赖:matplotlib、mcp(官方 SDK,2.x 起 API 为 `MCPServer`)、pillow、openpyxl(Excel 读取).

## LICENSE
Apache 2.0