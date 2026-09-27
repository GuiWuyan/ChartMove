# ChartGen(chartgen)

**中文数据图表生成器 —— 人可用、AI 可调。** matplotlib 内核,9 种图表 × 8 主题,输出 PNG / PDF / TIF / GIF / MP4;入口为 CLI 与 MCP Server(AI / agent 调用)两个,未来作为桌宠 agent 的出图插件。原 PPT / PDF / Word 文档生成能力已移除;GUI 入口已取消(2026-09-27),PPT 由独立的 PPT Master 项目承担。

## 目录结构

```
├─ src/chartgen/     # 包:core 内核 + themes / fonts / output + cli / mcp_server(待 M2/M3)
├─ tests/            # 9 图 × 3 输出 smoke test 矩阵 + 单元测试
├─ examples/         # make_all.py:一条命令生成全部 9 种示例图,兼任用法文档
└─ docs/plan.md      # 开发方案
```

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

- 9 种类型:`bar`(支持 `horizontal=True` 横向条形)/ `line` / `line_multi` / `area` / `pie` / `donut` / `combo` / `bar_multi` / `radar`
- 8 套主题:excel(默认)/ soft / dark / minimal / tech / vivid / business / science
- 输出:PNG / PDF(矢量)/ TIF(600dpi,期刊投稿)/ GIF("数据生长"动画,播一遍停末帧,适配 PPT 放映与聊天窗)/ MP4(需 ffmpeg);`figsize` / `dpi` 参数化,默认 16:9 / 150dpi(1920×1080)
- 差异化:最大/最小值自动高亮、y 轴智能从 0 起、中文字体零配置(Windows 雅黑 / macOS 苹方 / Linux Noto CJK,见 fonts.py)
- 输出目录:默认 `~/ChartGen/`(持久,不做 TTL 清理);优先级 `out_dir=` 参数 > 环境变量 `CHARTGEN_OUT_DIR` > 默认

依赖:matplotlib、mcp(官方 SDK,2.x 起 API 为 `MCPServer`)、pillow、pywin32(Windows)。
