"""chartgen —— 中文数据图表生成器(人可用、AI 可调)。

matplotlib 内核,16 种图表 × 13 主题(4 风格包),输出 PNG / PDF / TIF / GIF / MP4;
入口:CLI 与 MCP Server(GUI 已取消)。

    from chartgen import bar, line, pie, donut, area, combo, line_multi, bar_multi, radar
    path = bar('季度产量', ['Q1', 'Q2', 'Q3'], [120, 200, 90], style='cyberpunk', animate=True)
    # -> .../ChartGen/bar_季度产量.gif
"""
from .core import (
                   THEMES,
                   area,
                   bar,
                   bar_multi,
                   box,
                   bubble,
                   combo,
                   donut,
                   funnel,
                   heatmap,
                   hist,
                   line,
                   line_multi,
                   pie,
                   radar,
                   scatter,
                   waterfall,
)
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS

__version__ = "0.2.0"

__all__ = [
    "bar", "line", "pie", "donut", "area", "combo", "line_multi", "bar_multi",
    "radar", "scatter", "bubble", "hist", "box", "heatmap", "waterfall", "funnel",
    "THEMES", "THEME_PACKS", "THEME_LABELS", "THEME_DESCS", "__version__",
]
