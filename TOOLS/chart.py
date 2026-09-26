"""图表生成：matplotlib 封装，同一份绘图代码输出 PNG / GIF / MP4 三种产物。

多主题设计：style 参数切换视觉风格，AI 可按用户意图选择——
    'excel'    Excel 经典风（默认）：粗蓝线大圆点、最大橙/最小灰高亮
    'soft'     柔和紫风：紫罗兰色系、点状浅网格
    'dark'     暗色风：深底亮色系
    'minimal'  极简风：黑白灰、细线、去装饰
    'tech'     科技风：深空底 + 霓虹青紫
    'vivid'    炫彩风：白底高饱和撞色
    'business' 商务风：藏青钢蓝、稳重低饱和
    'science'  科学风：出版物式四边框、细网格、克制配色
扩展新主题：在 THEMES 里加一组配色与网格参数即可，绘图代码零改动。

用法（模块化，返回文件路径，供 PPT/Word 生成脚本直接插入）：
    from TOOLS.chart import bar, line, line_multi, pie, donut, radar, area, combo, bar_multi

    line('月度增长', months, vals)                                     # 单系列折线
    line_multi('对比', months, [('销售额', v1), ('成本', v2)])           # 多系列折线
    donut('品类分布', cats, vals)                                       # 环形图
    radar('能力对比', abilities, [('学生A', va), ('学生B', vb)])         # 雷达图
    bar('产量', cats, vals, style='soft')                               # 换主题
    任意类型 animate=True 出 GIF，fmt='mp4' 出 MP4（需 ffmpeg）

约定：
    - 产物存 Cache/charts/（中间产物，TTL 3 天；嵌入 PPT/Word 后即可随 TTL 清理）
    - PNG 1920x1080（PPT 全屏），GIF 960x540（控制体积），MP4 1920x1080
    - 中文微软雅黑预设，import 即用；动画为"数据生长"式，GIF 播放一遍停在末帧（PPT 放映友好）
    - 注意：Word 不播放 GIF/MP4 动画（只显示首帧），文档配图一律用 PNG
"""
from __future__ import annotations

import argparse
import math
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # 无窗口渲染，必须在 pyplot 之前
from matplotlib import animation, rcParams
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

CHART_DIR = Path(__file__).resolve().parent.parent / 'Cache' / 'charts'
FIGSIZE = (12.8, 7.2)          # 16:9
DPI_PNG = 150                  # 12.8*150 = 1920px
DPI_GIF = 75                   # 960px，控制 GIF 体积
DPI_MP4 = 150
GIF_FPS, MP4_FPS, FRAMES = 20, 24, 48
HIGHLIGHT_SIZE = 650           # 最大/最小值高亮圆点大小（pt^2）

# ---------------- 主题库 ----------------

THEMES: dict[str, dict] = {
    'excel': dict(
        palette=('#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5', '#70AD47'),
        hi_max='#ED7D31', hi_min='#A5A5A5',
        face='white', text='#404040', axis='#BFBFBF',
        grid_color='#D9D9D9', grid_ls='-', grid_lw=0.9,
    ),
    'soft': dict(
        palette=('#8474D1', '#2F2B5B', '#A9A2E6', '#6FAEDF', '#E89A7C', '#E8C468'),
        hi_max='#E89A7C', hi_min='#B7B1DC',
        face='white', text='#4A4568', axis='#C9C5E4',
        grid_color='#DAD7EE', grid_ls=':', grid_lw=1.0,
    ),
    'dark': dict(
        palette=('#8FA8FF', '#FFB26B', '#7FD8BE', '#F28B9B', '#C3A6FF', '#7FD1F5'),
        hi_max='#FFB26B', hi_min='#5A6280',
        face='#1B2030', text='#E6E9F5', axis='#454C66',
        grid_color='#333A52', grid_ls='-', grid_lw=0.8,
    ),
    'minimal': dict(  # 极简风：黑白灰、细线、去装饰
        palette=('#2B2B2B', '#8A8A8A', '#BFBFBF', '#595959', '#A6A6A6', '#D0D0D0'),
        hi_max='#2B2B2B', hi_min='#C9C9C9',
        face='white', text='#1A1A1A', axis='#E0E0E0',
        grid_color='#EEEEEE', grid_ls='-', grid_lw=0.7,
    ),
    'tech': dict(  # 科技风：深空底 + 霓虹青紫
        palette=('#00D4FF', '#7B61FF', '#00FFC8', '#FF5CA8', '#FFB454', '#5B8CFF'),
        hi_max='#00D4FF', hi_min='#4A5578',
        face='#0B1020', text='#C8D6F0', axis='#2A3555',
        grid_color='#1E2A45', grid_ls='-', grid_lw=0.8,
    ),
    'vivid': dict(  # 炫彩风：白底高饱和撞色
        palette=('#FF4D6D', '#FFB627', '#06D6A0', '#4CC9F0', '#9B5DE5', '#F15BB5'),
        hi_max='#FF4D6D', hi_min='#B8B8B8',
        face='white', text='#333333', axis='#CCCCCC',
        grid_color='#E8E8E8', grid_ls='-', grid_lw=0.8,
    ),
    'business': dict(  # 商务风：藏青钢蓝、稳重低饱和
        palette=('#1F4E79', '#2E75B6', '#8496B0', '#C55A11', '#7C7C7C', '#BFBFBF'),
        hi_max='#C55A11', hi_min='#A6A6A6',
        face='white', text='#262626', axis='#BFBFBF',
        grid_color='#E3E7EC', grid_ls='-', grid_lw=0.8,
    ),
    'science': dict(  # 科学风：出版物式四边框、细网格、克配色
        palette=('#0C5DA5', '#00B945', '#FF9500', '#C20078', '#5B8CFF', '#7F7F7F'),
        hi_max='#C20078', hi_min='#7F7F7F',
        face='white', text='#000000', axis='#000000',
        grid_color='#E0E0E0', grid_ls='-', grid_lw=0.6,
        box=True,
    ),
}


