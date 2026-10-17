# ChartMove

**中文数据图表生成器**:matplotlib 内核,30 种图表,15 套主题分属 4 个风格包,输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)。

## 目录结构

```
├─ src/chartmove/     # 图表内核 + themes / fonts / output + cli / mcp_server
├─ tests/            # 24 图 smoke test 矩阵 + CLI / 单元测试
└─ examples/         # make_all.py:一条命令生成全部类型示例图
```

## CLI

命令结构:**`chartmove <类型> "标题" [数据] [参数]`**,产物默认写入 `./Results/`(同名自动加序号,不覆盖)。

30 种类型,按用途分组(多词类型用 kebab-case):

| 用途     | 类型                                                                                                                                                                  |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 类目构成 | `bar` 柱状图 / `pie` 饼图 / `donut` 环形图 / `rose` 玫瑰图 / `treemap` 矩形树图 / `waterfall` 瀑布图 / `pareto` 帕累托图 / `funnel` 漏斗图 / `bar-multi` 多系列柱状图 |
| 趋势     | `line` 折线图 / `line-multi` 多系列折线 / `area` 面积图 / `combo` 双轴组合图                                                                                          |
| 分布     | `hist` 直方图 / `box` 箱线图 / `violin` 小提琴图                                                                                                                      |
| 相关     | `scatter` 散点图 / `bubble` 气泡图 / `heatmap` 热力图                                                                                                                 |
| 关系     | `radar` 雷达图 / `gantt` 甘特图 / `dumbbell` 哑铃图 / `sankey` 桑基图 / `sunburst` 旭日图                                                                             |
| 科学绘图 | `funcplot` 函数图像 / `polar` 极坐标曲线 / `param` 参数曲线·相轨线 / `vector` 矢量场·流线·方向场 / `contour` 等高线 / `surface` 三维曲面(`--animate` 相机环绕)        |

`chartmove --help` 看总览,`chartmove bar --help` 看单类型全部参数。

**数据的四种写法**(按类型任选其一,`--file` 优先级最高):

| 方式                 | 适用类型                                                                                                                              | 示例                                                                  |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| 内联 `类目=值`       | 单系列类目型                                                                                                                          | `chartmove bar "季度产量" Q1=120 Q2=200`                              |
| `--data` JSON        | 单系列(仅单图命令)                                                                                                                    | `--data '{"categories":["Q1"],"values":[120]}'` 或 `--data data.json` |
| `--series` JSON      | 多系列:`line-multi` / `bar-multi` / `radar` / `area` / `dumbbell`(配 `--categories`);`box` / `violin` 只要 `--series`(每系列一组样本) | `--series '[["销售额",[1,2]],...]'`(也接受 `{名称: [值...]}`)         |
| `--file` CSV / Excel | 全部类型除 `sunburst`                                                                                                                 | `--file sales.csv --cat-col 基金名称 --col "盈亏率(%)"`               |
| 表达式(math 域)      | `funcplot` / `polar` / `param` / `vector` / `contour` / `surface`                                                                     | `chartmove funcplot "正弦" "sin(x)" --xmin -6.28 --xmax 6.28`         |

**表达式语法**(math 域专用,与 `--file` / `--x/--y` 等数据参数互斥):变量 `x`、`y`(二维场)/ `t`(param)/ `theta`(polar,弧度);常量 `pi`、`e`、`tau`;函数为 numpy 数学函数白名单(`sin cos tan exp log sqrt abs where clip minimum maximum heaviside ...`,完整清单见报错提示)。范围用 `--xmin/--xmax`(二维场加 `--ymin/--ymax`);`--samples` 是采样点数(曲线默认 400)或二维场每轴点数(vector 默认 20 / contour、surface 默认 60)。安全闸:仅算术运算 + 白名单函数,禁属性访问/导入/连续幂/指数>100,违规报中文错。以 `-` 开头的表达式(如旋转场 `-y`)先把选项写完再用 `--` 分隔:`chartmove vector "旋转场" --xmin -2 --xmax 2 --ymin -2 --ymax 2 -- -y x`。

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

