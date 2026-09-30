"""图表内核:matplotlib 封装,同一份绘图代码输出 PNG / PDF / TIF / GIF / MP4。

13 主题 × 4 风格包(学术 / 商务 / 简约演示 / 其他),定义与元数据见 themes.py;
扩展新主题只需在 THEMES 加一组参数,绘图代码零改动。

    from vizkit import bar, line, pie, donut, area, combo, line_multi, bar_multi, radar
    bar('季度产量', ['Q1', 'Q2', 'Q3'], [120, 200, 90], style='mckinsey', animate=True)
    # -> .../VizKit/bar_季度产量.gif

约定:animate=True 出 GIF(默认)/ MP4,静态图 fmt='png'(默认)/'pdf'/'tif';
GIF 默认播一遍停在末帧,loop=True 无限循环(MP4 是否循环由播放器决定);
大数据:类目 >25 自动抽稀刻度、折线标记超 50 个隔点绘制,line/area/line-multi
支持 sample=N 做 LTTB 保形降采样(数千行 CSV 出图用);
产物默认写 ./Results/(持久,不做 TTL 清理;同名文件自动加序号不覆盖);
数值标签/刻度 numfmt='auto' 默认中文单位(≥1e4 万、≥1e8 亿;percent 追加 %;
plain 原样);note 参数在底部左侧出脚注(数据来源 / 备注);
不播放动画的场景(如 Word)一律 PNG。
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
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter

from .fonts import setup_fonts, sketch_font_chain
from .output import claim_path, resolve_out_dir, safe_stem
from .themes import THEME_LABELS, THEMES

setup_fonts()

FIGSIZE = (12.8, 7.2)   # 16:9;12.8 * DPI_PNG = 1920px
DPI_PNG = 150
DPI_GIF = 75            # 960px,控制 GIF 体积
DPI_MP4 = 150
DPI_TIF = 600           # 期刊投稿级
GIF_FPS, MP4_FPS, FRAMES = 20, 24, 48
HIGHLIGHT_SIZE = 650    # 最大/最小值高亮点大小(pt^2)
THIN_TICKS_ABOVE = 25   # 类目超过此数,刻度自动抽稀(再多标签必然互相压盖)
THIN_TICKS_KEEP = 10    # 抽稀后保留的刻度数(含首尾)
MARKER_CAP = 50         # 折线标记数上限:超过则隔点绘制(markevery)

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


def _ease(t: float) -> float:
    """ease-out 缓动:起步快、收尾慢。"""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def _stagger(p: float, i: int, n: int) -> float:
    """第 i 个元素的局部进度:错峰出现(重叠 60%),实现"逐根升起"。
    时间轴按最后元素的完成点归一,整个动画恰在 p=1 收尾,不留静止尾巴。"""
    if n <= 1:
        return _ease(p)
    span = 0.6
    last = span + (1 - span) * (n - 1) / n  # 未归一时最后元素的完成点(<1)
    start = (1 - span) * i / n
    return _ease((last * p - start) / span)


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
    """设置类目刻度;标签多且长时旋转 30° 并加大下边距,返回是否发生了旋转。
    类目超过 THIN_TICKS_ABOVE 时均匀抽稀到 ~THIN_TICKS_KEEP 个刻度(含首尾),
    避免大数据下标签叠成黑带。"""
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
    """数值标签/刻度格式化(th['numfmt']):percent 追加 %(数值本身即百分数);
    auto 中文单位(≥1e4 万、≥1e8 亿);plain / 未识别值原样 :g。"""
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
    """数值轴刻度跟随 numfmt(percent 恒加 %;auto 在数据达万级时切万/亿刻度);
    axis 指定数值轴(默认 y;横向条形 / 直方图的数值轴为 x)。"""
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


def _lttb_indices(ys, target: int) -> list[int]:
    """LTTB(Largest-Triangle-Three-Buckets)降采样:保留首尾,其余各桶取与前后
    参照点构成三角形面积最大的点,保形地抽到 ~target 个点(尖峰不丢)。"""
    n = len(ys)
    if target >= n or target < 3:
        return list(range(n))
    ys_ = np.asarray(ys, dtype=float)
    keep, a = [0], 0
    step = (n - 2) / (target - 2)
    for i in range(1, target - 1):
        s, e = int((i - 1) * step) + 1, int(i * step) + 1      # 当前候选桶 [s, e)
        ns, ne = e, int((i + 1) * step) + 1                    # 下一桶(取均值作参照)
        avg_x, avg_y = (ns + ne - 1) / 2, float(ys_[ns:ne].mean())
        xs = np.arange(s, e)
        area = np.abs((avg_x - a) * (ys_[s:e] - ys_[a]) - (xs - a) * (avg_y - ys_[a]))
        a = s + int(np.argmax(area))
        keep.append(a)
    keep.append(n - 1)
    return keep


def _downsample(cats: list[str], sample: int | None,
                series: list[list[float]]) -> tuple[list[str], list[list[float]]]:
    """折线类大数据降采样:LTTB 保形抽稀;多系列取各系列保留索引的并集并同步截取,
    保证类目与各系列长度一致。sample 缺省 / 不小于点数 / 小于 3 时原样返回。"""
    n = len(cats)
    if not sample or sample >= n or sample < 3:
        return cats, series
    idx = sorted(set().union(*(_lttb_indices(v, sample) for v in series)))
    return [cats[i] for i in idx], [[v[i] for i in idx] for v in series]


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
                    ax.text(hs[i], b.get_y() + b.get_height() / 2, _nf(vals[i], th),
                            va='center', ha='left', fontsize=14, color=th['text'])
            ax.set_xlim(0, max(max(vals) * 1.15, 1))
            ax.set_yticks(range(len(vals)))
            ax.set_yticklabels(cats)
            ax.invert_yaxis()
            _vfmt(ax, vals, th, axis='x')
        else:
            bars = ax.bar(range(len(vals)), hs, width=0.6, color=cols)
            for i, b in enumerate(bars):
                if _stagger(p, i, len(vals)) > 0.5:
                    ax.text(b.get_x() + b.get_width() / 2, hs[i], _nf(vals[i], th),
                            ha='center', va='bottom', fontsize=14, color=th['text'])
            ax.set_ylim(0, max(max(vals) * 1.15, 1))
            _vfmt(ax, vals, th)
            _xticks(ax, cats, th)
    return draw


def _line_draw(title, cats, vals, th, fill=False, name='数值', band=None):
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
        if band is not None:  # 区间带跟随折线同步渐进展开
            lr = list(lo_band[:k + 1])
            hr = list(hi_band[:k + 1])
            if k + 1 < n:
                lr.append(lo_band[k] + frac * (lo_band[k + 1] - lo_band[k]))
                hr.append(hi_band[k] + frac * (hi_band[k + 1] - hi_band[k]))
            ax.fill_between(xr, lr, hr, color=th['palette'][0], alpha=0.18, linewidth=0)
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
            ax.plot(xr, yr, color=c, linewidth=3, marker='o', markersize=9,
                    markevery=_marker_step(n))
            if value_labels and n <= 12:
                for xi in range(k + 1):
                    ax.annotate(_nf(vals[xi], th), (xi, vals[xi]), textcoords='offset points',
                                xytext=(0, 9), ha='center', fontsize=10, color=c)
        all_vals = [v for _, vals in series for v in vals]
        _ylim(ax, all_vals, th)
        _vfmt(ax, all_vals, th)
        _xticks(ax, cats, th)
        _xlim(ax, 0, n - 1)  # 同单系列折线:x 轴从首帧钉在最终范围
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
        labels = [(f'{c} {_nf(v, th)}' if show_values else c) if v > 0 else ''
                  for c, v in zip(cats, vals)]
        wedges = dict(edgecolor='white', linewidth=2)
        if donut:
            wedges['width'] = 0.42
        _, texts, autotexts = ax.pie(
            vis, labels=labels, labeldistance=1.12,
            colors=[th['palette'][i % len(th['palette'])] for i in range(len(vals))],
            autopct=(lambda pct: _nf(round(pct / 100 * total), th) if pct > 6 else '')
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


def _combo_draw(title, cats, bar_vals, line_vals, th, bar_name, line_name):
    def draw(ax, p):
        _style(ax, title, th)
        n = len(cats)
        hs = [v * _stagger(p, i, n) for i, v in enumerate(bar_vals)]
        ax.bar(range(n), hs, width=0.5, color=th['palette'][0])
        ax.set_ylim(0, max(max(bar_vals) * 1.2, 1))
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
        ax2.plot(xr, yr, color=th['palette'][1], linewidth=4, marker='o', markersize=14)
        _ylim(ax2, line_vals, th)
        _vfmt(ax2, line_vals, th)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color(th['axis'])
        ax2.tick_params(labelsize=13, colors=th['text'])
        ax2.set_facecolor('none')

        _legend_bottom(ax, [Patch(facecolor=th['palette'][0], label=bar_name),
                            Line2D([0], [0], color=th['palette'][1], lw=4, marker='o',
                                   markersize=12, label=line_name)], th, rotated)
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
        _vfmt(ax, [v for _, vals in series for v in vals], th)
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


def _heatmap_draw(title, rows, cols, arr, th, annotate=True):
    cmap = LinearSegmentedColormap.from_list(
        'vizkit_seq', [th['face'], th['palette'][0], th['hi_max']])
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
                            alpha=a)
        for idx in (imax, imin):  # 最大/最小格描边:随所在格一起淡入,不再末帧突现
            a = float(alpha[idx[0], idx[1]])
            if a > 0:
                ax.add_patch(Rectangle((idx[1] - 0.5, idx[0] - 0.5), 1, 1, fill=False,
                                       edgecolor=th['text'], linewidth=2.5, alpha=a))
    return draw


def _waterfall_draw(title, cats, vals, th, total=True):
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


def _squarify(sizes, x, y, w, h):
    """Squarified treemap 布局(Bruls et al. 2000):sizes 需降序且面积和 = w*h,
    返回 [(x, y, w, h)];逐行贪心摆放,保持每格长宽比尽量接近 1。"""
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


# ---------- 渲染 ----------

class _GifWriter(animation.PillowWriter):
    """GIF 写入器:默认不写 NETSCAPE 循环扩展(播一遍停在末帧,PPT 里不重播);
    loop=True 写入无限循环扩展。

    Pillow 保存时静默丢弃与前一帧相同的帧并把其时长累加到保留帧(总播放时长
    不变),分步生长的图表(如热力图)帧数少但节奏正确,此处无需重复处理。
    """

    def __init__(self, fps: float = 5, loop: bool = False, **kwargs):
        super().__init__(fps=fps, **kwargs)
        self._loop = loop

    def finish(self):
        self._frames[0].save(
            self.outfile, save_all=True, append_images=self._frames[1:],
            duration=int(1000 / self.fps), **({'loop': 0} if self._loop else {}))


def _render(kind, title, draw, *, animate, fmt, out, out_dir=None, loop=False,
            polar: bool = False, figsize=None, dpi=None,
            th: dict | None = None) -> Path:
    th = th or {}
    face = th.get('face', 'white')
    fig_face = th.get('fig_face') or face
    rc_extra = _sketch_rc_extra(th, fig_face)  # 手绘风:路径抖动 + 西文手写体

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
                if loop:
                    raise ValueError('loop 仅对 GIF 生效(MP4 是否循环由播放器决定);'
                                     '请改用 fmt="gif" 或去掉 loop')
                if not shutil.which('ffmpeg'):
                    raise RuntimeError('未找到 ffmpeg(MP4 需要)。'
                                       '安装:winget install Gyan.FFmpeg,或改用 fmt="gif"')
                writer = animation.FFMpegWriter(fps=MP4_FPS, codec='h264',
                                                extra_args=['-pix_fmt', 'yuv420p'])
                path, fps, dpi_eff = out_path / f'{stem}.mp4', MP4_FPS, (dpi or DPI_MP4)
            else:
                writer = _GifWriter(fps=GIF_FPS, loop=loop)
                path, fps, dpi_eff = out_path / f'{stem}.gif', GIF_FPS, (dpi or DPI_GIF)

            path = claim_path(path)  # 原子占位:并发下也保证"同名不覆盖"
            try:
                fig = plt.figure(figsize=fig_size, facecolor=fig_face)

                def update(i):
                    fig.clear()  # 连同 twinx 一起清空,避免帧间残留
                    draw(fig.add_subplot(111, polar=polar), i / (FRAMES - 1))
                    _note(fig, th)

                ani = animation.FuncAnimation(fig, update, frames=FRAMES,
                                              interval=1000 / fps)
                ani.save(path, writer=writer, dpi=dpi_eff,
                         savefig_kwargs={'facecolor': fig_face})
            except BaseException:
                path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
                raise
            finally:
                plt.close('all')
        else:
            if fmt not in STATIC_FMTS:
                raise ValueError(f'静态图支持 {" / ".join(STATIC_FMTS)},收到 fmt={fmt!r};'
                                 '动画请传 animate=True(仅 gif / mp4)')
            if loop:
                raise ValueError('loop 仅对动画生效,需 animate=True(仅 gif)')
            path = claim_path(out_path / f'{stem}.{fmt}')  # 原子占位:并发下不覆盖
            dpi_eff = dpi or (DPI_TIF if fmt == 'tif' else DPI_PNG)
            try:
                fig = plt.figure(figsize=fig_size, facecolor=fig_face)
                draw(fig.add_subplot(111, polar=polar), 1.0)
                _note(fig, th)
                fig.savefig(path, dpi=dpi_eff, facecolor=fig_face)
            except BaseException:
                path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
                raise
            finally:
                plt.close(fig)

        print(f'图表已生成: {path}')
        return path


def _check_finite(vals, what: str = 'values') -> None:
    """拒绝 nan / inf:静默渲染会产出 'nan' / 'inf亿' 标签,必须报中文错误。"""
    if any(not math.isfinite(v) for v in vals):
        raise ValueError(f'{what} 含 nan / inf 等非法数值,请检查数据')


def _validate(categories, values) -> tuple[list, list]:
    cats = [str(c) for c in categories]
    vals = [float(v) for v in values]
    if not cats or len(cats) != len(vals):
        raise ValueError('categories 与 values 必须非空且长度一致')
    _check_finite(vals)
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


def _validate_band(vals, lower, upper) -> tuple[list[float], list[float]] | None:
    """区间带校验:lower/upper 须同时给出、与 values 等长且 upper >= lower;未给返回 None。"""
    if lower is None and upper is None:
        return None
    if lower is None or upper is None:
        raise ValueError('区间带需要同时给出 lower 与 upper')
    lo = [float(v) for v in lower]
    hi = [float(v) for v in upper]
    _check_finite(lo, 'lower')
    _check_finite(hi, 'upper')
    if not (len(lo) == len(hi) == len(vals)):
        raise ValueError(f'区间带 lower/upper 需与 values 等长(需 {len(vals)} 个,'
                         f'收到 lower {len(lo)} / upper {len(hi)} 个)')
    bad = next((i for i, (a, b) in enumerate(zip(lo, hi)) if b < a), None)
    if bad is not None:
        raise ValueError(f'区间带 upper 需 >= lower(第 {bad + 1} 个点相反)')
    return lo, hi


def _validate_xy(xs, ys) -> tuple[list[float], list[float]]:
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    if not x or len(x) != len(y):
        raise ValueError('x 与 y 必须非空且长度一致')
    _check_finite(x, 'x')
    _check_finite(y, 'y')
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
        _check_finite(vals, f'系列「{nm}」')
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
    if not np.isfinite(arr).all():
        raise ValueError('values 含 nan / inf 等非法数值,请检查数据')
    return r, c, arr


def _theme(style: str | None, numfmt: str = 'auto', note: str | None = None) -> dict:
    """主题 + 全局展示选项:numfmt 数值格式(auto / plain / percent),note 底部脚注。"""
    if numfmt not in ('auto', 'plain', 'percent'):
        raise ValueError(f'numfmt 仅支持 auto / plain / percent,收到 {numfmt!r}')
    if style and style not in THEMES:  # None / '' 仍回退 business(保持既有调用方兼容)
        raise ValueError(f'未知主题 {style!r};可选:{", ".join(THEMES)}')
    th = THEMES.get(style or 'business', THEMES['business'])
    return dict(th, palette=list(th['palette']), numfmt=numfmt, note=note)


# ---------- 公开 API ----------

def bar(title: str, categories, values, *, style='business', animate=False, fmt=None, loop=False,
        out: str | None = None, out_dir=None, horizontal=False,
        figsize=None, dpi=None, numfmt='auto',
        note: str | None = None) -> Path:
    """柱状图(values 需 >=0):最大/最小高亮;horizontal=True 横向条形,animate=True 逐根升起。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('柱状图 values 需 >=0,含正负增减的数据请用 waterfall')
    th = _theme(style, numfmt, note)
    return _render('bar', title, _bar_draw(title, cats, vals, th, horizontal),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def rose(title: str, categories, values, *, style='business', animate=False, fmt=None,
         loop=False, out: str | None = None, out_dir=None,
         figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """玫瑰图(Nightingale 极坐标柱状,values 需 >=0):半径即数值,构成/排名的圆形展示;
    animate=True 逐扇区生长。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('玫瑰图 values 需 >=0,含正负增减的数据请用 waterfall')
    th = _theme(style, numfmt, note)
    return _render('rose', title, _rose_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   polar=True, th=th, figsize=figsize, dpi=dpi)


def treemap(title: str, categories, values, *, style='business', animate=False, fmt=None,
            loop=False, out: str | None = None, out_dir=None,
            figsize=None, dpi=None, numfmt='auto',
            note: str | None = None) -> Path:
    """矩形树图(构成分析,values 需 >=0 且有正值):面积即占比,
    内部按值降序 squarify 布局;animate=True 逐格从中心浮现。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('矩形树图 values 需 >=0,含正负增减的数据请用 waterfall')
    if max(vals) <= 0:
        raise ValueError('矩形树图 values 需有正值(面积即占比)')
    th = _theme(style, numfmt, note)
    return _render('treemap', title, _treemap_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def line(title: str, categories, values, *, name='销售额', style='business',
         animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
         sample: int | None = None, lower=None, upper=None,
         figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """单系列折线:粗线大圆点,最大/最小高亮;animate=True 渐进绘制;
    lower/upper 同时给出时画半透明区间带(预测/置信区间,随折线同步降采样);
    sample=N 对大数据做 LTTB 保形降采样(数千行 CSV 出图用)。"""
    cats, vals = _validate(categories, values)
    band = _validate_band(vals, lower, upper)
    th = _theme(style, numfmt, note)
    if sample and sample < len(cats) and sample >= 3:  # 带与线用同一批 LTTB 保留点
        idx = _lttb_indices(list(vals), sample)
        cats = [cats[i] for i in idx]
        vals = [vals[i] for i in idx]
        if band is not None:
            band = ([band[0][i] for i in idx], [band[1][i] for i in idx])
    return _render('line', title, _line_draw(title, cats, vals, th, name=name, band=band),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def line_multi(title: str, categories, series, *, value_labels=True, style='business',
               animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
               sample: int | None = None, figsize=None, dpi=None, numfmt='auto',
               note: str | None = None) -> Path:
    """多系列折线:series=[(名称, 数值列表), ...],图例在顶部,可带数值标注;
    sample=N 对大数据做 LTTB 保形降采样(各系列取保留索引并集,同步截取)。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style, numfmt, note)
    cats, vals_list = _downsample(cats, sample, [vals for _, vals in ss])
    ss = [(nm, vals) for (nm, _), vals in zip(ss, vals_list)]
    return _render('line_multi', title,
                   _line_multi_draw(title, cats, ss, th, value_labels),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def area(title: str, categories, values, *, name='数值', style='business',
         animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
         sample: int | None = None, figsize=None, dpi=None, numfmt='auto',
         note: str | None = None) -> Path:
    """面积图:折线 + 半透明填充;animate=True 渐进填充;
    sample=N 对大数据做 LTTB 保形降采样。"""
    cats, vals = _validate(categories, values)
    th = _theme(style, numfmt, note)
    cats, (vals,) = _downsample(cats, sample, [list(vals)])
    return _render('area', title, _line_draw(title, cats, vals, th, fill=True, name=name),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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


def combo(title: str, categories, bar_values, line_values, *,
          bar_name='柱状', line_name='折线', style='business',
          animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """双轴组合图:柱状(左轴)+ 折线(右轴),柱值需 >=0(折线值可为负);animate=True 同步生长。"""
    cats, bv = _validate(categories, bar_values)
    _, lv = _validate(categories, line_values)
    if min(bv) < 0:
        raise ValueError('combo 柱值需 >=0(折线值可为负)')
    th = _theme(style, numfmt, note)
    draw = _combo_draw(title, cats, bv, lv, th, bar_name, line_name)
    return _render('combo', title, draw, animate=animate, fmt=fmt, loop=loop, out=out,
                   out_dir=out_dir, th=th, figsize=figsize, dpi=dpi)


def bar_multi(title: str, categories, series, *, style='business',
              animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
              figsize=None, dpi=None, numfmt='auto',
              note: str | None = None) -> Path:
    """多系列分组柱状图:series=[(名称, 数值列表), ...],各系列 values 需 >=0,图例在顶部。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    if any(min(vals) < 0 for _, vals in ss):
        raise ValueError('多系列柱状图各系列 values 需 >=0')
    th = _theme(style, numfmt, note)
    return _render('bar_multi', title, _bar_multi_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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


def box(title: str, series, *, style='business', animate=False, fmt=None, loop=False,
        out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
        note: str | None = None) -> Path:
    """箱线图:series=[(组名, 原始样本), ...],各组样本数无需对齐;animate=True 箱体从中位数展开。"""
    ss = _validate_samples(series)
    th = _theme(style, numfmt, note)
    return _render('box', title, _box_draw(title, ss, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


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


def gantt(title: str, tasks, starts, ends, *, style='business', animate=False, fmt=None,
          loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """甘特图:tasks 为任务名,starts/ends 为数值(如天;日期轴暂不支持);
    ends 需 >= starts;工期最长/最短自动高亮;animate=True 逐条从起点生长。"""
    tsks, ss = _validate(tasks, starts)
    _, es = _validate(tasks, ends)
    if any(e < s for s, e in zip(ss, es)):
        bad = next(i for i, (s, e) in enumerate(zip(ss, es)) if e < s)
        raise ValueError(f'甘特图 ends 需 >= starts(任务「{tsks[bad]}」结束早于开始)')
    th = _theme(style, numfmt, note)
    return _render('gantt', title, _gantt_draw(title, tsks, ss, es, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def dumbbell(title: str, categories, series, *, slope=False, style='business',
             animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
             figsize=None, dpi=None, numfmt='auto',
             note: str | None = None) -> Path:
    """哑铃图(两期/两组对比):series 恰好 2 个 [(期初名, 值列表), (期末名, 值列表)];
    slope=True 出坡度图(期初/期末两列斜线,右端标类别名);animate=True 逐行浮现。"""
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


def themes_preview(*, out: str | None = None, out_dir=None, dpi=None) -> Path:
    """主题预览拼版图:全部主题各画一组相同数据的迷你柱状图,一张 PNG 对比选风格。"""
    cats, vals = ['一季度', '二季度', '三季度', '四季度'], [120, 200, 90, 160]
    names = list(THEMES)
    cols, rows = 4, math.ceil(len(names) / 4)
    fig = plt.figure(figsize=(cols * 4.2, rows * 2.9), facecolor='white')
    for i, name in enumerate(names):
        th = _theme(name)
        ax = fig.add_subplot(rows, cols, i + 1, facecolor=th.get('fig_face') or th['face'])
        with plt.rc_context(_sketch_rc_extra(th, 'white')):
            _bar_draw(THEME_LABELS[name], cats, vals, th)(ax, 1.0)
        # 格标题落在白色图底上,固定深灰(主题正文色在深色主题下是浅色,会看不清)
        ax.set_title(f'{THEME_LABELS[name]} · {name}', fontsize=13, color='#333333', pad=8)
    for j in range(len(names), rows * cols):
        fig.add_subplot(rows, cols, j + 1).axis('off')
    fig.subplots_adjust(left=0.04, right=0.985, top=0.93, bottom=0.04,
                        hspace=0.62, wspace=0.22)
    path = claim_path(resolve_out_dir(out_dir) / f'{safe_stem("themes", "预览", out)}.png')
    try:
        fig.savefig(path, dpi=dpi or DPI_PNG, facecolor='white')
    except BaseException:
        path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
        raise
    finally:
        plt.close(fig)
    print(f'主题预览图已生成: {path}')
    return path