def _setup_fonts() -> None:
    for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'):
        if Path(f).exists():
            fontManager.addfont(f)
            rcParams['font.sans-serif'] = [FontProperties(fname=f).get_name(), 'DejaVu Sans']
            break
    rcParams['axes.unicode_minus'] = False   # 坐标轴负号
    rcParams['font.size'] = 14


_setup_fonts()


# ---------- 内部工具 ----------

def _style(ax, title: str, th: dict) -> None:
    ax.set_title(title, fontsize=20, pad=18, color=th['text'])
    hide = () if th.get('box') else ('top', 'right')  # science 等主题保留四边框
    for side in ('top', 'right', 'left', 'bottom'):
        ax.spines[side].set_visible(side not in hide)
        ax.spines[side].set_color(th['axis'])
    ax.grid(axis='y', color=th['grid_color'], linestyle=th['grid_ls'],
            linewidth=th['grid_lw'])
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
    """图例放绘图区上方（figure 级定位，避免与标题重叠）。"""
    ax.figure.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.09, 0.985),
                     ncol=min(len(handles), 6), frameon=False, fontsize=13,
                     labelcolor=th['text'], handlelength=1.4, columnspacing=1.5)
    ax.figure.subplots_adjust(top=0.84)


def _ease(t: float) -> float:
    """ease-out 缓动：起步快、收尾慢，动画更自然。"""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def _stagger(p: float, i: int, n: int) -> float:
    """第 i 个元素的局部进度：错峰出现（重叠 60%），实现"逐根升起"。"""
    if n <= 1:
        return _ease(p)
    span = 0.6
    start = i / n * (1 - span)
    return _ease((p - start) / span)


def _ylim(ax, vals: list[float], th: dict) -> None:
    """按完整数据固定 y 轴范围，动画过程中坐标轴不跳动。

    正数且跨度大时从 0 起（Excel 默认行为）；数值挤在一起时才局部放大。
    """
    lo, hi = min(vals), max(vals)
    if lo >= 0 and lo <= hi * 0.8:
        ax.set_ylim(0, hi * 1.12)
        return
    pad = (hi - lo) or (abs(hi) or 1) * 0.2
    ax.set_ylim(lo - 0.15 * pad, hi + 0.2 * pad)


def _xticks(ax, cats: list[str], th: dict) -> None:
    xs = list(range(len(cats)))
    ax.set_xticks(xs)
    if len(cats) > 6 and max(len(c) for c in cats) > 4:  # 短标签（如"1月"）横排即可
        ax.set_xticklabels(cats, rotation=30, ha='right')
    else:
        ax.set_xticklabels(cats)


def _has_spread(vals: list[float]) -> bool:
    """数据有差异才谈得上最大/最小高亮。"""
    return len(vals) >= 2 and max(vals) != min(vals)


# ---------- 各图表的绘制函数（静态 = draw(ax, 1.0)，动画 = draw(ax, p)）----------

