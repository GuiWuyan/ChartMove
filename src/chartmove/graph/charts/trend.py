"""趋势与对比类图表:折线(区间带)/ 多系列折线 / 面积(叠加·堆积)/ 组合 / 雷达。"""
from __future__ import annotations

import math
from pathlib import Path

from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from ..render import _ease, _render, _stagger
from ..style import (
    HIGHLIGHT_SIZE,
    _has_spread,
    _legend_bottom,
    _legend_top,
    _marker_step,
    _nf,
    _style,
    _theme,
    _vfmt,
    _xlim,
    _xticks,
    _ylim,
)
from ..validate import (
    _downsample,
    _lttb_indices,
    _validate,
    _validate_band,
    _validate_err,
    _validate_series,
)


def _line_draw(title, cats, vals, th, fill=False, name='数值', band=None,
               err_style='band'):
    """单系列折线绘制闭包(单系列面积图 fill=True 复用):折线逐点延伸、末端
    线性插值,最大/最小点过线即高亮;band 给出时按 err_style 画同步展开的
    半透明区间带(band)或须状误差线(whisker);fill=True 时线下填充;
    x 轴从首帧钉在最终范围。"""
    lo_band, hi_band = band if band is not None else (None, None)

    def draw(ax, p):
        _style(ax, title, th)
        n = len(vals)
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        xr, yr = list(range(k + 1)), list(vals[:k + 1])
        if k + 1 < n:
            xr.append(k + frac)
            yr.append(vals[k] + frac * (vals[k + 1] - vals[k]))
        if band is not None:  # 区间随折线同步渐进展开:带或须同一批插值点
            lr = list(lo_band[:k + 1])
            hr = list(hi_band[:k + 1])
            if k + 1 < n:
                lr.append(lo_band[k] + frac * (lo_band[k + 1] - lo_band[k]))
                hr.append(hi_band[k] + frac * (hi_band[k + 1] - hi_band[k]))
            if err_style == 'whisker':
                ax.errorbar(xr, yr, yerr=[[y - lo for y, lo in zip(yr, lr)],
                                          [hi - y for y, hi in zip(yr, hr)]],
                            fmt='none', ecolor=th['palette'][0], elinewidth=1.6,
                            capsize=5, capthick=1.6, zorder=4)
            else:
                ax.fill_between(xr, lr, hr, color=th['palette'][0],
                                alpha=0.18, linewidth=0)
        if fill:
            ax.fill_between(xr, yr, color=th['palette'][0], alpha=0.30)
        ax.plot(xr, yr, color=th['palette'][0], linewidth=4, marker='o', markersize=16,
                markevery=_marker_step(n))
        if _has_spread(vals):
            for idx, c in ((vals.index(max(vals)), th['hi_max']),
                           (vals.index(min(vals)), th['hi_min'])):
                if pos >= idx:
                    ax.scatter([idx], [vals[idx]], s=HIGHLIGHT_SIZE, color=c,
                               zorder=6, edgecolors=th['face'], linewidths=1.5)
        _ylim(ax, vals if band is None else vals + list(lo_band) + list(hi_band), th)
        _vfmt(ax, vals, th)
        rotated = _xticks(ax, cats, th)
        _xlim(ax, 0, n - 1)  # 折线逐点延伸,x 轴必须从首帧钉在最终范围
        handles = [Line2D([0], [0], color=th['palette'][0], lw=4, marker='o',
                          markersize=12, label=name)]
        if _has_spread(vals):
            handles += [Line2D([0], [0], linestyle='none', marker='o', markersize=13,
                               markerfacecolor=c, label=t)
                        for c, t in ((th['hi_max'], '最好'), (th['hi_min'], '最差'))]
        _legend_bottom(ax, handles, th, rotated)
    return draw


