"""主题应用与视觉/布局工具:_style/_legend_* 管坐标轴外观,_nf/_vfmt 管中文数值
格式,_ylim/_xlim/_xticks 落实"动画期间轴固定",_theme 组装主题字典。"""
from __future__ import annotations

import math

import numpy as np
from matplotlib import patheffects
from matplotlib.ticker import FuncFormatter

from ..fonts import sketch_font_chain
from ..themes import THEMES

HIGHLIGHT_SIZE = 650    # 最大/最小值高亮点大小(pt^2)
THIN_TICKS_ABOVE = 25   # 类目超过此数,刻度自动抽稀(再多标签必然互相压盖)
THIN_TICKS_KEEP = 10    # 抽稀后保留的刻度数(含首尾)
MARKER_CAP = 50         # 折线标记数上限:超过则隔点绘制(markevery)


def _style(ax, title: str, th: dict, grid_axis: str | None = None) -> None:
    ax.set_title(title, fontsize=20, pad=18, color=th['text'])
    # spines:'box' 四边框,'none' 全去,默认藏顶右
    hide = {'box': (), 'none': ('top', 'right', 'left', 'bottom')}.get(
        th.get('spines'), ('top', 'right'))
    for side in ('top', 'right', 'left', 'bottom'):
        ax.spines[side].set_visible(side not in hide)
        ax.spines[side].set_color(th['axis'])
    ax.grid(axis=grid_axis or th.get('grid_axis', 'y'), color=th['grid_color'],
            linestyle=th['grid_ls'], linewidth=th['grid_lw'])
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=13, colors=th['text'])
    ax.set_facecolor(th['face'])


def _legend_bottom(ax, handles: list, th: dict, rotated: bool = False) -> None:
    """底部图例;长标签旋转时会与刻度文字重叠,此时自动改放到顶部。"""
    if rotated:
        _legend_top(ax, handles, th)
        return
    if not handles:
        return
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.08),
              ncol=min(len(handles), 5), frameon=False, fontsize=14,
              labelcolor=th['text'], handlelength=1.6, columnspacing=1.8)
    ax.figure.subplots_adjust(bottom=0.14)


def _legend_top(ax, handles: list, th: dict) -> None:
    """图例放绘图区上方,避免与标题重叠。"""
    ax.figure.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.09, 0.985),
                     ncol=min(len(handles), 6), frameon=False, fontsize=13,
                     labelcolor=th['text'], handlelength=1.4, columnspacing=1.5)
    ax.figure.subplots_adjust(top=0.84)


def _ylim(ax, vals: list[float], th: dict) -> None:
    """按完整数据固定 y 轴(动画中轴不跳动);正数且跨度大时从 0 起(Excel 语义)。"""
    lo, hi = min(vals), max(vals)
    if lo >= 0 and lo <= hi * 0.8:
        ax.set_ylim(0, hi * 1.12)
        return
    pad = (hi - lo) or (abs(hi) or 1) * 0.2
    ax.set_ylim(lo - 0.15 * pad, hi + 0.2 * pad)


def _xlim(ax, lo: float, hi: float) -> None:
    """按最终数据范围固定 x 轴(5% 边距与 matplotlib 默认一致,动画中轴不跳动)。"""
    span = hi - lo
    pad = span * 0.05 if span else max(abs(hi), 1) * 0.4
    ax.set_xlim(lo - pad, hi + pad)


def _xticks(ax, cats: list[str], th: dict) -> bool:
    """类目刻度:标签多且长时旋转 30°;超过 THIN_TICKS_ABOVE 自动抽稀到 ~10 个。"""
    n = len(cats)
    if n > THIN_TICKS_ABOVE:
        xs = sorted(set(np.linspace(0, n - 1, THIN_TICKS_KEEP).round().astype(int)))
        labels = [cats[i] for i in xs]
    else:
        xs, labels = list(range(n)), list(cats)
    ax.set_xticks(xs)
    if n > 6 and max(len(c) for c in labels) > 4:
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.figure.subplots_adjust(bottom=0.2)
        return True
    ax.set_xticklabels(labels)
    return False


def _has_spread(vals: list[float]) -> bool:
    return len(vals) >= 2 and max(vals) != min(vals)