| 类型                                 | 参数                                                                                                                                                                                                                                                                      |
|--------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `bar`                                | `--horizontal` 横向条形、`--err` 误差线(SD/SEM,逗号分隔;横向自动切 x 向)                                                                                                                                                                                                  |
| `pie` / `donut` / `rose` / `treemap` | `--percent` 标签追加占合计 %(原始数据自动归一,如 `120 (31%)`)                                                                                                                                                                                                             |
| `bar-multi`                          | `--stacked` 堆积、`--percent` 百分比堆积(<4% 小段不标占比)、`--errs` 各系列误差 JSON(仅分组)                                                                                                                                                                              |
| `area`                               | `--series` 多系列、`--stacked` / `--percent` 堆积(堆积折线图 = `area --stacked`)                                                                                                                                                                                          |
| `combo`                              | `--line` 折线值、`--bar-name` / `--line-name` 图例名、`--bar-err` / `--line-err` 误差线                                                                                                                                                                                   |
| `line-multi`                         | `--no-value-labels` 关闭数值标注、`--errs` 各系列误差 JSON(null 占位 = 无误差)                                                                                                                                                                                            |
| `line` / `area` / `line-multi`       | `--sample N` LTTB 保形降采样(数千行 CSV)                                                                                                                                                                                                                                  |
| `line`                               | `--lower` / `--upper` 预测 / 置信区间带、`--err` 对称误差(与 lower/upper 互斥)、`--err-style band`(半透明带,默认)/ `whisker`(须状误差线)                                                                                                                                  |
| `gantt`                              | `--categories` / `--starts` / `--ends`(或 `--file` 两数值列 = 起止)                                                                                                                                                                                                       |
| `dumbbell`                           | `--slope` 坡度图、`--series` 恰好 2 个系列                                                                                                                                                                                                                                |
| `scatter`                            | `--trend` 趋势线、`--trend-eq` 标注方程与 R²、`--xerr` / `--yerr` 双向误差、`--groups` 重复测量 JSON `[[x,[读数...]],...]`(逐组聚合均值±SD)、`--show-raw` 叠加原始读数空心点、`--no-highlight` 关最好/最差高亮(groups 默认已关)、`--labels` 逐点标注(bubble 加 `--sizes`) |
| `violin`                             | `--mean-sd` 组内叠加均值±SD(菱形 + 须)                                                                                                                                                                                                                                    |
| `hist`                               | `--bins` 整数 / `auto` / 逗号分隔边界                                                                                                                                                                                                                                     |
| `waterfall`                          | `--no-total` 不追加合计柱                                                                                                                                                                                                                                                 |
| `heatmap`                            | `--no-annotate` 不在格子标数值                                                                                                                                                                                                                                            |
| `sunburst`                           | `--data` 两级层级 JSON `{"父类目": {"子类目": 数值}}`、`--percent` 外环标签追加占合计 %                                                                                                                                                                                   |
| `funcplot`                           | `--x` / `--y`、`--sample` LTTB 降采样、`--pi-ticks` π 分数刻度、`--equal` 等比例、`--points` 实测点 JSON `[[x,y,(err)],...]`(带误差线叠加)、`--points-fit` 实测点线性拟合 + 方程与 R²、`--points-name` 图例名                                                             |
| `polar`                              | `--x`(theta,弧度)/ `--y`(r)、`--fill` 填充到圆心、`--no-theta-pi` 关 π 刻度                                                                                                                                                                                               |
| `param`                              | `--x` / `--y`、`--arrows` 方向箭头、`--no-equal` 关等比例、`--pi-ticks`                                                                                                                                                                                                   |
| `vector`                             | `--x` / `--y` / `--u` / `--v`、`--mode` quiver(默认)/ stream / dir、`--density` 流线密度                                                                                                                                                                                  |
| `contour`                            | `--x` / `--y` / `--z`、`--long` 长表布局、`--levels` 级数或分级、`--no-fill`、`--no-colorbar`、`--pi-ticks`                                                                                                                                                               |
| `surface`                            | `--x` / `--y` / `--z`、`--long` 长表布局、`--no-colorbar`、`--elev` / `--azim` 视角                                                                                                                                                                                       |

