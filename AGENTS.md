# AGENTS.md — AI 工作规则

本项目定位:**数据图表生成工具**(`chartgen`),内核在 `src/chartgen/` 包(M1 自旧版单文件 `TOOLS/chart.py` 迁移而来,该文件已删除)。

## 技术要点

- 图表:`from chartgen import bar, line, line_multi, pie, donut, area, combo, bar_multi, radar`;matplotlib 封装,9 类型 × 8 主题(excel/soft/dark/minimal/tech/vivid/business/science)
- 输出:PNG / PDF(矢量)/ TIF(600dpi,期刊投稿)/ GIF(动画,播一遍停末帧)/ MP4(动画,需 ffmpeg,`winget install Gyan.FFmpeg`);figsize / dpi 可调,默认 16:9 / 150dpi
- 动画为"数据生长"式,插 PPT 或聊天窗放映友好;不播放动画的场景(如 Word 类文档)一律给 PNG
- 命令行:`chartgen` 命令为占位,完整 CLI 在 M2 交付(单系列"类目=值"内联、多系列 `--series` JSON、`themes` 子命令)
- MCP:官方 SDK `mcp` 2.x,服务端类 `MCPServer`(`from mcp.server.mcpserver import MCPServer`,旧教程的 `FastMCP` 写法已废弃);server 设计见方案 5.3 节

## 产出与目录

- 包 `chartgen` 产物默认写入 `~/ChartGen/`(持久,不做 TTL 清理);优先级 `out_dir=` 参数 > 环境变量 `CHARTGEN_OUT_DIR` > 默认目录
- `docs/` 存开发方案等长期文档(`docs/plan.md`),不做清理
- 临时测试文件用完即删

## 硬性规范

- Python 一律用 `.venv/Scripts/python.exe`;Node 侧无依赖(package.json 已移除,勿再创建)
- 新增 Python 库:装进 .venv 并同步写入 requirements.txt(版本约束用 `>=`,禁用 `>`)
- 如果无法依赖现在的环境制作出成品,则反馈给用户原因并道歉

## 交付前必须验证(不过关不许交付)

1. 每种用到的图表类型跑 smoke test:出图不抛异常、文件存在、主题与中文字体渲染正确
2. 验证用的临时文件全部清理
