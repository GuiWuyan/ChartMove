"""图表内核:matplotlib 封装,同一份绘图代码输出 PNG / PDF / TIF / GIF / MP4。

13 主题 × 4 风格包(学术 / 商务 / 简约演示 / 其他),定义与元数据见 themes.py;
扩展新主题只需在 THEMES 加一组参数,绘图代码零改动。

    from chartgen import bar, line, pie, donut, area, combo, line_multi, bar_multi, radar
    bar('季度产量', ['Q1', 'Q2', 'Q3'], [120, 200, 90], style='mckinsey', animate=True)
    # -> .../ChartGen/bar_季度产量.gif

约定:animate=True 出 GIF(默认)/ MP4,静态图 fmt='png'(默认)/'pdf'/'tif';
产物默认写 ~/ChartGen/(持久,不做 TTL 清理);不播放动画的场景(如 Word)一律 PNG。
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use('Agg')  # 无窗口渲染,必须在 pyplot 之前
from matplotlib import animation, patheffects
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from .fonts import setup_fonts, sketch_font_chain
from .output import resolve_out_dir, safe_stem
from .themes import THEMES

setup_fonts()

FIGSIZE = (12.8, 7.2)   # 16:9;12.8 * DPI_PNG = 1920px
DPI_PNG = 150
DPI_GIF = 75            # 960px,控制 GIF 体积
DPI_MP4 = 150
DPI_TIF = 600           # 期刊投稿级
GIF_FPS, MP4_FPS, FRAMES = 20, 24, 48
HIGHLIGHT_SIZE = 650    # 最大/最小值高亮点大小(pt^2)

STATIC_FMTS = ('png', 'pdf', 'tif')
ANIMATED_FMTS = ('gif', 'mp4')


# ---------- 内部工具 ----------

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


def _legend_bottom(ax, handles: list, th: dict) -> None:
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


def _ease(t: float) -> float:
    """ease-out 缓动:起步快、收尾慢。"""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def _stagger(p: float, i: int, n: int) -> float:
    """第 i 个元素的局部进度:错峰出现(重叠 60%),实现"逐根升起"。"""
    if n <= 1:
        return _ease(p)
    span = 0.6
    start = i / n * (1 - span)
    return _ease((p - start) / span)


def _ylim(ax, vals: list[float], th: dict) -> None:
    """按完整数据固定 y 轴(动画中轴不跳动);正数且跨度大时从 0 起(Excel 语义)。"""
    lo, hi = min(vals), max(vals)
    if lo >= 0 and lo <= hi * 0.8:
        ax.set_ylim(0, hi * 1.12)
        return
    pad = (hi - lo) or (abs(hi) or 1) * 0.2
    ax.set_ylim(lo - 0.15 * pad, hi + 0.2 * pad)


def _xticks(ax, cats: list[str], th: dict) -> None:
    xs = list(range(len(cats)))
    ax.set_xticks(xs)
    if len(cats) > 6 and max(len(c) for c in cats) > 4:
        ax.set_xticklabels(cats, rotation=30, ha='right')
    else:
        ax.set_xticklabels(cats)


def _has_spread(vals: list[float]) -> bool:
    return len(vals) >= 2 and max(vals) != min(vals)


# ---------- 各图表的绘制函数(静态 = draw(ax, 1.0),动画 = draw(ax, p))----------

def _bar_draw(title, cats, vals, th, horizontal=False):
    def draw(ax, p):
        _style(ax, title, th, grid_axis='x' if horizontal else None)
        hs = [v * _stagger(p, i, len(vals)) for i, v in enumerate(vals)]
        cols = [th['palette'][0]] * len(vals)
        if _has_spread(vals):
            cols[vals.index(max(vals))] = th['hi_max']
            cols[vals.index(min(vals))] = th['hi_min']
        if horizontal:  # 首条目在顶部,适配排名场景
            bars = ax.barh(range(len(vals)), hs, height=0.6, color=cols)
            for i, b in enumerate(bars):
                if _stagger(p, i, len(vals)) > 0.5:
                    ax.text(hs[i], b.get_y() + b.get_height() / 2, f'{vals[i]:g}',
                            va='center', ha='left', fontsize=14, color=th['text'])
            ax.set_xlim(0, max(max(vals) * 1.15, 1))
            ax.set_yticks(range(len(vals)))
            ax.set_yticklabels(cats)
            ax.invert_yaxis()
        else:
            bars = ax.bar(range(len(vals)), hs, width=0.6, color=cols)
            for i, b in enumerate(bars):
                if _stagger(p, i, len(vals)) > 0.5:
                    ax.text(b.get_x() + b.get_width() / 2, hs[i], f'{vals[i]:g}',
                            ha='center', va='bottom', fontsize=14, color=th['text'])
            ax.set_ylim(0, max(max(vals) * 1.15, 1))
            _xticks(ax, cats, th)
    return draw


def _line_draw(title, cats, vals, th, fill=False, name='数值'):
    def draw(ax, p):
        _style(ax, title, th)
        n = len(vals)
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        xr, yr = list(range(k + 1)), list(vals[:k + 1])
        if k + 1 < n:
            xr.append(k + frac)
            yr.append(vals[k] + frac * (vals[k + 1] - vals[k]))
        if fill:
            ax.fill_between(xr, yr, color=th['palette'][0], alpha=0.30)
        ax.plot(xr, yr, color=th['palette'][0], linewidth=4, marker='o', markersize=16)
        if _has_spread(vals):
            for idx, c in ((vals.index(max(vals)), th['hi_max']),
                           (vals.index(min(vals)), th['hi_min'])):
                if pos >= idx:
                    ax.scatter([idx], [vals[idx]], s=HIGHLIGHT_SIZE, color=c,
                               zorder=6, edgecolors=th['face'], linewidths=1.5)
        _ylim(ax, vals, th)
        _xticks(ax, cats, th)
        handles = [Line2D([0], [0], color=th['palette'][0], lw=4, marker='o',
                          markersize=12, label=name)]
        if _has_spread(vals):
            handles += [Line2D([0], [0], linestyle='none', marker='o', markersize=13,
                               markerfacecolor=c, label=t)
                        for c, t in ((th['hi_max'], '最好'), (th['hi_min'], '最差'))]
        _legend_bottom(ax, handles, th)
    return draw


def _line_multi_draw(title, cats, series, th, value_labels=True):
    def draw(ax, p):
        _style(ax, title, th)
        n = len(cats)
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        for si, (nm, vals) in enumerate(series):
            c = th['palette'][si % len(th['palette'])]
            xr, yr = list(range(k + 1)), list(vals[:k + 1])
            if k + 1 < n:
                xr.append(k + frac)
                yr.append(vals[k] + frac * (vals[k + 1] - vals[k]))
            ax.plot(xr, yr, color=c, linewidth=3, marker='o', markersize=9)
            if value_labels and n <= 12:
                for xi in range(k + 1):
                    ax.annotate(f'{vals[xi]:g}', (xi, vals[xi]), textcoords='offset points',
                                xytext=(0, 9), ha='center', fontsize=10, color=c)
        _ylim(ax, [v for _, vals in series for v in vals], th)
        _xticks(ax, cats, th)
        _legend_top(ax, [Line2D([0], [0], color=th['palette'][si % len(th['palette'])],
                                lw=3, marker='o', markersize=9, label=nm)
                         for si, (nm, _) in enumerate(series)], th)
    return draw


def _pie_like_draw(title, cats, vals, th, donut=False, show_values=True):
    def draw(ax, p):
        ax.set_facecolor(th['face'])  # 深色主题下避免露出白色圆形面板
        total = sum(vals) or 1
        sweep = 360 * _ease(p)
        vis, start = [], 0.0
        for v in vals:
            a = 360 * v / total
            vis.append(min(max(sweep - start, 0.0), a))
            start += a
        if sum(vis) <= 0:
            vis[0] = 1e-6  # p=0 时 pie 不接受全 0
        labels = [(f'{c} {v:g}' if show_values else c) if v > 0 else ''
                  for c, v in zip(cats, vals)]
        wedges = dict(edgecolor='white', linewidth=2)
        if donut:
            wedges['width'] = 0.42
        _, texts, autotexts = ax.pie(
            vis, labels=labels, labeldistance=1.12,
            colors=[th['palette'][i % len(th['palette'])] for i in range(len(vals))],
            autopct=(lambda pct: f'{round(pct / 100 * total):g}' if pct > 6 else '')
                    if show_values else None,
            pctdistance=0.79, startangle=90, counterclock=False,
            textprops={'fontsize': 13, 'color': th['text']}, wedgeprops=wedges)
        for at in autotexts:
            at.set_color('white')
            at.set_fontsize(12)
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        _legend_bottom(ax, [Line2D([0], [0], linestyle='none', marker='s', markersize=10,
                                   markerfacecolor=th['palette'][i % len(th['palette'])],
                                   label=c) for i, c in enumerate(cats)], th)
    return draw


def _radar_draw(title, cats, series, th):
    n = len(cats)
    ang = [2 * math.pi * i / n for i in range(n)]
    ang_c = ang + [ang[0]]

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        s = _ease(p)
        for si, (nm, vals) in enumerate(series):
            c = th['palette'][si % len(th['palette'])]
            v_c = [x * s for x in vals] + [vals[0] * s]
            ax.plot(ang_c, v_c, color=c, linewidth=2.5, marker='o', markersize=5)
            ax.fill(ang_c, v_c, color=c, alpha=0.18)
        ax.set_xticks(ang)
        ax.set_xticklabels(cats, fontsize=13, color=th['text'])
        ax.tick_params(axis='x', pad=14)
        top = max(max(v) for _, v in series)
        ax.set_ylim(0, top * 1.15)
        rt = [top * i / 4 for i in (1, 2, 3, 4)]
        ax.set_rgrids(rt, labels=[f'{r:g}' for r in rt], angle=337.5,
                      fontsize=9, color=th['axis'])
        ax.grid(color=th['grid_color'], linestyle=th['grid_ls'], linewidth=th['grid_lw'])
        ax.spines['polar'].set_color(th['axis'])
        ax.set_title(title, fontsize=20, pad=24, color=th['text'])
        _legend_bottom(ax, [Line2D([0], [0], color=th['palette'][si % len(th['palette'])],
                                   lw=3, marker='o', markersize=8, label=nm)
                            for si, (nm, _) in enumerate(series)], th)
        # 极坐标圆等比,顶部必须预留标题空间,否则标题被裁
        ax.figure.subplots_adjust(top=0.80)
    return draw


def _combo_draw(title, cats, bar_vals, line_vals, th, bar_name, line_name):
    def draw(ax, p):
        _style(ax, title, th)
        n = len(cats)
        hs = [v * _stagger(p, i, n) for i, v in enumerate(bar_vals)]
        ax.bar(range(n), hs, width=0.5, color=th['palette'][0])
        ax.set_ylim(0, max(max(bar_vals) * 1.2, 1))
        _xticks(ax, cats, th)

        ax2 = ax.twinx()
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        xr, yr = list(range(k + 1)), list(line_vals[:k + 1])
        if k + 1 < n:
            xr.append(k + frac)
            yr.append(line_vals[k] + frac * (line_vals[k + 1] - line_vals[k]))
        ax2.plot(xr, yr, color=th['palette'][1], linewidth=4, marker='o', markersize=14)
        _ylim(ax2, line_vals, th)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color(th['axis'])
        ax2.tick_params(labelsize=13, colors=th['text'])
        ax2.set_facecolor('none')

        _legend_bottom(ax, [Patch(facecolor=th['palette'][0], label=bar_name),
                            Line2D([0], [0], color=th['palette'][1], lw=4, marker='o',
                                   markersize=12, label=line_name)], th)
    return draw


def _bar_multi_draw(title, cats, series, th):
    m, ng = len(series), len(cats)

    def draw(ax, p):
        _style(ax, title, th)
        w = 0.8 / m
        for si, (nm, vals) in enumerate(series):
            prog = _stagger(p, si, m)
            ax.bar([i + (si - m / 2 + 0.5) * w for i in range(ng)],
                   [v * prog for v in vals], width=w * 0.92,
                   color=th['palette'][si % len(th['palette'])], label=nm)
        ax.set_ylim(0, max(max(v) for _, v in series) * 1.15)
        _xticks(ax, cats, th)
        _legend_top(ax, [Patch(facecolor=th['palette'][si % len(th['palette'])],
                               label=nm) for si, (nm, _) in enumerate(series)], th)
    return draw


def _scatter_draw(title, xs, ys, th, name='数值', trend=False, labels=None):
    n = len(xs)

    def draw(ax, p):
        _style(ax, title, th)
        for i in range(n):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            ax.scatter([xs[i]], [ys[i]], s=120 * (0.3 + 0.7 * pr), color=th['palette'][0],
                       alpha=0.85, edgecolors=th['face'], linewidths=1.2, zorder=5)
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        if _has_spread(ys):
            for idx, c in ((ys.index(max(ys)), th['hi_max']),
                           (ys.index(min(ys)), th['hi_min'])):
                if pos >= idx:
                    ax.scatter([xs[idx]], [ys[idx]], s=HIGHLIGHT_SIZE, color=c, zorder=6,
                               edgecolors=th['face'], linewidths=1.5)
        if trend and n >= 2:
            k, b = np.polyfit(xs, ys, 1)
            x0, x1 = min(xs), max(xs)
            ax.plot([x0, x1], [k * x0 + b, k * x1 + b], color=th['palette'][1],
                    linewidth=2, linestyle='--', alpha=_ease(p), zorder=4)
        if labels:
            for i, lb in enumerate(labels):
                if _stagger(p, i, n) > 0.5:
                    ax.annotate(str(lb), (xs[i], ys[i]), textcoords='offset points',
                                xytext=(0, 10), ha='center', fontsize=11, color=th['text'])
        _ylim(ax, ys, th)
        handles = [Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                          markerfacecolor=th['palette'][0], label=name)]
        if _has_spread(ys):
            handles += [Line2D([0], [0], linestyle='none', marker='o', markersize=13,
                               markerfacecolor=c, label=t)
                        for c, t in ((th['hi_max'], '最好'), (th['hi_min'], '最差'))]
        _legend_bottom(ax, handles, th)
    return draw


def _bubble_draw(title, xs, ys, sizes, th, name='数值', labels=None):
    n = len(xs)
    smin, smax = min(sizes), max(sizes)

    def scale(v):  # 气泡面积归一到 80~1480 pt^2
        if smax <= smin:
            return 400.0
        return 80 + (v - smin) / (smax - smin) * 1400

    def draw(ax, p):
        _style(ax, title, th)
        for i in range(n):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            ax.scatter([xs[i]], [ys[i]], s=scale(sizes[i]) * (0.3 + 0.7 * pr),
                       color=th['palette'][i % len(th['palette'])], alpha=0.65,
                       edgecolors=th['face'], linewidths=1.2, zorder=5)
        if labels:
            for i, lb in enumerate(labels):
                if _stagger(p, i, n) > 0.5:
                    ax.annotate(str(lb), (xs[i], ys[i]), textcoords='offset points',
                                xytext=(0, 10), ha='center', fontsize=11, color=th['text'])
        _ylim(ax, ys, th)
        _legend_bottom(ax, [Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                                   markerfacecolor=th['palette'][0], label=name)], th)
    return draw


def _hist_draw(title, vals, bins, th):
    heights, edges = np.histogram(vals, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    widths = np.diff(edges)
    tallest = int(np.argmax(heights))

    def draw(ax, p):
        _style(ax, title, th)
        for i, h in enumerate(heights):
            pr = _stagger(p, i, len(heights))
            col = th['hi_max'] if i == tallest and heights[tallest] > 0 else th['palette'][0]
            ax.bar(centers[i], h * pr, width=widths[i] * 0.96, color=col)
        ax.set_ylim(0, max(heights.max() * 1.15, 1))
    return draw


def _box_draw(title, series, th):
    stats = []
    for nm, samples in series:
        a = np.asarray(samples, dtype=float)
        q1, med, q3 = np.percentile(a, [25, 50, 75])
        iqr = q3 - q1
        stats.append(dict(
            label=nm, med=med, q1=q1, q3=q3,
            whislo=a[a >= q1 - 1.5 * iqr].min(), whishi=a[a <= q3 + 1.5 * iqr].max()))
    n = len(stats)
    lo = min(st['whislo'] for st in stats)
    hi = max(st['whishi'] for st in stats)
    pad = (hi - lo) * 0.12 or 1.0

    def draw(ax, p):
        _style(ax, title, th)
        pos_idx, shown = [], []
        for i, st in enumerate(stats):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            # 箱体从 中位数 向外展开(逐帧 lerp),保持 q1<=med<=q3 单调
            grown = {k: st[k] + (st['med'] - st[k]) * (1 - pr)
                     for k in ('q1', 'q3', 'whislo', 'whishi')}
            pos_idx.append(i + 1)
            shown.append({'med': st['med'], **grown})
        if shown:
            bp = ax.bxp(shown, positions=pos_idx, widths=0.5, patch_artist=True,
                        showfliers=False, boxprops=dict(edgecolor=th['axis']),
                        whiskerprops=dict(color=th['axis']),
                        capprops=dict(color=th['axis']),
                        medianprops=dict(color=th['text'], linewidth=2))
            for b in bp['boxes']:
                b.set_facecolor(th['palette'][0])
                b.set_alpha(0.75)
        ax.set_xticks(range(1, n + 1))
        ax.set_xticklabels([nm for nm, _ in series])
        ax.set_ylim(lo - pad, hi + pad)
    return draw


def _heatmap_draw(title, rows, cols, arr, th, annotate=True):
    cmap = LinearSegmentedColormap.from_list(
        'chartgen_seq', [th['face'], th['palette'][0], th['hi_max']])
    vmin, vmax = float(arr.min()), float(arr.max())
    if vmax <= vmin:
        vmax = vmin + 1.0
    imax = np.unravel_index(int(np.argmax(arr)), arr.shape)
    imin = np.unravel_index(int(np.argmin(arr)), arr.shape)
    nr, nc = arr.shape

    def draw(ax, p):
        pos = _ease(p) * nc  # 从左到右逐列显现(用逐格 alpha,避免全遮罩帧)
        alpha = np.broadcast_to(np.arange(nc)[None, :] < pos, arr.shape).astype(float)
        im = ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto', alpha=alpha)
        cb = ax.figure.colorbar(im, ax=ax, shrink=0.85)
        cb.ax.tick_params(labelsize=11, colors=th['text'])
        cb.outline.set_edgecolor(th['axis'])
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        ax.set_xticks(range(nc))
        ax.set_xticklabels(cols, fontsize=13, color=th['text'])
        ax.set_yticks(range(nr))
        ax.set_yticklabels(rows, fontsize=13, color=th['text'])
        ax.tick_params(colors=th['axis'])
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            ax.spines[side].set_color(th['axis'])
        ax.set_facecolor(th['face'])
        ax.invert_yaxis()
        if annotate and nr * nc <= 25:
            for i in range(nr):
                for j in range(nc):
                    if j >= pos:
                        continue
                    r, g, b, _ = cmap((arr[i, j] - vmin) / (vmax - vmin))
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    ax.text(j, i, f'{arr[i, j]:g}', ha='center', va='center',
                            fontsize=11, color='#000000' if lum > 0.55 else '#FFFFFF')
        if p >= 0.98:  # 最大/最小格子描边
            for idx in (imax, imin):
                ax.add_patch(Rectangle((idx[1] - 0.5, idx[0] - 0.5), 1, 1, fill=False,
                                       edgecolor=th['text'], linewidth=2.5))
    return draw


def _waterfall_draw(title, cats, vals, th):
    bars, acc = [], 0.0  # (label, value 或 None=合计, 起点)
    for c, v in zip(cats, vals):
        bars.append((c, v, acc))
        acc += v
    bars.append(('合计', None, acc))

    def draw(ax, p):
        _style(ax, title, th)
        ends = []
        for i, (c, v, base) in enumerate(bars):
            pr = _stagger(p, i, len(bars))
            ends.append(base + (v or 0.0))
            if v is None:  # 合计柱
                col = th['hi_min']
                bottom = base * pr if base >= 0 else base * (1 - pr)
                h, text = abs(base) * pr, f'{base:g}'
            elif v >= 0:
                col, bottom, h, text = th['palette'][0], base, v * pr, f'{v:g}'
            else:
                col, bottom, h, text = th['hi_max'], base + v * (1 - pr), abs(v) * pr, f'{v:g}'
            if pr <= 0:
                continue
            ax.bar(i, h, bottom=bottom, width=0.6, color=col)
            if pr > 0.5:
                ax.text(i, bottom + h, text, ha='center', va='bottom',
                        fontsize=14, color=th['text'])
            if i > 0 and _stagger(p, i, len(bars)) > 0:  # 与上一柱顶部相连的桥线
                ax.plot([i - 1 + 0.3, i - 0.3], [ends[i - 1]] * 2,
                        color=th['axis'], linewidth=1, alpha=pr)
        levels = [0.0] + ends
        lo, hi = min(levels), max(levels)
        pad = (hi - lo) * 0.12 or 1.0
        ax.set_ylim(lo - pad, hi + pad)
        _xticks(ax, [b[0] for b in bars], th)
    return draw


def _funnel_draw(title, cats, vals, th):
    vmax = max(vals) or 1

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        ax.axis('off')  # 漏斗无坐标轴,标签直接画在图上
        n = len(cats)
        for i, (c, v) in enumerate(zip(cats, vals)):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            w = v * pr / vmax
            ax.barh(i, w, left=(1 - w) / 2, height=0.72,
                    color=th['palette'][i % len(th['palette'])])
            if pr > 0.6:
                rate = f'  ({v / vals[i - 1] * 100:.0f}%)' if i and vals[i - 1] else ''
                ax.text(1.02, i, f'{c} {v:g}{rate}', va='center', ha='left',
                        fontsize=13, color=th['text'])
        ax.set_xlim(0, 1.55)
        ax.invert_yaxis()
    return draw


# ---------- 渲染 ----------

class _OncePillowWriter(animation.PillowWriter):
    """GIF 播一遍停在末帧:不写 NETSCAPE 循环扩展,避免在 PPT 里无限重播。"""

    def finish(self):
        self._frames[0].save(
            self.outfile, save_all=True, append_images=self._frames[1:],
            duration=int(1000 / self.fps))


def _render(kind, title, draw, *, animate, fmt, out, out_dir=None,
            polar: bool = False, figsize=None, dpi=None,
            th: dict | None = None) -> Path:
    th = th or {}
    face = th.get('face', 'white')
    fig_face = th.get('fig_face') or face
    rc_extra: dict = {}
    if th.get('sketch'):  # 手绘风:路径抖动 + 西文手写体
        # 逐字回退必须把字体族列表直接给 font.family;泛型 sans-serif 只取首个命中
        rc_extra = {'path.sketch': (1, 100, 2),
                    'font.family': sketch_font_chain(),
                    'path.effects': [patheffects.withStroke(linewidth=3, foreground=fig_face)]}

    with plt.rc_context(rc_extra):
        out_path = resolve_out_dir(out_dir)
        stem = safe_stem(kind, title, out)
        fmt = (fmt or ('gif' if animate else 'png')).lower()
        fig_size = figsize or FIGSIZE

        if animate:
            if fmt not in ANIMATED_FMTS:
                raise ValueError(f'动画仅支持 {" / ".join(ANIMATED_FMTS)} 格式,收到 fmt={fmt!r};'
                                 f'静态图请用 animate=False(fmt 可选 {" / ".join(STATIC_FMTS)})')
            if fmt == 'mp4':
                if not shutil.which('ffmpeg'):
                    raise RuntimeError('未找到 ffmpeg(MP4 需要)。'
                                       '安装:winget install Gyan.FFmpeg,或改用 fmt="gif"')
                writer = animation.FFMpegWriter(fps=MP4_FPS, codec='h264',
                                                extra_args=['-pix_fmt', 'yuv420p'])
                path, fps, dpi_eff = out_path / f'{stem}.mp4', MP4_FPS, (dpi or DPI_MP4)
            else:
                writer = _OncePillowWriter(fps=GIF_FPS)
                path, fps, dpi_eff = out_path / f'{stem}.gif', GIF_FPS, (dpi or DPI_GIF)

            fig = plt.figure(figsize=fig_size, facecolor=fig_face)

            def update(i):
                fig.clear()  # 连同 twinx 一起清空,避免帧间残留
                draw(fig.add_subplot(111, polar=polar), i / (FRAMES - 1))

            ani = animation.FuncAnimation(fig, update, frames=FRAMES, interval=1000 / fps)
            try:
                ani.save(path, writer=writer, dpi=dpi_eff,
                         savefig_kwargs={'facecolor': fig_face})
            finally:
                plt.close('all')
        else:
            if fmt not in STATIC_FMTS:
                raise ValueError(f'静态图支持 {" / ".join(STATIC_FMTS)},收到 fmt={fmt!r};'
                                 '动画请传 animate=True(仅 gif / mp4)')
            path = out_path / f'{stem}.{fmt}'
            dpi_eff = dpi or (DPI_TIF if fmt == 'tif' else DPI_PNG)
            fig = plt.figure(figsize=fig_size, facecolor=fig_face)
            draw(fig.add_subplot(111, polar=polar), 1.0)
            fig.savefig(path, dpi=dpi_eff, facecolor=fig_face)
            plt.close(fig)

        print(f'图表已生成: {path}')
        return path


def _validate(categories, values) -> tuple[list, list]:
    cats = [str(c) for c in categories]
    vals = [float(v) for v in values]
    if not cats or len(cats) != len(vals):
        raise ValueError('categories 与 values 必须非空且长度一致')
    return cats, vals


def _validate_series(categories, series) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...],各系列长度须与类目一致。"""
    if isinstance(series, dict):
        series = list(series.items())
    out = []
    for item in series:
        nm, vals = item
        _, v = _validate(categories, vals)
        out.append((str(nm), v))
    if not out:
        raise ValueError('series 不能为空')
    return out


