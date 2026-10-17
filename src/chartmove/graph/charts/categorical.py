"""柱类图表:柱状(横向)/ 多系列(分组·堆积·百分比堆积)/ 帕累托 / 瀑布。"""
from __future__ import annotations

from pathlib import Path

from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.patheffects import Normal

from ..render import _ease, _render, _stagger
from ..style import (
    _has_spread,
    _legend_bottom,
    _legend_top,
    _nf,
    _style,
    _theme,
    _vfmt,
    _xlim,
    _xticks,
)
from ..validate import _validate, _validate_err, _validate_series


def _bar_draw(title, cats, vals, th, horizontal=False, err=None):
    """柱状 / 横向条形共用绘制闭包:柱体逐根错峰生长,过半后浮现数值标签;
    有差距时最大/最小值分别换 hi_max / hi_min 高亮;err 对称误差随柱生长
    (纵向柱顶 yerr / 横向条末端 xerr),数值标签让位到误差须端点之外。"""
    def draw(ax, p):
        _style(ax, title, th, grid_axis='x' if horizontal else None)
        hs = [v * _stagger(p, i, len(vals)) for i, v in enumerate(vals)]
        ebar = ([[e * _stagger(p, i, len(vals)) for i, e in enumerate(err)]]
                if err else None)
        ecolor = dict(ecolor=th['text'], elinewidth=1.5, capsize=4,
                      capthick=1.4) if ebar else None
        cols = [th['palette'][0]] * len(vals)
        if _has_spread(vals):
            cols[vals.index(max(vals))] = th['hi_max']
            cols[vals.index(min(vals))] = th['hi_min']
        if horizontal:  # 首条目在顶部,适配排名场景
            bars = ax.barh(range(len(vals)), hs, height=0.6, color=cols,
                           xerr=ebar, error_kw=ecolor)
            top = (max(v + e for v, e in zip(vals, err)) if err else max(vals))
            pad = top * 0.012  # 标签起点留出空隙,不压误差线端帽
            for i, b in enumerate(bars):
                if _stagger(p, i, len(vals)) > 0.5:
                    tip = hs[i] + (err[i] * _stagger(p, i, len(vals)) if err else 0)
                    ax.text(tip + pad, b.get_y() + b.get_height() / 2, _nf(vals[i], th),
                            va='center', ha='left', fontsize=14, color=th['text'])
            ax.set_xlim(0, max(top * 1.15, 1))
            ax.set_yticks(range(len(vals)))
            ax.set_yticklabels(cats)
            ax.invert_yaxis()
            _vfmt(ax, vals, th, axis='x')
        else:
            bars = ax.bar(range(len(vals)), hs, width=0.6, color=cols,
                          yerr=ebar, error_kw=ecolor)
            for i, b in enumerate(bars):
                if _stagger(p, i, len(vals)) > 0.5:
                    tip = hs[i] + (err[i] * _stagger(p, i, len(vals)) if err else 0)
                    ax.text(b.get_x() + b.get_width() / 2, tip, _nf(vals[i], th),
                            ha='center', va='bottom', fontsize=14, color=th['text'])
            top = (max(v + e for v, e in zip(vals, err)) if err else max(vals))
            ax.set_ylim(0, max(top * 1.15, 1))
            _vfmt(ax, vals, th)
            _xticks(ax, cats, th)
    return draw


