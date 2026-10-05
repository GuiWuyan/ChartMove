"""占比类图表:饼 / 环形 / 玫瑰(极坐标柱状)/ 旭日(两级层级)/ 矩形树图。"""
from __future__ import annotations

import math
from pathlib import Path

from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from ..render import _ease, _render, _stagger
from ..style import _has_spread, _legend_bottom, _nf, _squarify, _style, _theme
from ..validate import _validate, _validate_hierarchy


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
        labels = [(f'{c} {_nf(v, th)}' if show_values else c) if v > 0 else ''
                  for c, v in zip(cats, vals)]
        wedges = dict(edgecolor='white', linewidth=2)
        if donut:
            wedges['width'] = 0.42
        # 数值已由外标签给出,扇区内不再重复标注(<6% 的小扇区也不丢数);
        # 不解包返回值:autopct=None 时 pie 只返回二元,曾把 show_values=False 路径炸穿
        ax.pie(
            vis, labels=labels, labeldistance=1.12,
            colors=[th['palette'][i % len(th['palette'])] for i in range(len(vals))],
            autopct=None, startangle=90, counterclock=False,
            textprops={'fontsize': 13, 'color': th['text']}, wedgeprops=wedges)
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        _legend_bottom(ax, [Line2D([0], [0], linestyle='none', marker='s', markersize=10,
                                   markerfacecolor=th['palette'][i % len(th['palette'])],
                                   label=c) for i, c in enumerate(cats)], th)
    return draw