def _bar_draw(title, cats, vals, th):
    def draw(ax, p):
        _style(ax, title, th)
        hs = [v * _stagger(p, i, len(vals)) for i, v in enumerate(vals)]
        cols = [th['palette'][0]] * len(vals)
        if _has_spread(vals):  # 最大橙、最小灰，其余统一主色
            cols[vals.index(max(vals))] = th['hi_max']
            cols[vals.index(min(vals))] = th['hi_min']
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
        if k + 1 < n:  # 最后一小段插值，绘制更平滑
            xr.append(k + frac)
            yr.append(vals[k] + frac * (vals[k + 1] - vals[k]))
        if fill:
            ax.fill_between(xr, yr, color=th['palette'][0], alpha=0.30)
        ax.plot(xr, yr, color=th['palette'][0], linewidth=4, marker='o', markersize=16)
        if _has_spread(vals):  # 高亮圆点随推进显现
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
            if value_labels and n <= 12:  # 数值标注随线显现
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
        total = sum(vals) or 1
        sweep = 360 * _ease(p)  # 扇区按角度展开
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
        ax.set_theta_offset(math.pi / 2)   # 0° 放在顶部
        ax.set_theta_direction(-1)         # 顺时针
        s = _ease(p)  # 多边形从中心放大
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
        # 极坐标圆是等比正方形，顶部必须预留标题空间，否则标题会被裁掉
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
            prog = _stagger(p, si, m)  # 每组柱依次升起
            ax.bar([i + (si - m / 2 + 0.5) * w for i in range(ng)],
                   [v * prog for v in vals], width=w * 0.92,
                   color=th['palette'][si % len(th['palette'])], label=nm)
        ax.set_ylim(0, max(max(v) for _, v in series) * 1.15)
        _xticks(ax, cats, th)
        _legend_top(ax, [Patch(facecolor=th['palette'][si % len(th['palette'])],
                               label=nm) for si, (nm, _) in enumerate(series)], th)
    return draw


# ---------- 渲染 ----------

class _OncePillowWriter(animation.PillowWriter):
    """播放一遍后停在末帧的 GIF writer。

    matplotlib 默认 finish() 写死 loop=0（无限循环），插进 PPT 会反复重播；
    不传 loop 参数即不写 NETSCAPE 循环扩展，GIF 播完停在最后一帧。
    """

    def finish(self):
        self._frames[0].save(
            self.outfile, save_all=True, append_images=self._frames[1:],
            duration=int(1000 / self.fps))


def _render(kind, title, draw, *, animate, fmt, out,
            face: str = 'white', polar: bool = False) -> Path:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', out or f'{kind}_{title}').strip('_')[:60] or 'chart'

    if not animate:  # PNG
        path = CHART_DIR / f'{stem}.png'
        fig = plt.figure(figsize=FIGSIZE, facecolor=face)
        draw(fig.add_subplot(111, polar=polar), 1.0)
        fig.savefig(path, dpi=DPI_PNG, facecolor=face)
        plt.close(fig)
    else:
        fmt = (fmt or 'gif').lower()
        if fmt == 'mp4':
            if not shutil.which('ffmpeg'):
                raise RuntimeError('未找到 ffmpeg（MP4 需要）。'
                                   '安装：winget install ffmpeg，或改用 fmt="gif"')
            path, writer, fps, dpi = (CHART_DIR / f'{stem}.mp4',
                                      animation.FFMpegWriter(fps=MP4_FPS, codec='h264',
                                                             extra_args=['-pix_fmt', 'yuv420p']),
                                      MP4_FPS, DPI_MP4)
        else:
                path, writer, fps, dpi = (CHART_DIR / f'{stem}.gif',
                                          _OncePillowWriter(fps=GIF_FPS), GIF_FPS, DPI_GIF)

        fig = plt.figure(figsize=FIGSIZE, facecolor=face)

        def update(i):
            fig.clear()  # 连同 twinx 一起清空，避免帧间残留
            draw(fig.add_subplot(111, polar=polar), i / (FRAMES - 1))

        ani = animation.FuncAnimation(fig, update, frames=FRAMES, interval=1000 / fps)
        try:
            ani.save(path, writer=writer, dpi=dpi, savefig_kwargs={'facecolor': face})
        finally:
            plt.close('all')

    print(f'图表已生成: {path}')
    return path


def _validate(categories, values) -> tuple[list, list]:
    cats = [str(c) for c in categories]
    vals = [float(v) for v in values]
    if not cats or len(cats) != len(vals):
        raise ValueError('categories 与 values 必须非空且长度一致')
    return cats, vals