def bar(title: str, categories, values, *, style='business', animate=False, fmt=None,
        loop=False, out: str | None = None, out_dir=None, horizontal=False,
        err=None, figsize=None, dpi=None, numfmt='auto',
        note: str | None = None) -> Path:
    """柱状图(values 需 >=0):最大/最小高亮;horizontal=True 横向条形(误差自动切
    x 向);err 对称误差(SD/SEM);animate=True 逐根升起。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('柱状图 values 需 >=0,含正负增减的数据请用 waterfall')
    es = _validate_err(vals, err, what='err')
    th = _theme(style, numfmt, note)
    return _render('bar', title, _bar_draw(title, cats, vals, th, horizontal, es),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _bar_multi_draw(title, cats, series, th, stacked=False, percent=False, errs=None):
    """多系列柱绘制闭包:默认分组并列,stacked=True 逐层堆叠;percent=True 先在
    类目内归一为占比(隐含 stacked),段内标注文字色按底色亮度自适应;
    errs 与 series 平行的对称误差(仅分组模式),随各系列柱生长。"""
    m, ng = len(series), len(cats)
    if percent:  # 百分比堆积:类目内归一为占比(%),隐含 stacked
        stacked = True
        totals = [sum(vals[i] for _, vals in series) or 1.0 for i in range(ng)]
        series = [(nm, [v / t * 100 for v, t in zip(vals, totals)]) for nm, vals in series]
    if stacked:  # 每系列柱底 = 前面系列的终值累计,逐层向上堆
        bases, acc = [], [0.0] * ng
        for _, vals in series:
            bases.append(list(acc))
            acc = [a + v for a, v in zip(acc, vals)]

    def draw(ax, p):
        _style(ax, title, th)
        w = 0.8 if stacked else 0.8 / m
        for si, (nm, vals) in enumerate(series):
            prog = _stagger(p, si, m)
            color = th['palette'][si % len(th['palette'])]
            e = errs[si] if errs else None
            ebar = ([[ev * prog for ev in e]] if e else None)
            ecolor = (dict(ecolor=th['text'], elinewidth=1.3, capsize=3, capthick=1.2)
                      if ebar else None)
            if stacked:
                ax.bar(range(ng), [v * prog for v in vals], bottom=bases[si],
                       width=w * 0.92, color=color, label=nm)
                if percent:  # 经典样式:占比直接标在段内,随段生长浮现;过小段(<4%)不标
                    r, g, b = to_rgb(color)
                    tc = '#111111' if 0.299 * r + 0.587 * g + 0.114 * b > 0.6 else '#ffffff'
                    for ci, v in enumerate(vals):
                        if v >= 4 and prog > 0.5:
                            # 覆盖 sketch 的 rc 白描边,否则色块内白字糊死
                            ax.text(ci, bases[si][ci] + v * prog / 2, f'{v:.0f}%',
                                    ha='center', va='center', fontsize=13, color=tc,
                                    path_effects=[Normal()])
            else:
                ax.bar([i + (si - m / 2 + 0.5) * w for i in range(ng)],
                       [v * prog for v in vals], width=w * 0.92, color=color,
                       label=nm, yerr=ebar, error_kw=ecolor)
        if percent:
            ax.set_ylim(0, 100)
            _vfmt(ax, [0, 100], dict(th, numfmt='percent'))  # 刻度追加 %
        else:
            tops = [max(v + e for v, e in zip(vals, es)) if es else max(vals)
                    for (nm, vals), es in zip(series, errs or [None] * m)]
            ceiling = max(acc) if stacked else max(tops)
            ax.set_ylim(0, max(ceiling * 1.15, 1))
            _vfmt(ax, [v for _, vals in series for v in vals], th)
        _xticks(ax, cats, th)
        _legend_top(ax, [Patch(facecolor=th['palette'][si % len(th['palette'])],
                               label=nm) for si, (nm, _) in enumerate(series)], th)
    return draw


def bar_multi(title: str, categories, series, *, stacked=False, percent=False,
              errs=None, style='business', animate=False, fmt=None, loop=False,
              out: str | None = None, out_dir=None, figsize=None, dpi=None,
              numfmt='auto', note: str | None = None) -> Path:
    """多系列柱状图:默认分组并列,stacked=True 堆积、percent=True 百分比堆积
    (隐含 stacked);errs=[误差列表, ...] 与 series 平行(None 项 = 无误差),
    仅分组模式支持(堆积段无从锚定误差)。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    if any(min(vals) < 0 for _, vals in ss):
        raise ValueError('多系列柱状图各系列 values 需 >=0')
    norm_errs = None
    if errs is not None:
        if stacked or percent:
            raise ValueError('堆积 / 百分比堆积柱状图不支持误差线(堆积段无从锚定误差),'
                             '请用分组模式(不传 stacked / percent)')
        if len(errs) != len(ss):
            raise ValueError(f'errs 需与 series 个数一致(需 {len(ss)} 个,'
                             f'收到 {len(errs)} 个)')
        norm_errs = [None if e is None else
                     _validate_err(vals, e, what=f'系列「{nm}」的 err')
                     for (nm, vals), e in zip(ss, errs)]
    th = _theme(style, numfmt, note)
    return _render('bar_multi', title,
                   _bar_multi_draw(title, cats, ss, th, stacked, percent, norm_errs),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _pareto_draw(title, cats, vals, th):
    """帕累托图:柱按值降序(此处统一排序,任何调用路径都有序),右轴累计占比折线 + 80% 参考线。"""
    order = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)  # 稳定降序
    cats = [cats[i] for i in order]
    vals = [vals[i] for i in order]
    total = sum(vals) or 1.0
    cum, acc = [], 0.0
    for v in vals:
        acc += v
        cum.append(acc / total * 100)
    n = len(vals)

    def draw(ax, p):
        _style(ax, title, th)
        hs = [v * _stagger(p, i, n) for i, v in enumerate(vals)]
        ax.bar(range(n), hs, width=0.6, color=th['palette'][0])
        for i, b in enumerate(ax.patches):
            if _stagger(p, i, n) > 0.5:
                ax.text(b.get_x() + b.get_width() / 2, hs[i], _nf(vals[i], th),
                        ha='center', va='bottom', fontsize=14, color=th['text'])
        ax.set_ylim(0, max(max(vals) * 1.2, 1))
        _vfmt(ax, vals, th)
        rotated = _xticks(ax, cats, th)
        _xlim(ax, -0.3, n - 1 + 0.3)  # 柱宽 0.6 的最终范围,防累计线轴共享侧扩张

        ax2 = ax.twinx()
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        xr, yr = list(range(k + 1)), list(cum[:k + 1])
        if k + 1 < n:
            xr.append(k + frac)
            yr.append(cum[k] + frac * (cum[k + 1] - cum[k]))
        ax2.plot(xr, yr, color=th['palette'][1], linewidth=4, marker='o', markersize=14)
        ax2.axhline(80, color=th['axis'], linewidth=1.2, linestyle='--', alpha=0.7)
        ax2.set_ylim(0, 100)
        _vfmt(ax2, [0, 100], dict(th, numfmt='percent'))
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color(th['axis'])
        ax2.tick_params(labelsize=13, colors=th['text'])
        ax2.set_facecolor('none')

        _legend_bottom(ax, [Patch(facecolor=th['palette'][0], label='数值'),
                            Line2D([0], [0], color=th['palette'][1], lw=4, marker='o',
                                   markersize=12, label='累计占比')], th, rotated)
    return draw


