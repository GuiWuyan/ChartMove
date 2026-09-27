# AGENTS.md — AI 工作规则

本项目定位:**数据图表生成工具**(`chartgen` 的前身与开发跳板),核心资产是 `TOOLS/chart.py`。
PPT / PDF / Word 文档生成能力已于 2026-09-27 移除——PPT 由独立的 PPT Master 项目承担。
开发蓝图见 `制图工具开发方案_20260927.md`,涉及方向取舍时以方案为准。

## 技术要点

- 图表:`from TOOLS.chart import bar, line, line_multi, pie, donut, area, combo, bar_multi, radar`;matplotlib 封装,9 类型 × 8 主题(excel/soft/dark/minimal/tech/vivid/business/science)
- 输出:PNG(1920×1080)/ GIF(动画,播一遍停末帧)/ MP4(动画,需 ffmpeg,`winget install Gyan.FFmpeg`)
- 动画为"数据生长"式,插 PPT 或聊天窗放映友好;不播放动画的场景(如 Word 类文档)一律给 PNG
- 命令行:`python TOOLS/chart.py bar "标题" Q1=120 --style tech --animate`
- MCP:官方 SDK `mcp` 2.x,服务端类 `MCPServer`(`from mcp.server.mcpserver import MCPServer`,旧教程的 `FastMCP` 写法已废弃);server 设计见方案 5.3 节

## 产出与目录

- 图表产物写入 `Cache/charts/`(现状);迁移新仓库后改持久输出目录(见方案第 4 节),届时不再依赖 Cache TTL
- `FILE/` 存开发方案等长期文档,不做清理
- 临时测试文件用完即删

## 硬性规范

- Python 一律用 `.venv/Scripts/python.exe`;Node 侧无依赖(package.json 已移除,勿再创建)
- 新增 Python 库:装进 .venv 并同步写入 requirements.txt(版本约束用 `>=`,禁用 `>`)
- 如果无法依赖现在的环境制作出成品,则反馈给用户原因并道歉

## 交付前必须验证(不过关不许交付)

1. 每种用到的图表类型跑 smoke test:出图不抛异常、文件存在、主题与中文字体渲染正确
2. 验证用的临时文件全部清理
