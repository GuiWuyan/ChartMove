# AGENTS.md — AI 工作规则

本项目用 AI 生成 PPT、PDF、Word 交付文档。项目背景与技术栈见 README.md。
以下规则每次会话都必须遵守；规范数值以本文件为准，改动时同步 README。

## 技术选型

- 生成 PPT：pptxgenjs（Node，首选）；复杂排版用 python-pptx
- 生成 PDF：
  - PPT 转 PDF：PowerPoint COM（pywin32），保真度最高，优先于任何第三方转换
  - 直接排版：reportlab，中文字体一律 `from TOOLS.reportlab_fonts import FONT_HEI, FONT_SONG`，禁止手写字体名字符串
- 生成 Word：python-docx；docx → PDF 用 Word COM（pywin32）
- md 转 Word / PDF：pandoc（md → docx → PDF）
- 读取校对：markitdown（pptx / docx / pdf → Markdown）；PDF 视觉检查用 pypdfium2 渲染成图

## 产出与目录

- `.pptx` 写入 `PPT/`；md、PDF、Word 及导出成品写入 `FILE/`；中间产物写入 `Cache/`（TTL 3 天）
- 每个生成任务开始时先调 `TOOLS.cache.clean_cache()` 惰性清理 Cache/；长期不跑项目时由定时任务兜底执行 `python TOOLS/cache.py`
- 交付文件命名：`主题_YYYYMMDD.扩展名`；临时测试文件用完即删，不许留在 PPT/ 或 FILE/
- 禁止改动 `node_modules/`、`.venv/` 内部，禁止删除用户已有文件

## 硬性规范

- 幻灯片 16:9；PPT 中文统一微软雅黑，标题 28–32pt、正文 18–24pt，每页要点不超过 6 行
- reportlab PDF：标题 FONT_HEI、正文 FONT_SONG；PDF 脚本从项目根目录运行
- Python 一律用 `.venv/Scripts/python.exe`；Node 脚本从项目根目录运行
- 如果无法依赖现在的环境制作出成品，则反馈给用户原因并道歉

## 依赖管理

- 新增 Python 库：装进 .venv 并同步写入 requirements.txt（版本约束用 `>=`，禁用 `>`）
- 新增 Node 库：同步写入 package.json

## 交付前必须验证（不过关不许交付）

1. PDF：pypdfium2 渲染成图，检查乱码、文字溢出、字体是否正确嵌入
2. PPT / Word：markitdown 提取文本，校对内容完整、无乱码
3. 验证用的临时文件全部清理
