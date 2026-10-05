"""图表内核:matplotlib 封装,同一份绘图代码输出 PNG / PDF / TIF / GIF / MP4。

约定:animate=True 出 GIF(默认)/ MP4,静态 fmt='png'(默认)/'pdf'/'tif';
GIF 默认播一遍停末帧,loop=True 无限循环(MP4 循环由播放器决定);产物默认写
./Results/(持久,同名自动加序号不覆盖);numfmt='auto' 中文单位万/亿;
不播放动画的场景(如 Word)一律 PNG。
分层:validate 纯校验 / style 视觉与布局 / render 渲染管线 / charts 22 种图按
语义域 5 模块;本 __init__ 只做公开 API 汇总与后端设定。
"""
from __future__ import annotations

import matplotlib

matplotlib.use('Agg')  # 无窗口渲染,必须在 pyplot 之前;导入本包即锁定后端

from ..fonts import setup_fonts
from .charts import themes_preview
from .charts.categorical import bar, bar_multi, pareto, waterfall
from .charts.composition import donut, pie, rose, sunburst, treemap
from .charts.distribution import box, bubble, heatmap, hist, scatter
from .charts.flow import dumbbell, funnel, gantt
from .charts.trend import area, combo, line, line_multi, radar

setup_fonts()  # 中文字体注册:必须在任何绘制发生前完成

__all__ = [
    "bar", "line", "pie", "donut", "area", "combo", "line_multi", "bar_multi",
    "radar", "scatter", "bubble", "hist", "box", "heatmap", "waterfall", "funnel",
    "rose", "themes_preview", "treemap", "gantt", "dumbbell", "sunburst", "pareto",
]
