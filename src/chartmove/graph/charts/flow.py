"""流程与进度类图表:漏斗(自动转化率)/ 甘特 / 哑铃(坡度)。"""
from __future__ import annotations

from pathlib import Path

from matplotlib.lines import Line2D

from ..render import _render, _stagger
from ..style import (
    _has_spread,
    _legend_bottom,
    _nf,
    _style,
    _theme,
    _vfmt,
    _ylim,
)
from ..validate import _validate, _validate_series


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
                ax.text(1.02, i, f'{c} {_nf(v, th)}{rate}', va='center', ha='left',
                        fontsize=13, color=th['text'])
        ax.set_xlim(0, 1.55)
        ypad = 0.05 * (n - 1 + 0.72)  # 柱高 0.72 的 y 范围 + 5% 边距,轴从首帧固定
        ax.set_ylim(-0.36 - ypad, n - 1 + 0.36 + ypad)
        ax.invert_yaxis()
    return draw


def funnel(title: str, categories, values, *, style='business', animate=False, fmt=None, loop=False,
           out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
           note: str | None = None) -> Path:
    """漏斗图:按给定顺序从上到下,自动标注逐级转化率;values 需 >=0。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('漏斗图 values 需 >=0')
    th = _theme(style, numfmt, note)
    return _render('funnel', title, _funnel_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _gantt_draw(title, tasks, starts, ends, th):
    n = len(tasks)
    lo, hi = min(starts), max(ends)
    span = (hi - lo) or 1.0
    durs = [e - s for s, e in zip(starts, ends)]

    def draw(ax, p):
        _style(ax, title, th, grid_axis='x')
        for i in range(n):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            col = th['palette'][0]
            if _has_spread(durs):  # 语义默认值:工期最长高亮、最短弱化
                col = (th['hi_max'] if i == durs.index(max(durs))
                       else th['hi_min'] if i == durs.index(min(durs)) else col)
            s, e = starts[i], starts[i] + durs[i] * pr  # 从起点向右生长
            ax.barh(i, e - s, left=s, height=0.55, color=col)
            if pr > 0.5:
                ax.text(e + span * 0.012, i, f'{_nf(starts[i], th)}–{_nf(ends[i], th)}',
                        va='center', ha='left', fontsize=12, color=th['text'])
        ax.set_yticks(range(n))
        ax.set_yticklabels(tasks)
        ax.invert_yaxis()  # 首任务在顶
        ax.set_xlim(lo - span * 0.02, hi + span * 0.14)  # 右侧留给起止标注
        _vfmt(ax, [*starts, *ends], th, axis='x')
    return draw


def gantt(title: str, tasks, starts, ends, *, style='business', animate=False, fmt=None,
          loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """甘特图:tasks 为任务名,starts/ends 为数值(日期轴暂不支持),ends >= starts。"""
    tsks, ss = _validate(tasks, starts)
    _, es = _validate(tasks, ends)
    if any(e < s for s, e in zip(ss, es)):
        bad = next(i for i, (s, e) in enumerate(zip(ss, es)) if e < s)
        raise ValueError(f'甘特图 ends 需 >= starts(任务「{tsks[bad]}」结束早于开始)')
    th = _theme(style, numfmt, note)
    return _render('gantt', title, _gantt_draw(title, tsks, ss, es, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _dumbbell_draw(title, cats, name_a, va, name_b, vb, th, slope):
    n = len(cats)

    def draw(ax, p):
        _style(ax, title, th, grid_axis=None if slope else 'x')
        if slope:  # 坡度图:期初/期末两列,每类别一条斜线
            for i in range(n):
                pr = _stagger(p, i, n)
                if pr <= 0:
                    continue
                col = th['palette'][i % len(th['palette'])]
                ax.plot([0.0, pr], [va[i], va[i] + (vb[i] - va[i]) * pr],
                        color=col, linewidth=3, marker='o', markersize=11,
                        markeredgecolor=th['face'], markeredgewidth=1.2)
                if pr > 0.5:
                    ax.text(-0.03, va[i], _nf(va[i], th), ha='right', va='center',
                            fontsize=12, color=th['text'], zorder=7)
                    ax.text(1.03, vb[i], f'{cats[i]} {_nf(vb[i], th)}', ha='left',
                            va='center', fontsize=12, color=th['text'], zorder=7)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([name_a, name_b])
            ax.set_xlim(-0.32, 1.42)
            _ylim(ax, list(va) + list(vb), th)
            _vfmt(ax, list(va) + list(vb), th)
        else:  # 哑铃图:横向,类别在 y 轴
            all_vals = list(va) + list(vb)
            lo, hi = min(all_vals), max(all_vals)
            pad = (hi - lo) * 0.14 or 1.0
            off = (hi - lo) * 0.02 or 0.3  # 标签离开圆点,避免被压住
            for i in range(n):
                pr = _stagger(p, i, n)
                if pr <= 0:
                    continue
                mid = va[i] + (vb[i] - va[i]) * pr  # 连线从期初点长到期末点
                ax.plot([va[i], mid], [i, i], color=th['axis'], linewidth=3)
                ax.scatter([va[i]], [i], s=120, color=th['axis'], zorder=5,
                           edgecolors=th['face'], linewidths=1.2)
                ax.scatter([mid], [i], s=150, color=th['palette'][0], zorder=6,
                           edgecolors=th['face'], linewidths=1.2)
                if pr > 0.5:
                    ax.text(va[i] - off if va[i] <= vb[i] else va[i] + off, i,
                            _nf(va[i], th),
                            ha='right' if va[i] <= vb[i] else 'left',
                            va='center', fontsize=12, color=th['text'], zorder=7)
                    ax.text(vb[i] + off if va[i] <= vb[i] else vb[i] - off, i,
                            _nf(vb[i], th),
                            ha='left' if va[i] <= vb[i] else 'right',
                            va='center', fontsize=12, color=th['text'], zorder=7)
            ax.set_yticks(range(n))
            ax.set_yticklabels(cats)
            ax.invert_yaxis()  # 首条目在顶
            pad = (max(all_vals) - min(all_vals)) * 0.14 or 1.0
            ax.set_xlim(min(all_vals) - pad, max(all_vals) + pad)
            _vfmt(ax, all_vals, th, axis='x')
            _legend_bottom(ax, [
                Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                       markerfacecolor=th['axis'], label=name_a),
                Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                       markerfacecolor=th['palette'][0], label=name_b)], th)
    return draw


def dumbbell(title: str, categories, series, *, slope=False, style='business',
             animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
             figsize=None, dpi=None, numfmt='auto',
             note: str | None = None) -> Path:
    """哑铃图(两期对比):series 恰好 2 个;slope=True 出坡度图。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    if len(ss) != 2:
        raise ValueError(f'哑铃图需要恰好 2 个系列(期初/期末),收到 {len(ss)} 个;'
                         '坡度图同样只用两期数据')
    (name_a, va), (name_b, vb) = ss
    th = _theme(style, numfmt, note)
    return _render('dumbbell', title,
                   _dumbbell_draw(title, cats, name_a, va, name_b, vb, th, slope),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
