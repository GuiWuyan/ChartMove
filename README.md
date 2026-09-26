# AI-WORK 项目说明

通过 AI（ZCode）辅助生成 **PPT、PDF、Word** 三类交付文档，并配套渲染质检链路。

## 目录约定
- PPT/    存放生成的 .pptx
- FILE/   存放导出的 PDF 与 Word
- Cache/  存放中间产物，TTL 设置为 3*24（由 TOOLS/cache.py 负责清理）
- TOOLS/  通用工具（reportlab_fonts.py 字体注册、image_fetch.py 配图抓取、chart.py 图表生成、cache.py 缓存清理等公共模块）

## 技术路线
- 生成 PPT：pptxgenjs（Node）为主，复杂排版用 python-pptx
- 图表：TOOLS/chart.py（matplotlib 封装，微软雅黑预设），PNG / GIF / MP4 三种输出，存 Cache/charts/；8 主题（excel / soft / dark / minimal / tech / vivid / business / science）+ 9 种图表类型（柱/折线/多系列折线/饼/环形/面积/双轴/分组柱/雷达）
- PPT 转 PDF：pywin32 调 PowerPoint COM，导出后用 pypdfium2 渲染检查
- 直接生成 PDF：reportlab，先用公共模块注册中文字体（见下节）
- 生成 Word：python-docx
- Word 转 PDF：pywin32 调 Word COM，保真度最高
- md 转 Word / PDF：pandoc（md → docx → PDF，pandoc 需另装）；或 md → HTML 后用 Word COM 另存
- 读取校对：markitdown 提取文本（pptx / docx / pdf）

## 环境配置
```bash

#Pyhon环境
py -3.13 -m venv .venv      #Python可用>=3.13,<3.14
.venv/Scripts/python.exe -m pip install -r requirements.txt

#Node环境
npm install

#可选安装
winget install Gyan.FFmpeg   # 仅动画图表导出 MP4 时需要，可不装
```

## 规范
- 幻灯片 16:9；PPT 中文统一微软雅黑，标题 28–32pt、正文 18–24pt
- reportlab 生成 PDF：标题黑体 SimHei、正文宋体 SimSun
- 每页要点不超过 6 行

## 交付前检查
- 生成后必须实际打开验证（渲染成图或提取文本），确认无乱码、无溢出
