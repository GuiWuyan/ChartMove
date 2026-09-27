# AGENTS.md — AI 工作规则

本项目是中文数据图表生成器 `chartgen`:matplotlib 内核在 `src/chartgen/`,入口为 CLI 与 MCP(能力总览见 README,开发蓝图见 `docs/plan.md`)。

## 硬性规范

- Python 一律用 `.venv/Scripts/python.exe`;Node 侧无依赖,勿创建 package.json
- 新增 Python 库:装进 .venv 并同步写入 requirements.txt(版本约束用 `>=`,禁用 `>`)
- 图表产物写持久目录(默认 `~/ChartGen/`,可用 `out_dir=` 参数或 `CHARTGEN_OUT_DIR` 环境变量覆盖),绝不做 TTL 清理
- 临时测试文件用完即删
- GUI 已取消(2026-09-27),入口只有 CLI 与 MCP,勿再规划 GUI
- 如果无法依赖现在的环境制作出成品,则反馈给用户原因并道歉

## 技术红线(踩过的坑)

- `matplotlib.use('Agg')` 必须在 pyplot import 之前
- 中文字体跨平台注册在 fonts.py,勿在别处硬编码字体路径;手绘风逐字回退必须把字体族列表直接给 `font.family`
- MCP 用官方 SDK 2.x,服务端类是 `MCPServer`(旧教程的 `FastMCP` 写法已废弃);工具描述用英文写清楚参数,报错消息才用中文

## 交付前必须验证(不过关不许交付)

1. 每种用到的图表类型跑 smoke test:出图不抛异常、文件存在、主题与中文字体渲染正确(跑法:`.venv/Scripts/python.exe -m pytest`)
2. 验证用的临时文件全部清理