def _validate_xy(xs, ys) -> tuple[list[float], list[float]]:
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    if not x or len(x) != len(y):
        raise ValueError('x 与 y 必须非空且长度一致')
    return x, y


def _validate_labels(labels, n: int) -> list[str] | None:
    if labels is None:
        return None
    lbs = [str(lb) for lb in labels]
    if len(lbs) != n:
        raise ValueError('labels 与数据长度必须一致')
    return lbs


def _validate_samples(series) -> list[tuple[str, list[float]]]:
    """箱线图 series=[(组名, 原始样本), ...],各组样本数无需对齐。"""
    if isinstance(series, dict):
        series = list(series.items())
    out = []
    for item in series:
        nm, samples = item
        vals = [float(v) for v in samples]
        if not vals:
            raise ValueError('每个系列的样本数据不能为空')
        out.append((str(nm), vals))
    if not out:
        raise ValueError('series 不能为空')
    return out


def _validate_matrix(rows, cols, values) -> tuple[list[str], list[str], np.ndarray]:
    r, c = [str(x) for x in rows], [str(x) for x in cols]
    try:
        arr = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError('values 必须是二维数值矩阵') from e
    if arr.ndim != 2 or not r or not c or arr.shape != (len(r), len(c)):
        raise ValueError('values 必须是 (行数 × 列数) 的二维数值矩阵')
    return r, c, arr


