"""reportlab 中文字体注册（全项目公共模块）。

import 本模块即完成注册（幂等），之后所有地方直接用字体名常量：

    from TOOLS.reportlab_fonts import FONT_HEI, FONT_SONG

    c.setFont(FONT_HEI, 16)             # canvas
    ParagraphStyle(fontName=FONT_SONG)  # platypus

项目规范：PDF 标题用黑体、正文用宋体；微软雅黑为备选。
"""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

FONT_HEI = 'SimHei'          # 黑体（标题）
FONT_SONG = 'SimSun'         # 宋体（正文）
FONT_YAHEI = 'MSYH'          # 微软雅黑（备选）
FONT_YAHEI_BOLD = 'MSYH-Bold'

# (注册名, 字体文件路径, subfontIndex)——.ttc 是字体集合文件，必须指定子字体索引
_FONT_FILES = [
    (FONT_HEI, 'C:/Windows/Fonts/simhei.ttf', 0),
    (FONT_SONG, 'C:/Windows/Fonts/simsun.ttc', 0),
    (FONT_YAHEI, 'C:/Windows/Fonts/msyh.ttc', 0),
    (FONT_YAHEI_BOLD, 'C:/Windows/Fonts/msyhbd.ttc', 0),
]

_registered = False


def register_chinese_fonts():
    """注册全部中文字体；可重复调用，只有第一次真正执行。"""
    global _registered
    if _registered:
        return
    for name, path, index in _FONT_FILES:
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))
    # 宋体没有独立粗体文件，按中文排版习惯用黑体充当其粗体
    registerFontFamily(FONT_SONG, normal=FONT_SONG, bold=FONT_HEI,
                       italic=FONT_SONG, boldItalic=FONT_HEI)
    # 雅黑有独立粗体文件
    registerFontFamily(FONT_YAHEI, normal=FONT_YAHEI, bold=FONT_YAHEI_BOLD,
                       italic=FONT_YAHEI, boldItalic=FONT_YAHEI_BOLD)
    _registered = True


register_chinese_fonts()
