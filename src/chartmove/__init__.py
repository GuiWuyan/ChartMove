"""chartmove —— 中文数据图表生成器:22 种图表、13 套主题分属 4 个风格包,
输出 PNG / PDF / TIF / GIF / MP4;入口 CLI 与 MCP Server。"""
from ._version import __version__
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS, THEMES

__all__ = [
    "bar", "line", "pie", "donut", "area", "combo", "line_multi", "bar_multi",
    "radar", "scatter", "bubble", "hist", "box", "heatmap", "waterfall", "funnel",
    "rose", "themes_preview", "treemap", "gantt", "dumbbell", "sunburst", "pareto",
    "THEMES", "THEME_PACKS", "THEME_LABELS", "THEME_DESCS", "__version__",
]

# 惰性导出(PEP 562):图表函数在 graph 包,import chartmove 不应为此付 matplotlib
# 启动成本(chartmove themes / --version / MCP 启动都走这条路径);首次取属性才加载内核。
_CHART_EXPORTS = frozenset({
    "area", "bar", "bar_multi", "box", "bubble", "combo", "donut", "dumbbell",
    "funnel", "gantt", "heatmap", "hist", "line", "line_multi", "pareto", "pie",
    "radar", "rose", "scatter", "sunburst", "themes_preview", "treemap", "waterfall",
})


def __getattr__(name: str):
    if name in _CHART_EXPORTS:
        from . import graph
        return getattr(graph, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__() -> list[str]:
    return sorted(set(globals()) | _CHART_EXPORTS)