def line(title: str, categories, values, *, name='销售额', style='business',
         animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
         sample: int | None = None, lower=None, upper=None,
         err=None, err_style='band',
         figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """单系列折线:最大/最小高亮;lower/upper 或 err(对称 ±)给区间,呈现方式
    err_style='band' 半透明带(默认)/ 'whisker' 须状误差线;sample=N 做 LTTB 降采样。"""
    cats, vals = _validate(categories, values)
    if err is not None:
        if lower is not None or upper is not None:
            raise ValueError('err(对称误差)与 lower/upper(区间带)只能二选一')
        es = _validate_err(vals, err, what='err')
        lower = [v - e for v, e in zip(vals, es)]
        upper = [v + e for v, e in zip(vals, es)]
    if err_style not in ('band', 'whisker'):
        raise ValueError(f'err_style 仅支持 band / whisker,收到 {err_style!r}')
    band = _validate_band(vals, lower, upper)
    if err_style == 'whisker' and band is None:
        raise ValueError('err_style="whisker" 需要配合 err 或 lower/upper 给出区间数据')
    th = _theme(style, numfmt, note)
    if sample and sample < len(cats) and sample >= 3:  # 带与线用同一批 LTTB 保留点
        idx = _lttb_indices(list(vals), sample)
        cats = [cats[i] for i in idx]
        vals = [vals[i] for i in idx]
        if band is not None:
            band = ([band[0][i] for i in idx], [band[1][i] for i in idx])
    return _render('line', title,
                   _line_draw(title, cats, vals, th, name=name, band=band,
                              err_style=err_style),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _line_multi_draw(title, cats, series, th, value_labels=True, errs=None):
    """多系列折线绘制闭包:各系列同进度逐点延伸(同色系取色板轮换),
    value_labels 且 ≤12 个类目时逐点标数值(用系列色,读图时归属一目了然);
    errs 与 series 平行的对称误差,随折线同步逐点延伸。"""

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
            ax.plot(xr, yr, color=c, linewidth=3, marker='o', markersize=9,
                    markevery=_marker_step(n))
            e = errs[si] if errs else None
            if e is not None:  # 误差须与折线同一批插值点同步延伸
                er = list(e[:k + 1])
                if k + 1 < n:
                    er.append(e[k] + frac * (e[k + 1] - e[k]))
                ax.errorbar(xr, yr, yerr=er, fmt='none', ecolor=c, elinewidth=1.4,
                            capsize=4, capthick=1.4, zorder=4)
            if value_labels and n <= 12:
                for xi in range(k + 1):
                    # 带误差的系列:标注让位到误差须端点之上,不与须线相碰
                    lift = e[xi] if e is not None else 0.0
                    ax.annotate(_nf(vals[xi], th), (xi, vals[xi] + lift),
                                textcoords='offset points',
                                xytext=(0, 9), ha='center', fontsize=10, color=c)
        all_vals = [v for _, vals in series for v in vals]
        if errs:
            all_vals += [v + e for (_, vals), es in zip(series, errs) if es
                         for v, e in zip(vals, es)]
            all_vals += [v - e for (_, vals), es in zip(series, errs) if es
                         for v, e in zip(vals, es)]
        _ylim(ax, all_vals, th)
        _vfmt(ax, all_vals, th)
        _xticks(ax, cats, th)
        _xlim(ax, 0, n - 1)  # 同单系列折线:x 轴从首帧钉在最终范围
        _legend_top(ax, [Line2D([0], [0], color=th['palette'][si % len(th['palette'])],
                                lw=3, marker='o', markersize=9, label=nm)
                         for si, (nm, _) in enumerate(series)], th)
    return draw


def line_multi(title: str, categories, series, *, value_labels=True, style='business',
               animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
               sample: int | None = None, errs=None, figsize=None, dpi=None,
               numfmt='auto', note: str | None = None) -> Path:
    """多系列折线:图例在顶部,可带数值标注;errs=[误差列表, ...] 与 series 平行
    (None 项 = 该系列无误差);sample=N 各系列取保留点并集。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    norm_errs = None
    if errs is not None:
        if len(errs) != len(ss):
            raise ValueError(f'errs 需与 series 个数一致(需 {len(ss)} 个,'
                             f'收到 {len(errs)} 个)')
        norm_errs = [None if e is None else
                     _validate_err(vals, e, what=f'系列「{nm}」的 err')
                     for (nm, vals), e in zip(ss, errs)]
    th = _theme(style, numfmt, note)
    cats, vals_list, ds_errs = _downsample(cats, sample, [vals for _, vals in ss],
                                           extra=norm_errs)
    ss = [(nm, vals) for (nm, _), vals in zip(ss, vals_list)]
    return _render('line_multi', title,
                   _line_multi_draw(title, cats, ss, th, value_labels,
                                    errs=ds_errs or None),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _area_draw(title, cats, series, th, stacked=False, percent=False):
    """多系列面积:默认半透明叠加,stacked=True 逐层堆叠,percent=True 百分比堆积。"""
    n, m = len(cats), len(series)
    if percent:  # 百分比堆积:类目内归一为占比(%),隐含 stacked
        stacked = True
        totals = [sum(vals[i] for _, vals in series) or 1.0 for i in range(n)]
        series = [(nm, [v / t * 100 for v, t in zip(vals, totals)]) for nm, vals in series]
    if stacked:  # 每层下边界 = 前面系列的累计,上边界 = 含本系列的累计
        hi_s, acc = [], [0.0] * n
        for _, vals in series:
            acc = [a + v for a, v in zip(acc, vals)]
            hi_s.append(list(acc))
        lo_s = [[0.0] * n] + hi_s[:-1]
    else:
        lo_s = [[0.0] * n] * m
        hi_s = [vals for _, vals in series]

    def draw(ax, p):
        _style(ax, title, th)
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        for si, (nm, _) in enumerate(series):
            c = th['palette'][si % len(th['palette'])]
            lo, hi = lo_s[si], hi_s[si]
            xr, lr, tr = list(range(k + 1)), list(lo[:k + 1]), list(hi[:k + 1])
            if k + 1 < n:
                xr.append(k + frac)
                lr.append(lo[k] + frac * (lo[k + 1] - lo[k]))
                tr.append(hi[k] + frac * (hi[k + 1] - hi[k]))
            ax.fill_between(xr, lr, tr, color=c,
                            alpha=0.85 if stacked else 0.30, linewidth=0)
            ax.plot(xr, tr, color=c, linewidth=3, marker='o', markersize=9,
                    markevery=_marker_step(n))
        all_vals = [v for _, vals in series for v in vals]
        if percent:
            ax.set_ylim(0, 100)
            _vfmt(ax, [0, 100], dict(th, numfmt='percent'))
        elif stacked:
            _ylim(ax, acc, th)
            _vfmt(ax, acc, th)
        else:  # 叠加层从 0 起画,基线不可被裁掉
            _ylim(ax, all_vals + [0.0], th)
            _vfmt(ax, all_vals, th)
        _xticks(ax, cats, th)
        _xlim(ax, 0, n - 1)  # 面积自左向右显形,x 轴从首帧钉在最终范围
        _legend_top(ax, [Line2D([0], [0], color=th['palette'][si % len(th['palette'])],
                                lw=3, marker='o', markersize=9, label=nm)
                         for si, (nm, _) in enumerate(series)], th)
    return draw


def area(title: str, categories, values=None, *, series=None, stacked=False, percent=False,
         name='数值', style='business', animate=False, fmt=None, loop=False,
         out: str | None = None, out_dir=None, sample: int | None = None,
         figsize=None, dpi=None, numfmt='auto', note: str | None = None) -> Path:
    """面积图:单系列传 values,多系列传 series(默认叠加,stacked/percent 堆积);
    堆积模式各系列 values 需 >=0;sample=N 做 LTTB 降采样。"""
    cats = [str(c) for c in categories]
    if series is None and values is None:
        raise ValueError('area 需要 values(单系列)或 series(多系列)之一')
    if series is not None and values is not None:
        raise ValueError('values 与 series 只能二选一:单系列用 values,多系列用 series')
    th = _theme(style, numfmt, note)
    if series is None:
        if stacked or percent:
            raise ValueError('堆积面积图需要多系列(series);单系列面积图无需 stacked / percent')
        _, vals = _validate(cats, values)
        cats, (vals,), _ = _downsample(cats, sample, [list(vals)])
        return _render('area', title, _line_draw(title, cats, vals, th, fill=True, name=name),
                       animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                       th=th, figsize=figsize, dpi=dpi)
    ss = _validate_series(cats, series)
    if (stacked or percent) and any(min(vals) < 0 for _, vals in ss):
        raise ValueError('堆积面积图各系列 values 需 >=0(面积从 0 起逐层堆)')
    cats, vals_list, _ = _downsample(cats, sample, [vals for _, vals in ss])
    ss = [(nm, vals) for (nm, _), vals in zip(ss, vals_list)]
    return _render('area', title, _area_draw(title, cats, ss, th, stacked, percent),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _combo_draw(title, cats, bar_vals, line_vals, th, bar_name, line_name,
                bar_err=None, line_err=None):
    """双轴组合绘制闭包:柱(左轴)逐根升起,折线(右轴)逐点延伸;bar_err/line_err
    为对称误差,柱误差随柱生长,线误差随折线延伸;
    x 轴按柱宽钉死,防 twinx 共享侧把柱挤出画面。"""
    def draw(ax, p):
        _style(ax, title, th)
        n = len(cats)
        hs = [v * _stagger(p, i, n) for i, v in enumerate(bar_vals)]
        berr = ([[e * _stagger(p, i, n) for i, e in enumerate(bar_err)]]
                if bar_err else None)
        ax.bar(range(n), hs, width=0.5, color=th['palette'][0], yerr=berr,
               error_kw=dict(ecolor=th['text'], elinewidth=1.5, capsize=4,
                             capthick=1.4) if berr else None)
        btop = (max(v + e for v, e in zip(bar_vals, bar_err))
                if bar_err else max(bar_vals))
        ax.set_ylim(0, max(btop * 1.2, 1))
        _vfmt(ax, bar_vals, th)
        rotated = _xticks(ax, cats, th)
        _xlim(ax, -0.25, n - 1 + 0.25)  # 柱宽 0.5 的最终范围,防折线轴共享侧扩张

        ax2 = ax.twinx()
        pos = _ease(p) * (n - 1) if n > 1 else 0.0
        k, frac = int(pos), pos - int(pos)
        xr, yr = list(range(k + 1)), list(line_vals[:k + 1])
        if k + 1 < n:
            xr.append(k + frac)
            yr.append(line_vals[k] + frac * (line_vals[k + 1] - line_vals[k]))
        if line_err is not None:
            er = list(line_err[:k + 1])
            if k + 1 < n:
                er.append(line_err[k] + frac * (line_err[k + 1] - line_err[k]))
            ax2.errorbar(xr, yr, yerr=er, fmt='none', ecolor=th['palette'][1],
                         elinewidth=1.4, capsize=4, capthick=1.4, zorder=4)
        ax2.plot(xr, yr, color=th['palette'][1], linewidth=4, marker='o', markersize=14)
        lvals = list(line_vals)
        if line_err is not None:
            lvals += [v + e for v, e in zip(line_vals, line_err)]
            lvals += [v - e for v, e in zip(line_vals, line_err)]
        _ylim(ax2, lvals, th)
        _vfmt(ax2, line_vals, th)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color(th['axis'])
        ax2.tick_params(labelsize=13, colors=th['text'])
        ax2.set_facecolor('none')

        _legend_bottom(ax, [Patch(facecolor=th['palette'][0], label=bar_name),
                            Line2D([0], [0], color=th['palette'][1], lw=4, marker='o',
                                   markersize=12, label=line_name)], th, rotated)
    return draw


def combo(title: str, categories, bar_values, line_values, *,
          bar_name='柱状', line_name='折线', bar_err=None, line_err=None,
          style='business',
          animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """双轴组合图:柱状(左轴)+ 折线(右轴),柱值需 >=0(折线值可为负);
    bar_err / line_err 为柱与线的对称误差;animate=True 同步生长。"""
    cats, bv = _validate(categories, bar_values)
    _, lv = _validate(categories, line_values)
    if min(bv) < 0:
        raise ValueError('combo 柱值需 >=0(折线值可为负)')
    berr = _validate_err(bv, bar_err, what='bar_err')
    lerr = _validate_err(lv, line_err, what='line_err')
    th = _theme(style, numfmt, note)
    draw = _combo_draw(title, cats, bv, lv, th, bar_name, line_name, berr, lerr)
    return _render('combo', title, draw, animate=animate, fmt=fmt, loop=loop, out=out,
                   out_dir=out_dir, th=th, figsize=figsize, dpi=dpi)


def _radar_draw(title, cats, series, th):
    """雷达绘制闭包:各系列多边形从中心同步展开,径向刻度取最大值四等分
    (337.5° 方位避让顶部标签);首角度重复闭合多边形。"""
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
        ax.set_rgrids(rt, labels=[_nf(r, th) for r in rt], angle=337.5,
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


def radar(title: str, categories, series, *, style='business',
          animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """雷达图:series=[(名称, 数值列表), ...];animate=True 多边形从中心展开。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style, numfmt, note)
    return _render('radar', title, _radar_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   polar=True, th=th, figsize=figsize, dpi=dpi)
