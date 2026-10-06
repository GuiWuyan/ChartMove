"""分布与关系类图表:直方 / 箱线 / 小提琴 / 散点(趋势线)/ 气泡 / 热力。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.patheffects import Normal

from ..render import _ease, _render, _stagger
from ..style import (
    HIGHLIGHT_SIZE,
    _has_spread,
    _legend_bottom,
    _nf,
    _style,
    _theme,
    _vfmt,
    _xlim,
    _ylim,
)
from ..validate import (
    _check_finite,
    _validate_labels,
    _validate_matrix,
    _validate_samples,
    _validate_xy,
)


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
        _vfmt(ax, xs, th, axis='x')
        _vfmt(ax, ys, th)
        _xlim(ax, min(xs), max(xs))  # 散点逐个出现,x 轴必须从首帧钉在最终范围
        handles = [Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                          markerfacecolor=th['palette'][0], label=name)]
        if _has_spread(ys):
            handles += [Line2D([0], [0], linestyle='none', marker='o', markersize=13,
                               markerfacecolor=c, label=t)
                        for c, t in ((th['hi_max'], '最好'), (th['hi_min'], '最差'))]
        _legend_bottom(ax, handles, th)
    return draw


def scatter(title: str, xs, ys, *, name='数值', trend=False, labels=None,
            style='business', animate=False, fmt=None, loop=False, out: str | None = None,
            out_dir=None, figsize=None, dpi=None, numfmt='auto',
            note: str | None = None) -> Path:
    """散点图:x/y 均为数值列表;trend=True 加线性趋势线,labels 可标注每个点。"""
    x, y = _validate_xy(xs, ys)
    lbs = _validate_labels(labels, len(x))
    th = _theme(style, numfmt, note)
    return _render('scatter', title, _scatter_draw(title, x, y, th, name, trend, lbs),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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
        _vfmt(ax, xs, th, axis='x')
        _vfmt(ax, ys, th)
        _xlim(ax, min(xs), max(xs))  # 同散点:气泡逐个出现,x 轴从首帧钉在最终范围
        _legend_bottom(ax, [Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                                   markerfacecolor=th['palette'][0], label=name)], th)
    return draw


def bubble(title: str, xs, ys, sizes, *, name='数值', labels=None, style='business',
           animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
           figsize=None, dpi=None, numfmt='auto',
           note: str | None = None) -> Path:
    """气泡图:scatter + sizes(气泡面积按 sizes 归一);颜色按点轮换主题色板。"""
    x, y = _validate_xy(xs, ys)
    sz = [float(v) for v in sizes]
    if not sz or len(sz) != len(x):
        raise ValueError('sizes 必须非空且与数据长度一致')
    _check_finite(sz, 'sizes')
    lbs = _validate_labels(labels, len(x))
    th = _theme(style, numfmt, note)
    return _render('bubble', title, _bubble_draw(title, x, y, sz, th, name, lbs),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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
        _vfmt(ax, vals, th, axis='x')  # 数值轴是 x(分箱边界);y 是频数计数,不格式化
    return draw


def hist(title: str, values, *, bins=10, style='business', animate=False, fmt=None, loop=False,
         out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """直方图:values 为原始样本,bins 可为整数 / 'auto' / 分箱边界;最高频箱高亮。"""
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError('values 不能为空')
    _check_finite(vals)
    th = _theme(style, numfmt, note)
    return _render('hist', title, _hist_draw(title, vals, bins, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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
        ax.set_xlim(0.5, n + 0.5)  # 箱子逐个出现,x 轴从首帧钉在最终范围
        ax.set_ylim(lo - pad, hi + pad)
        _vfmt(ax, [lo, hi], th)
    return draw


def box(title: str, series, *, style='business', animate=False, fmt=None, loop=False,
        out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
        note: str | None = None) -> Path:
    """箱线图:series=[(组名, 原始样本), ...],各组样本数无需对齐;animate=True 箱体从中位数展开。"""
    ss = _validate_samples(series)
    th = _theme(style, numfmt, note)
    return _render('box', title, _box_draw(title, ss, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _violin_draw(title, groups, th):
    """groups: [(组名, np.ndarray 样本), ...];动画 = 小提琴从中位数向两侧展开。"""
    n = len(groups)
    lo = min(float(a.min()) for _, a in groups)
    hi = max(float(a.max()) for _, a in groups)
    pad = (hi - lo) * 0.12 or 1.0

    def draw(ax, p):
        _style(ax, title, th)
        for i, (_, a) in enumerate(groups):
            pr = _stagger(p, i, n)
            if pr <= 0:  # pr=0 时样本全等于中位数,KDE 协方差奇异,必须跳过
                continue
            med = float(np.median(a))
            # KDE 带宽随样本自适应:向中位数等比收缩的样本画出的就是等比缩小的小提琴
            vp = ax.violinplot([med + (a - med) * pr], positions=[i + 1], widths=0.7,
                               showextrema=False, points=100)
            for body in vp['bodies']:
                body.set_facecolor(th['palette'][i % len(th['palette'])])
                body.set_alpha(0.65)
                body.set_edgecolor(th['axis'])
                body.set_linewidth(1.0)
            q1, _, q3 = (float(v) for v in np.percentile(a, [25, 50, 75]))
            # IQR 线随小提琴一起从中位数生长(solid_capstyle 防止 q1=q3 时画出端点帽)
            ax.plot([i + 1, i + 1], [med + (q1 - med) * pr, med + (q3 - med) * pr],
                    color=th['text'], alpha=0.6 * pr, linewidth=2.5, zorder=5,
                    solid_capstyle='butt')
            ax.scatter([i + 1], [med], s=45, color=th['text'], alpha=pr, zorder=6)
        ax.set_xticks(range(1, n + 1))
        ax.set_xticklabels([nm for nm, _ in groups])
        ax.set_xlim(0.5, n + 0.5)  # 小提琴逐个出现,x 轴从首帧钉在最终范围
        ax.set_ylim(lo - pad, hi + pad)
        _vfmt(ax, [lo, hi], th)
    return draw


def violin(title: str, series, *, style='business', animate=False, fmt=None, loop=False,
           out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
           note: str | None = None) -> Path:
    """小提琴图:series=[(组名, 原始样本), ...],各组样本数无需对齐;KDE 密度形态 +
    组内 IQR 线与中位数点;每组需 ≥2 个不同取值。animate=True 从中位数展开。"""
    ss = _validate_samples(series)
    for nm, vals in ss:
        if len(set(vals)) < 2:  # 零方差会让 gaussian KDE 抛英文 LinAlgError,入口先拦
            raise ValueError(f'小提琴图每组需至少 2 个不同的取值(密度估计要求),'
                             f'系列「{nm}」不满足')
    th = _theme(style, numfmt, note)
    return _render('violin', title,
                   _violin_draw(title, [(nm, np.asarray(v, dtype=float))
                                        for nm, v in ss], th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _heatmap_draw(title, rows, cols, arr, th, annotate=True):
    cmap = LinearSegmentedColormap.from_list(
        'chartmove_seq', [th['face'], th['palette'][0], th['hi_max']])
    vmin, vmax = float(arr.min()), float(arr.max())
    if vmax <= vmin:
        vmax = vmin + 1.0
    imax = np.unravel_index(int(np.argmax(arr)), arr.shape)
    imin = np.unravel_index(int(np.argmin(arr)), arr.shape)
    nr, nc = arr.shape

    def draw(ax, p):
        # 逐格 alpha 渐入:显现前沿 pos 线性推进(不用 _ease,前快后慢会留大段静止帧),
        # 格 j 在 pos∈[j, j+1] 淡入,最后一格恰在 p=1 完成
        pos = p * nc
        alpha = np.broadcast_to(
            np.clip(pos - np.arange(nc)[None, :], 0.0, 1.0), arr.shape).astype(float)
        im = ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto', alpha=alpha)
        cb = ax.figure.colorbar(im, ax=ax, shrink=0.85)
        cb.ax.tick_params(labelsize=11, colors=th['text'])
        cb.outline.set_edgecolor(th['axis'])
        _vfmt(cb.ax, [vmin, vmax], th)  # 色带刻度与格子标注同一格式
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
                    a = float(alpha[i, j])
                    if a <= 0:
                        continue
                    r, g, b, _ = cmap((arr[i, j] - vmin) / (vmax - vmin))
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    ax.text(j, i, _nf(arr[i, j], th), ha='center', va='center',
                            fontsize=11, color='#000000' if lum > 0.55 else '#FFFFFF',
                            alpha=a,
                            path_effects=[Normal()])  # 覆盖 sketch 的 rc 白描边,否则色块内白字糊死
        for idx in (imax, imin):  # 最大/最小格描边:随所在格一起淡入,不再末帧突现
            a = float(alpha[idx[0], idx[1]])
            if a > 0:
                ax.add_patch(Rectangle((idx[1] - 0.5, idx[0] - 0.5), 1, 1, fill=False,
                                       edgecolor=th['text'], linewidth=2.5, alpha=a))
    return draw


def heatmap(title: str, rows, cols, values, *, annotate=True, style='business',
            animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
            figsize=None, dpi=None, numfmt='auto',
            note: str | None = None) -> Path:
    """热力图:values 为 (行数 × 列数) 矩阵;色带取自主题,≤25 格自动标数值,最大/最小格描边。"""
    r, c, arr = _validate_matrix(rows, cols, values)
    th = _theme(style, numfmt, note)
    return _render('heatmap', title, _heatmap_draw(title, r, c, arr, th, annotate),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