注:`--percent` 一词两义——饼家族(`pie` / `donut` / `rose` / `treemap` / `sunburst`)是标签追加占比,`bar-multi` / `area` 是百分比堆积;若数据本身已是百分数,用通用的 `--numfmt percent` 只做格式化即可。

**`--file` 列约定**(CSV 兼容 UTF-8 / GBK):首行表头,第 1 列类目、其余列数值——bar / line / area 多数值列自动升级多系列(系列名 = 表头),combo 取前两数值列(柱、线),box / violin 每列一组,sankey 取 3 列(源、目标、数值),scatter / bubble 按 x, y(, sizes)(, labels),heatmap 第 1 列行名,hist 第 1 列样本。math 域全为数值列、按行对齐(缺格整行剔除):funcplot 第 1 列 x、其余列 = 各曲线 y(多列自动多曲线),polar 2 列(theta, r),param 2 列(x, y)或 3 列(t, x, y 取后两列),vector 4 列(x, y, u, v),contour / surface 默认矩阵布局(首列 = y 坐标、首行 = x 坐标,需数值)或 `--long` 切 3 列长表(x, y, z)。

```bash
chartmove bar "季度产量" Q1=120 Q2=200 --style mckinsey                        # 内联数据
chartmove pie "品类占比" 线上=55 门店=30 批发=15 --percent                      # 标签自动算占比
chartmove line "营收预测" 1月=120 2月=135 --lower 112,125 --upper 128,145      # 区间带
chartmove line "月度销量" 1月=120 2月=135 --err 12,18 --err-style whisker      # 须状误差线(SD)
chartmove scatter "标准曲线" --groups '[[0,[0.02,0.03]],[4,[0.25,0.28]],[8,[0.45,0.5]]]' \
    --trend --trend-eq --show-raw                       # 重复测量聚合均值±SD + 回归方程/R² + 原始读数
chartmove line "盈亏率" --file 基金.csv --cat-col 基金名称 --col "盈亏率(%)" --style cyberpunk   # 表格选列
chartmove sunburst "销售构成" --data '{"水果": {"苹果": 30}}'                   # 层级 JSON
chartmove funcplot "阻尼振荡" --file data.csv --pi-ticks                        # 科学绘图:文件 x,y(多列 = 多曲线)
chartmove funcplot "标准曲线" "0.0418*x+0.087" --xmin 0 --xmax 20 \
    --points '[[0,0.02,0.01],[4,0.23,0.03],[8,0.42,0.02],[16,0.75,0.03]]' --points-fit   # 理论曲线 + 实测点误差线 + 拟合标注
chartmove vector "流场" --file field.csv --mode stream                          # 矢量场出流线(x,y,u,v 四列)
chartmove surface "波面" "sin(x)*cos(y)" --xmin -3 --xmax 3 --ymin -3 --ymax 3 --animate   # 表达式 3D 曲面 + 相机环绕
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

| 工具          | 要点                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make_chart`  | `type`(30 种)+ `title`;数据参数按类型:`categories`/`values`、`series`、`links`(sankey)、`hierarchy`(sunburst)、`x`/`y`/`sizes`、`rows`/`cols`/`matrix`、`starts`/`ends`、`lower`/`upper`、`line_values`、`bins`、math 域:`u`/`v`/`z`/`curves`/`mode`/`density`/`pi_ticks`/`fill`/`arrows`/`elev`/`azim`/`long`;形态:`stacked`/`percent`/`horizontal`/`trend`/`trend_eq`/`labels`/`total`/`slope`;误差线:`err`/`err_style`(line)、`errs`(line-multi/bar-multi)、`bar_err`/`line_err`(combo)、`xerr`/`yerr`/`groups`/`show_raw`/`highlight`(scatter)、`mean_sd`(violin)、`points`/`points_name`/`points_fit`(funcplot);输出:`style`/`animate`/`loop`/`sample`/`numfmt`/`note`/`fmt`/`out`/`out_dir`;表格直读:`file`/`cat_col`/`col`/`sheet`(优先于内联数据,列约定同 CLI `--file`)。返回 `{path, file_size, ...}`,`path` 即交付物 |
| `list_themes` | 15 套主题(4 风格包)名称 + 中文描述;`preview=true` 附拼版图路径                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

