"""中文字体注册,跨平台。

现按平台候选列表依次查找,全找不到时回退 DejaVu 并打印警告(macOS / Linux 实际渲染效果待实测。
"""
from __future__ import annotations

import sys
from pathlib import Path

from matplotlib import rcParams
from matplotlib.font_manager import FontProperties, fontManager

# 按平台依次尝试的字体文件,命中即注册(Windows:雅黑→黑体;macOS:苹方;Linux:Noto CJK)
_FILE_CANDIDATES: dict[str, tuple[str, ...]] = {
    'win32': ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'),
    'darwin': (
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
    ),
    'linux': (
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    ),
}

# 候选文件全落空时,在系统已注册字体里按族名兜底扫描(覆盖各发行版自定义安装路径)
_KNOWN_FAMILIES = (
    'Microsoft YaHei', 'SimHei', 'PingFang SC', 'Hiragino Sans GB',
    'Noto Sans CJK SC', 'Noto Sans SC', 'Source Han Sans SC', 'WenQuanYi Micro Hei',
)

FAMILY: str | None = None  # 命中的中文字体族名;None = 回退 DejaVu(中文可能显示为方框)


def setup_fonts() -> str | None:
    """注册平台中文字体并设为 sans-serif 首选,返回命中的字体族名(未找到为 None)。"""
    global FAMILY
    for fp in _FILE_CANDIDATES.get(sys.platform, ()):
        if Path(fp).exists():
            fontManager.addfont(fp)
            FAMILY = FontProperties(fname=fp).get_name()
            break
    if FAMILY is None:
        installed = {entry.name for entry in fontManager.ttflist}
        FAMILY = next((fam for fam in _KNOWN_FAMILIES if fam in installed), None)
    if FAMILY is not None:
        rcParams['font.sans-serif'] = [FAMILY, 'DejaVu Sans']
    else:
        print('chartmove: 未找到中文字体,中文可能显示为方框;'
              '请安装 微软雅黑(Windows)/ PingFang(macOS)/ Noto Sans CJK(Linux)',
              file=sys.stderr)
    rcParams['axes.unicode_minus'] = False   # 坐标轴负号
    rcParams['font.size'] = 14
    return FAMILY


# 手绘风可用的西文手写体,按优先级排列(本机装了哪个用哪个)
_COMIC_FAMILIES = ('Comic Sans MS', 'Comic Neue', 'xkcd', 'xkcd Script')


def sketch_font_chain() -> list[str]:
    """手绘草图风的字体链:手写体在前(西文/数字),中文逐字回退平台字体。

    matplotlib >=3.6 支持字体列表逐字回退,因此中文落到 FAMILY 时不会出方框。
    """
    installed = {entry.name for entry in fontManager.ttflist}
    return [fam for fam in _COMIC_FAMILIES if fam in installed] + [FAMILY or 'DejaVu Sans']