def _validate_series(categories, series) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...]，各系列长度必须与类目一致。"""
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


def _theme(style: str | None) -> dict:
    th = THEMES.get(style or 'excel', THEMES['excel'])
    return dict(th, palette=list(th['palette']))


# ---------- 公开 API ----------

def bar(title: str, categories, values, *, style='excel', animate=False, fmt='gif',
        out: str | None = None) -> Path:
    """柱状图（values 需 >=0）：统一主色，最大/最小高亮。animate=True 时逐根升起。"""
    cats, vals = _validate(categories, values)
    return _render('bar', title, _bar_draw(title, cats, vals, _theme(style)),
                   animate=animate, fmt=fmt, out=out,
                   face=_theme(style)['face'])


def line(title: str, categories, values, *, name='销售额', style='excel',
         animate=False, fmt='gif', out: str | None = None) -> Path:
    """单系列折线：粗线大圆点，最大/最小高亮。animate=True 时渐进绘制。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('line', title, _line_draw(title, cats, vals, th, name=name),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


def line_multi(title: str, categories, series, *, value_labels=True, style='excel',
               animate=False, fmt='gif', out: str | None = None) -> Path:
    """多系列折线：series=[(名称, 数值列表), ...]，图例在顶部，可带数值标注。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('line_multi', title,
                   _line_multi_draw(title, cats, ss, th, value_labels),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


def area(title: str, categories, values, *, name='数值', style='excel',
         animate=False, fmt='gif', out: str | None = None) -> Path:
    """面积图：折线 + 半透明填充。animate=True 时渐进填充。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('area', title, _line_draw(title, cats, vals, th, fill=True, name=name),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


def pie(title: str, categories, values, *, style='excel', animate=False, fmt='gif',
        out: str | None = None) -> Path:
    """饼图（values 需 >=0）。animate=True 时扇区展开。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('pie', title, _pie_like_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


def donut(title: str, categories, values, *, show_values=True, style='excel',
          animate=False, fmt='gif', out: str | None = None) -> Path:
    """环形图：外部"类目 数值"标注 + 底部图例。animate=True 时扇区展开。"""
    cats, vals = _validate(categories, values)
    th = _theme(style)
    return _render('donut', title, _pie_like_draw(title, cats, vals, th, donut=True,
                                                  show_values=show_values),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


def radar(title: str, categories, series, *, style='excel',
          animate=False, fmt='gif', out: str | None = None) -> Path:
    """雷达图：series=[(名称, 数值列表), ...]。animate=True 时多边形从中心展开。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('radar', title, _radar_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, out=out, face=th['face'], polar=True)


def combo(title: str, categories, bar_values, line_values, *,
          bar_name='柱状', line_name='折线', style='excel',
          animate=False, fmt='gif', out: str | None = None) -> Path:
    """双轴组合图：柱状（左轴）+ 折线（右轴），animate=True 时两者同步生长。"""
    cats, bv = _validate(categories, bar_values)
    _, lv = _validate(categories, line_values)
    th = _theme(style)
    draw = _combo_draw(title, cats, bv, lv, th, bar_name, line_name)
    return _render('combo', title, draw, animate=animate, fmt=fmt, out=out, face=th['face'])


def bar_multi(title: str, categories, series, *, style='excel',
              animate=False, fmt='gif', out: str | None = None) -> Path:
    """多系列分组柱状图：series=[(名称, 数值列表), ...]，图例在顶部。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    th = _theme(style)
    return _render('bar_multi', title, _bar_multi_draw(title, cats, ss, th),
                   animate=animate, fmt=fmt, out=out, face=th['face'])


# ---------- 命令行 ----------

def _parse_pairs(items: list[str]) -> tuple[list[str], list[float]]:
    cats, vals = [], []
    for it in items:
        k, _, v = it.partition('=')
        if not k or not v:
            raise SystemExit(f'数据格式应为 类别=数值，收到: {it!r}')
        cats.append(k)
        vals.append(float(v))
    return cats, vals


def main() -> None:
    ap = argparse.ArgumentParser(description='生成图表到 Cache/charts/（PNG/GIF/MP4）')
    ap.add_argument('type', choices=['bar', 'line', 'pie', 'area', 'donut'], help='图表类型')
    ap.add_argument('title', help='标题')
    ap.add_argument('data', nargs='+', help='数据，格式 类别=数值，如 Q1=120')
    ap.add_argument('--style', choices=list(THEMES), default='excel', help='视觉风格')
    ap.add_argument('--animate', action='store_true', help='生成动画（默认 GIF）')
    ap.add_argument('--fmt', choices=['gif', 'mp4'], default='gif', help='动画格式')
    ap.add_argument('--out', help='输出文件名（不含扩展名），默认 类型_标题')
    args = ap.parse_args()
    cats, vals = _parse_pairs(args.data)
    fn = {'bar': bar, 'line': line, 'pie': pie, 'area': area, 'donut': donut}[args.type]
    path = fn(args.title, cats, vals, style=args.style,
              animate=args.animate, fmt=args.fmt, out=args.out)
    raise SystemExit(0 if path else 1)


if __name__ == '__main__':
    main()