## 图表能力

- 30 种类型按用途分 6 组(类目构成 / 趋势 / 分布 / 相关 / 关系 / 科学绘图,见 CLI 节的类型总表;逐类型语义看 `--help` 与类型专属参数表)
- 15 套主题分 4 包(默认 business):学术 `academic` / `grayscale` / `ggplot` / `colorblind`;商务 `business` / `mckinsey` / `dashboard` / `sunset`;简约演示 `whitegrid` / `minimal` / `morandi` / `harvest`;其他 `sketch`(xkcd 手绘)/ `terminal` / `cyberpunk`
- 输出:PNG(16:9,1920×1080)/ PDF 矢量 / TIF 600dpi / GIF"数据生长"动画(播一遍停末帧,可 `--loop`)/ MP4(需 ffmpeg);`figsize` / `dpi` 参数化
- 体验:中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK)、数值默认中文单位(`numfmt='auto'`:≥1e4 万、≥1e8 亿)、最大 / 最小值自动高亮、y 轴智能从 0 起、类目 >25 刻度自动抽稀
- 占比一键出:原始数据自动归一——`pie` / `donut` / `rose` / `treemap` / `sunburst` 加 `--percent` 标签追加占比,`bar-multi` / `area` 加 `--percent` 出百分比堆积,`pareto` 自动算累计占比线(数据本身是百分数时用 `--numfmt percent` 只做格式)
- 误差线:`line`(`--err` 须/带双样式)/ `bar` / `line-multi` / `bar-multi`(分组)/ `combo` / `scatter`(双向)支持对称误差(SD/SEM);`scatter --groups` 从重复测量聚合均值±SD 并可 `--show-raw` 叠原始读数、`--trend-eq` 标注回归方程与 R²、`--no-highlight` 关最好/最差高亮(groups 默认关);`violin --mean-sd` 叠加均值±SD;`funcplot --points` 实测点带误差叠加理论曲线;堆积柱状图不支持误差线(堆积段无从锚定,市面共识)
- 校验:柱 / 饼类 `values` 需 ≥0(负值提示改用 waterfall;瀑布 / 直方 / 折线类不受限),nan / inf 拒绝,错误均为中文
- 产物持久:默认 `./Results/`,不清理不覆盖;输出目录优先级 `--out-dir` / `out_dir=` > 环境变量 `CHARTMOVE_OUT_DIR` > 默认

## 开发环境

```bash
py -3.13 -m venv .venv                              # Python >=3.12
.venv/Scripts/python.exe -m pip install -e ".[dev]" # 可编辑安装 + pytest/ruff
.venv/Scripts/python.exe -m pytest -n auto          # 全量约 30 秒
.venv/Scripts/python.exe -m pytest -m "not slow" -n auto  # 冒烟(跳过重渲染/MCP 会话)约 10 秒
.venv/Scripts/python.exe -m ruff check src tests examples
.venv/Scripts/python.exe examples/make_all.py        # 一次生成全部 42 张示例(30 类型 + 堆积/误差线变体)
winget install Gyan.FFmpeg                           # 可选,仅 MP4 需要
```

依赖:matplotlib、mcp(官方 SDK)、pillow、openpyxl(Excel 读取)。CI:push / PR 自动跑 ruff + pytest,见 `.github/workflows/ci.yml`。

## LICENSE
Apache 2.0