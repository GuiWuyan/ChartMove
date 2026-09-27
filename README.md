# AI-WORK 项目说明(数据图表工具)

数据图表生成工具——`chartgen`(开发蓝图见 [FILE/制图工具开发方案_20260927.md](制图工具开发方案_20260927.md))的前身与开发跳板。
原 PPT / PDF / Word 文档生成能力已移除;PPT 生成由独立的 PPT Master 项目承担。

## 目录约定
- TOOLS/chart.py  图表生成核心(matplotlib 封装,微软雅黑中文预设,import 即用)
- Cache/charts/   图表产物(现状;迁移新仓库后改持久输出目录)
- FILE/           开发方案等长期文档

## 图表能力
- 9 种类型:柱状 / 分组柱状 / 折线 / 多系列折线 / 面积 / 饼 / 环形 / 双轴组合 / 雷达;`bar` 规划支持 `horizontal=True` 出横向条形(排名场景)
- 8 套主题:excel(默认)/ soft / dark / minimal / tech / vivid / business / science
- 输出:PNG(1920×1080)/ GIF(数据生长动画,播一遍停末帧)/ MP4(需 ffmpeg);规划增加 pdf 矢量与 600dpi tif(期刊投稿)
- 差异化:最大/最小值自动高亮、y 轴智能从 0 起、GIF 停帧适配 PPT 放映

## 环境配置
```bash
py -3.13 -m venv .venv      # Python >=3.10,<3.14
.venv/Scripts/python.exe -m pip install -r requirements.txt
winget install Gyan.FFmpeg   # 可选,仅 MP4 动画需要
```

依赖:matplotlib、mcp(官方 MCP SDK,2.x 起 API 为 MCPServer)、pillow、pywin32。