def _marker_step(n: int) -> int:
    """折线标记稀疏化:点数超过 MARKER_CAP 时每隔 k 点画一个标记(markevery),线体不变。"""
    return max(1, math.ceil(n / MARKER_CAP))


def _nf(v: float, th: dict) -> str:
    """数值标签/刻度格式化:percent 追加 %,auto 中文单位,plain 原样。"""
    fmt = th.get('numfmt', 'auto')
    if fmt == 'percent':
        return f'{v:g}%'
    if fmt == 'auto':
        if abs(v) >= 1e8:
            return f'{v / 1e8:g}亿'
        if abs(v) >= 1e4:
            return f'{v / 1e4:g}万'
    return f'{v:g}'


def _vfmt(ax, vals, th: dict, axis: str = 'y') -> None:
    """数值轴刻度跟随 numfmt;axis 指定数值轴(默认 y,横向图为 x)。"""
    fmt = th.get('numfmt', 'auto')
    if fmt == 'percent' or (fmt == 'auto' and max(map(abs, vals), default=0) >= 1e4):
        value_axis = ax.xaxis if axis == 'x' else ax.yaxis
        value_axis.set_major_formatter(FuncFormatter(lambda v, _: _nf(v, th)))


def _note(fig, th: dict) -> None:
    """底部左侧脚注(数据来源 / 备注):正文色 55% 透明度,各主题下都退居次要。"""
    note = th.get('note')
    if note:
        fig.text(0.01, 0.012, note, fontsize=11, color=th['text'],
                 alpha=0.55, ha='left', va='bottom')


def _sketch_rc_extra(th: dict, fig_face: str) -> dict:
    """手绘风格的 rc 覆盖:路径抖动 + 西文手写体;非 sketch 主题返回空 dict。"""
    if not th.get('sketch'):
        return {}
    # 逐字回退必须把字体族列表直接给 font.family;泛型 sans-serif 只取首个命中
    return {'path.sketch': (1, 100, 2),
            'font.family': sketch_font_chain(),
            'path.effects': [patheffects.withStroke(linewidth=3, foreground=fig_face)]}


def _squarify(sizes, x, y, w, h):
    """Squarified 树图布局:sizes 降序且面积和 = w*h,返回 [(x, y, w, h)]。"""
    if not sizes:
        return []
    if len(sizes) == 1:
        return [(x, y, w, h)]

    def layout(row, rx, ry, rw, rh):
        out, off = [], 0.0
        if rw >= rh:  # 行铺在左侧竖条,行内纵向堆叠
            strip = sum(row) / rh
            for s in row:
                out.append((rx, ry + off, strip, s / strip))
                off += s / strip
        else:
            strip = sum(row) / rw
            for s in row:
                out.append((rx + off, ry, s / strip, strip))
                off += s / strip
        return out

    def worst(row):
        return max(max(dx / dy, dy / dx)
                   for _, _, dx, dy in layout(row, 0, 0, w, h) if dx and dy)

    i, best = 1, worst(sizes[:1])
    while i < len(sizes):
        wr = worst(sizes[:i + 1])
        if wr < best:
            best, i = wr, i + 1
        else:
            break
    row, rest = sizes[:i], sizes[i:]
    if w >= h:
        strip = sum(row) / h
        return layout(row, x, y, w, h) + _squarify(rest, x + strip, y, w - strip, h)
    strip = sum(row) / w
    return layout(row, x, y, w, h) + _squarify(rest, x, y + strip, w, h - strip)


def _theme(style: str | None, numfmt: str = 'auto', note: str | None = None) -> dict:
    """主题 + 全局展示选项:numfmt 数值格式(auto / plain / percent),note 底部脚注。"""
    if numfmt not in ('auto', 'plain', 'percent'):
        raise ValueError(f'numfmt 仅支持 auto / plain / percent,收到 {numfmt!r}')
    if style and style not in THEMES:  # None / '' 仍回退 business(保持既有调用方兼容)
        raise ValueError(f'未知主题 {style!r};可选:{", ".join(THEMES)}')
    th = THEMES.get(style or 'business', THEMES['business'])
    return dict(th, palette=list(th['palette']), numfmt=numfmt, note=note)