def pie(title: str, categories, values, *, style='business', animate=False, fmt=None, loop=False,
        out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
        note: str | None = None) -> Path:
    """饼图(values 需 >=0);animate=True 扇区展开。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('饼图 values 需 >=0')
    th = _theme(style, numfmt, note)
    return _render('pie', title, _pie_like_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def donut(title: str, categories, values, *, show_values=True, style='business',
          animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """环形图:外部"类目 数值"标注 + 底部图例;animate=True 扇区展开。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('环形图 values 需 >=0')
    th = _theme(style, numfmt, note)
    return _render('donut', title, _pie_like_draw(title, cats, vals, th, donut=True,
                                                  show_values=show_values),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _rose_draw(title, cats, vals, th):
    """玫瑰图(Nightingale):极坐标柱状,半径即数值;第一扇区朝正上、顺时针。"""
    n = len(vals)
    thetas = [2 * math.pi * i / n for i in range(n)]
    width = 2 * math.pi / n * 0.86  # 扇区间留缝

    def draw(ax, p):
        ax.set_facecolor(th['face'])  # 深色主题下避免露出白色圆形面板
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        hs = [v * _stagger(p, i, n) for i, v in enumerate(vals)]
        cols = [th['palette'][0]] * n
        if _has_spread(vals):
            cols[vals.index(max(vals))] = th['hi_max']
            cols[vals.index(min(vals))] = th['hi_min']
        ax.bar(thetas, hs, width=width, color=cols, edgecolor=th['face'], linewidth=1.5)
        for i, t in enumerate(thetas):
            if vals[i] > 0 and _stagger(p, i, n) > 0.5:
                ax.text(t, hs[i] + max(vals) * 0.05, _nf(vals[i], th),
                        ha='center', va='bottom', fontsize=12, color=th['text'])
        ax.set_xticks(thetas)
        ax.set_xticklabels(cats, fontsize=13, color=th['text'])
        ax.tick_params(axis='x', pad=14)
        ax.set_ylim(0, max(max(vals) * 1.18, 1))
        ax.set_yticks([])  # 数值已逐扇区标注,半径刻度是噪声
        ax.grid(color=th['grid_color'], linestyle=th['grid_ls'], linewidth=th['grid_lw'])
        ax.spines['polar'].set_visible(False)
        ax.set_title(title, fontsize=20, pad=24, color=th['text'])
        # 极坐标圆等比,顶部必须预留标题空间,否则标题被裁
        ax.figure.subplots_adjust(top=0.80)
    return draw


def rose(title: str, categories, values, *, style='business', animate=False, fmt=None,
         loop=False, out: str | None = None, out_dir=None,
         figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """玫瑰图(Nightingale 极坐标柱状,values 需 >=0):半径即数值。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('玫瑰图 values 需 >=0,含正负增减的数据请用 waterfall')
    th = _theme(style, numfmt, note)
    return _render('rose', title, _rose_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   polar=True, th=th, figsize=figsize, dpi=dpi)


def _sunburst_draw(title, hierarchy, th):
    """旭日图:内环 = 父类目(值 = 子类目合计),外环 = 子类目按父色向底色渐变;
    动画与饼图同款:两环随总扫过角同步展开,标签随所在扇区扫过渐次浮现。"""
    total = sum(v for _, kids in hierarchy for _, v in kids) or 1.0
    parent_vals = [sum(v for _, v in kids) for _, kids in hierarchy]
    kids_flat = [(cname, v) for _, kids in hierarchy for cname, v in kids]
    in_colors = [th['palette'][i % len(th['palette'])] for i in range(len(hierarchy))]
    face_rgb = to_rgb(th.get('fig_face') or th['face'])

    def tint(i, j, nk):  # 子扇区色 = 父色向底色渐变(同一父类目内由深到浅)
        t = 0.5 if nk == 1 else 0.15 + 0.45 * j / (nk - 1)
        return tuple(b + (f - b) * t for b, f in zip(to_rgb(in_colors[i]), face_rgb))

    out_colors = [tint(i, j, len(kids))
                  for i, (_, kids) in enumerate(hierarchy)
                  for j in range(len(kids))]
    p_angles, off = [], 0.0  # 父扇区(起始角, 终态扇角),与子扇区共享同一累计
    for pv in parent_vals:
        a = 360 * pv / total
        p_angles.append((off, a))
        off += a

    def visible(vals, sweep):  # 与饼图一致:扇角按终态比例裁剪到当前扫过角
        vis, off = [], 0.0
        for v in vals:
            a = 360 * v / total
            vis.append(min(max(sweep - off, 0.0), a))
            off += a
        if sum(vis) <= 0:
            vis[0] = 1e-6
        return vis

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        sweep = 360 * _ease(p)
        edge = dict(edgecolor=th['face'], linewidth=2)
        pv = visible(parent_vals, sweep)
        ax.pie(pv, radius=0.72, colors=in_colors, startangle=90, counterclock=False,
               wedgeprops={**edge, 'width': 0.44})
        ax.pie(visible([v for _, v in kids_flat], sweep), radius=1.0, colors=out_colors,
               startangle=90, counterclock=False, wedgeprops={**edge, 'width': 0.26})
        # 内环父类目:扇区够宽(>14°)且已扫过一半才标名,文字色按底色亮度自适应
        for i, ((name, _), (a0, a)) in enumerate(zip(hierarchy, p_angles)):
            if a < 14 or pv[i] <= a * 0.5:
                continue
            theta = math.radians(90 - (a0 + a / 2))
            r, g, b = to_rgb(in_colors[i])
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            ax.text(0.50 * math.cos(theta), 0.50 * math.sin(theta), name,
                    ha='center', va='center', fontsize=13,
                    color='#111111' if lum > 0.6 else '#ffffff')
        # 外环子类目:名字+数值置于中角外侧,随扇区扫过渐次出现
        off = 0.0
        for (cname, v), c in zip(kids_flat, out_colors):
            a = 360 * v / total
            if v > 0 and sweep - off > a * 0.5:
                theta = math.radians(90 - (off + a / 2))
                x, y = 1.10 * math.cos(theta), 1.10 * math.sin(theta)
                ax.text(x, y, f'{cname} {_nf(v, th)}',
                        ha='center' if abs(x) < 0.4 else ('left' if x > 0 else 'right'),
                        va='center', fontsize=12, color=th['text'])
            off += a
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        _legend_bottom(ax, [Patch(facecolor=in_colors[i], label=name)
                            for i, (name, _) in enumerate(hierarchy)], th)
    return draw


def sunburst(title: str, hierarchy, *, style='business', animate=False, fmt=None, loop=False,
             out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
             note: str | None = None) -> Path:
    """旭日图(两级层级占比):hierarchy = {父类目: {子类目: 数值}},内环父类目
    (值 = 子值合计)、外环子类目;数值需 >=0 且有正值。"""
    hh = _validate_hierarchy(hierarchy)
    th = _theme(style, numfmt, note)
    return _render('sunburst', title, _sunburst_draw(title, hh, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _treemap_draw(title, cats, vals, th):
    pairs = sorted([(c, v) for c, v in zip(cats, vals) if v > 0],
                   key=lambda cv: cv[1], reverse=True)  # 降序才出好比例
    total = sum(v for _, v in pairs) or 1.0
    # 面积单位须与画布一致(w*h),否则布局塌缩成细条
    rects = _squarify([v / total * 16.0 * 9.0 for _, v in pairs], 0.0, 0.0, 16.0, 9.0)

    def draw(ax, p):
        _style(ax, title, th)
        ax.set_axis_off()  # 树图无坐标轴,仅保留标题
        for i, ((cat, v), (rx, ry, rw, rh)) in enumerate(zip(pairs, rects)):
            pr = _stagger(p, i, len(pairs))
            if pr <= 0:
                continue
            cx, cy = rx + rw / 2, ry + rh / 2  # 逐格从自身中心浮现
            color = th['palette'][i % len(th['palette'])]
            ax.add_patch(Rectangle((cx - rw / 2 * pr, cy - rh / 2 * pr),
                                   rw * pr, rh * pr, facecolor=color,
                                   edgecolor=th['face'], linewidth=2))
            if pr > 0.5 and rw > 1.2 and rh > 0.62:  # 格子够大才标文字
                r, g, b = to_rgb(color)
                tc = '#111111' if 0.299 * r + 0.587 * g + 0.114 * b > 0.6 else '#ffffff'
                ax.text(cx, cy, f'{cat}\n{_nf(v, th)}', ha='center', va='center',
                        fontsize=14, color=tc)
        ax.set_xlim(0, 16.0)
        ax.set_ylim(0, 9.0)
    return draw


def treemap(title: str, categories, values, *, style='business', animate=False, fmt=None,
            loop=False, out: str | None = None, out_dir=None,
            figsize=None, dpi=None, numfmt='auto',
            note: str | None = None) -> Path:
    """矩形树图:面积即占比,values 需 >=0 且有正值;按值降序 squarify 布局。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('矩形树图 values 需 >=0,含正负增减的数据请用 waterfall')
    if max(vals) <= 0:
        raise ValueError('矩形树图 values 需有正值(面积即占比)')
    th = _theme(style, numfmt, note)
    return _render('treemap', title, _treemap_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