def _theme(style: str | None) -> dict:
    th = THEMES.get(style or 'business', THEMES['business'])
    return dict(th, palette=list(th['palette']))


# ---------- 公开 API ----------

def bar(title: str, categories, values, *, style='business', animate=False, fmt=None,
        out: str | None = None, out_dir=None, horizontal=False,
        figsize=None, dpi=None) -> Path:
    """柱状图(values 需 >=0):最大/最小高亮;horizontal=True 横向条形,animate=True 逐根升起。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('bar', title, _bar_draw(title, cats, vals, th, horizontal),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def line(title: str, categories, values, *, name='销售额', style='business',
         animate=False, fmt=None, out: str | None = None, out_dir=None,
         figsize=None, dpi=None) -> Path:
    """单系列折线:粗线大圆点,最大/最小高亮;animate=True 渐进绘制。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('line', title, _line_draw(title, cats, vals, th, name=name),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def line_multi(title: str, categories, series, *, value_labels=True, style='business',
               animate=False, fmt=None, out: str | None = None, out_dir=None,
               figsize=None, dpi=None) -> Path:
    """多系列折线:series=[(名称, 数值列表), ...],图例在顶部,可带数值标注。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('line_multi', title,
                   _line_multi_draw(title, cats, ss, th, value_labels),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def area(title: str, categories, values, *, name='数值', style='business',
         animate=False, fmt=None, out: str | None = None, out_dir=None,
         figsize=None, dpi=None) -> Path:
    """面积图:折线 + 半透明填充;animate=True 渐进填充。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('area', title, _line_draw(title, cats, vals, th, fill=True, name=name),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def pie(title: str, categories, values, *, style='business', animate=False, fmt=None,
        out: str | None = None, out_dir=None, figsize=None, dpi=None) -> Path:
    """饼图(values 需 >=0);animate=True 扇区展开。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('pie', title, _pie_like_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def donut(title: str, categories, values, *, show_values=True, style='business',
          animate=False, fmt=None, out: str | None = None, out_dir=None,
          figsize=None, dpi=None) -> Path:
    """环形图:外部"类目 数值"标注 + 底部图例;animate=True 扇区展开。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('donut', title, _pie_like_draw(title, cats, vals, th, donut=True,
                                                  show_values=show_values),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def radar(title: str, categories, series, *, style='business',
          animate=False, fmt=None, out: str | None = None, out_dir=None,
          figsize=None, dpi=None) -> Path:
    """雷达图:series=[(名称, 数值列表), ...];animate=True 多边形从中心展开。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('radar', title, _radar_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   polar=True, th=th, figsize=figsize, dpi=dpi)


def combo(title: str, categories, bar_values, line_values, *,
          bar_name='柱状', line_name='折线', style='business',
          animate=False, fmt=None, out: str | None = None, out_dir=None,
          figsize=None, dpi=None) -> Path:
    """双轴组合图:柱状(左轴)+ 折线(右轴),animate=True 同步生长。"""
    cats, bv = _validate(categories, bar_values)
    _, lv = _validate(categories, line_values)
    th = _theme(style)
    draw = _combo_draw(title, cats, bv, lv, th, bar_name, line_name)
    return _render('combo', title, draw, animate=animate, fmt=fmt, out=out,
                   out_dir=out_dir, th=th, figsize=figsize, dpi=dpi)


def bar_multi(title: str, categories, series, *, style='business',
              animate=False, fmt=None, out: str | None = None, out_dir=None,
              figsize=None, dpi=None) -> Path:
    """多系列分组柱状图:series=[(名称, 数值列表), ...],图例在顶部。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('bar_multi', title, _bar_multi_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def scatter(title: str, xs, ys, *, name='数值', trend=False, labels=None,
            style='business', animate=False, fmt=None, out: str | None = None,
            out_dir=None, figsize=None, dpi=None) -> Path:
    """散点图:x/y 均为数值列表;trend=True 加线性趋势线,labels 可标注每个点。"""
    x, y = _validate_xy(xs, ys)
    lbs = _validate_labels(labels, len(x))
    th = _theme(style)
    return _render('scatter', title, _scatter_draw(title, x, y, th, name, trend, lbs),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def bubble(title: str, xs, ys, sizes, *, name='数值', labels=None, style='business',
           animate=False, fmt=None, out: str | None = None, out_dir=None,
           figsize=None, dpi=None) -> Path:
    """气泡图:scatter + sizes(气泡面积按 sizes 归一);颜色按点轮换主题色板。"""
    x, y = _validate_xy(xs, ys)
    sz = [float(v) for v in sizes]
    if not sz or len(sz) != len(x):
        raise ValueError('sizes 必须非空且与数据长度一致')
    lbs = _validate_labels(labels, len(x))
    th = _theme(style)
    return _render('bubble', title, _bubble_draw(title, x, y, sz, th, name, lbs),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def hist(title: str, values, *, bins=10, style='business', animate=False, fmt=None,
         out: str | None = None, out_dir=None, figsize=None, dpi=None) -> Path:
    """直方图:values 为原始样本,bins 可为整数 / 'auto' / 分箱边界;最高频箱高亮。"""
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError('values 不能为空')
    th = _theme(style)
    return _render('hist', title, _hist_draw(title, vals, bins, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def box(title: str, series, *, style='business', animate=False, fmt=None,
        out: str | None = None, out_dir=None, figsize=None, dpi=None) -> Path:
    """箱线图:series=[(组名, 原始样本), ...],各组样本数无需对齐;animate=True 箱体从中位数展开。"""
    ss = _validate_samples(series)
    th = _theme(style)
    return _render('box', title, _box_draw(title, ss, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def heatmap(title: str, rows, cols, values, *, annotate=True, style='business',
            animate=False, fmt=None, out: str | None = None, out_dir=None,
            figsize=None, dpi=None) -> Path:
    """热力图:values 为 (行数 × 列数) 矩阵;色带取自主题,≤25 格自动标数值,最大/最小格描边。"""
    r, c, arr = _validate_matrix(rows, cols, values)
    th = _theme(style)
    return _render('heatmap', title, _heatmap_draw(title, r, c, arr, th, annotate),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def waterfall(title: str, categories, values, *, total=True, style='business',
              animate=False, fmt=None, out: str | None = None, out_dir=None,
              figsize=None, dpi=None) -> Path:
    """瀑布图:values 为逐项增减(正=升/负=降),total=True 自动补"合计"柱。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('waterfall', title,
                   _waterfall_draw(title, cats, list(vals) + [None] if total else list(vals),
                                   th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def funnel(title: str, categories, values, *, style='business', animate=False, fmt=None,
           out: str | None = None, out_dir=None, figsize=None, dpi=None) -> Path:
    """漏斗图:按给定顺序从上到下,自动标注逐级转化率;values 需 >=0。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('漏斗图 values 需 >=0')
    th = _theme(style)
    return _render('funnel', title, _funnel_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