def pareto(title: str, categories, values, *, style='business', animate=False, fmt=None,
           loop=False, out: str | None = None, out_dir=None, figsize=None, dpi=None,
           numfmt='auto', note: str | None = None) -> Path:
    """帕累托图(二八分析):柱按值自动降序,右轴累计占比线 + 80% 参考线;values 需 >=0 且有正值。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('帕累托图 values 需 >=0')
    if max(vals) <= 0:
        raise ValueError('帕累托图 values 需有正值(累计占比无意义)')
    th = _theme(style, numfmt, note)
    return _render('pareto', title, _pareto_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _waterfall_draw(title, cats, vals, th, total=True):
    """瀑布绘制闭包:正柱从上一累计水平向上生长,负柱顶端挂累计水平向下生长;
    total=True 末尾补"合计"柱(从 0 画到代数和),相邻柱间画桥线;
    y 轴按含合计的全部累计水平固定,合计柱长出时轴不动。"""
    bars, acc = [], 0.0  # (label, value 或 None=合计, 起点)
    for c, v in zip(cats, vals):
        bars.append((c, v, acc))
        acc += v
    if total:
        bars.append(('合计', None, acc))

    def draw(ax, p):
        _style(ax, title, th)
        ends = []
        for i, (c, v, base) in enumerate(bars):
            pr = _stagger(p, i, len(bars))
            ends.append(base + (v or 0.0))
            if v is None:  # 合计柱:从 0 画到代数和,负合计从 0 向下生长
                col = th['hi_min']
                bottom = base * pr if base < 0 else 0.0
                h, text = abs(base) * pr, _nf(base, th)
            elif v >= 0:
                col, bottom, h, text = th['palette'][0], base, v * pr, _nf(v, th)
            else:  # 负值柱:顶端挂在上一累计水平,向下生长
                col, bottom, h, text = th['hi_max'], base + v * pr, abs(v) * pr, _nf(v, th)
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
        _vfmt(ax, levels, th)
        _xlim(ax, -0.3, len(bars) - 1 + 0.3)  # 柱宽 0.6 的最终范围,合计柱长出时轴不动
        _xticks(ax, [b[0] for b in bars], th)
    return draw


def waterfall(title: str, categories, values, *, total=True, style='business',
              animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
              figsize=None, dpi=None, numfmt='auto',
              note: str | None = None) -> Path:
    """瀑布图:values 为逐项增减(正=升/负=降),total=True 自动补"合计"柱。"""
    cats, vals = _validate(categories, values)
    th = _theme(style, numfmt, note)
    return _render('waterfall', title,
                   _waterfall_draw(title, cats, vals, th, total),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
