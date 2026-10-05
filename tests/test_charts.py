"""冒烟测试:22 类型 × 静态 PNG 全量,动画抽样 5 代表型 × GIF / MP4;产物即测即删。"""
from __future__ import annotations

import shutil
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image

from chartmove import (
    THEMES,
    area,
    bar,
    bar_multi,
    box,
    bubble,
    combo,
    donut,
    dumbbell,
    fonts,
    funnel,
    gantt,
    heatmap,
    hist,
    line,
    line_multi,
    pareto,
    pie,
    radar,
    rose,
    scatter,
    sunburst,
    treemap,
    waterfall,
)
from chartmove.graph.charts.categorical import (
    _bar_draw,
    _bar_multi_draw,
    _pareto_draw,
    _waterfall_draw,
)
from chartmove.graph.charts.composition import _pie_like_draw, _sunburst_draw
from chartmove.graph.charts.distribution import (
    _box_draw,
    _bubble_draw,
    _heatmap_draw,
    _hist_draw,
    _scatter_draw,
)
from chartmove.graph.charts.flow import _funnel_draw
from chartmove.graph.charts.trend import (
    _area_draw,
    _combo_draw,
    _line_draw,
    _line_multi_draw,
)
from chartmove.graph.render import FRAMES, GIF_FPS, _stagger
from chartmove.graph.style import _nf, _theme
from chartmove.graph.validate import _downsample, _lttb_indices
from chartmove.themes import THEME_DESCS, THEME_LABELS, THEME_PACKS

HAS_FFMPEG = shutil.which('ffmpeg') is not None

CATS = ['Q1', 'Q2', 'Q3', 'Q4']
VALS = [120, 200, 90, 160]
SERIES = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
HIERARCHY = {'线上': {'直营': 40, '分销': 25}, '门店': {'直营': 20, '加盟': 15}}
XS = [1, 2, 3, 4, 5, 6]
YS = [120, 200, 90, 160, 210, 150]
MATRIX = [[3, 7, 2, 5], [8, 1, 6, 4], [2, 5, 9, 3], [6, 2, 4, 8]]

SINGLE = dict(categories=CATS, values=VALS)
CASES: dict[str, tuple] = {
    'bar': (bar, dict(SINGLE)),
    'line': (line, dict(SINGLE, lower=[100, 180, 70, 140],
                        upper=[140, 220, 110, 180])),
    'area': (area, dict(SINGLE)),
    'pie': (pie, dict(SINGLE)),
    'donut': (donut, dict(SINGLE)),
    'line_multi': (line_multi, dict(categories=CATS, series=SERIES)),
    'bar_multi': (bar_multi, dict(categories=CATS, series=SERIES)),
    'radar': (radar, dict(categories=CATS, series=SERIES)),
    'combo': (combo, dict(categories=CATS, bar_values=VALS,
                          line_values=[80, 140, 100, 180])),
    'scatter': (scatter, dict(xs=XS, ys=YS, labels=['a', 'b', 'c', 'd', 'e', 'f'])),
    'bubble': (bubble, dict(xs=XS, ys=YS, sizes=[10, 40, 5, 25, 35, 15])),
    'hist': (hist, dict(values=[68, 72, 70, 75, 77, 80, 82, 85, 88, 90,
                                91, 95, 55, 60, 63, 66])),
    'box': (box, dict(series=[('组A', [3, 5, 4, 6, 7, 5, 4]),
                              ('组B', [8, 9, 7, 10, 6, 9, 8]),
                              ('组C', [2, 3, 2, 4, 3, 5, 2])])),
    'heatmap': (heatmap, dict(rows=['周一', '周二', '周三', '周四'],
                              cols=['上午', '中午', '下午', '晚间'], values=MATRIX)),
    'waterfall': (waterfall, dict(categories=CATS, values=[120, -30, 50, -20])),
    'funnel': (funnel, dict(categories=['访问', '加购', '下单', '付款'],
                            values=[1000, 420, 180, 120])),
    'rose': (rose, dict(SINGLE)),
    'treemap': (treemap, dict(SINGLE)),
    'gantt': (gantt, dict(tasks=CATS, starts=[1, 4, 8, 12], ends=[5, 9, 13, 15])),
    'dumbbell': (dumbbell, dict(categories=CATS, series=SERIES, slope=True)),
    'sunburst': (sunburst, dict(hierarchy=HIERARCHY)),
    'pareto': (pareto, dict(SINGLE)),
}


def _render(fn, kw, tmp_path, **extra):
    """渲染并捕获警告,返回 (路径, 警告消息列表)。"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        path = fn('中文标题验证', out_dir=tmp_path, **kw, **extra)
    return path, [str(w.message) for w in caught]


def _assert_ok(path: Path, ext: str, warns: list[str]) -> None:
    assert isinstance(path, Path) and path.is_absolute()
    assert path.exists() and path.stat().st_size > 0
    assert path.suffix == f'.{ext}'
    if fonts.FAMILY is not None:  # 中文字体命中时不允许缺字警告
        assert not [w for w in warns if 'missing from font' in w], '中文字体缺字'
    path.unlink()  # 即测即删


ANIM_SAMPLE = ('bar', 'line', 'line_multi', 'heatmap', 'sunburst')
"""动画矩阵抽样(P4-2):全类型 × 2 动画曾是 CI 时长大头,按动画实现取代表——
bar=逐根升起、line=渐进折线(含区间带逐帧展开)、line_multi=多系列渐进、
heatmap=逐格淡入、sunburst=双环扇形展开。"""


@pytest.mark.parametrize('name', list(CASES))
def test_matrix_static(name, tmp_path):
    """验收主体:21 种类型 × 静态 PNG 全量(覆盖所有绘制分支,~0.1s/张)。"""
    fn, kw = CASES[name]
    path, warns = _render(fn, kw, tmp_path, fmt='png')
    _assert_ok(path, 'png', warns)


@pytest.mark.parametrize('fmt', ['gif', 'mp4'])
@pytest.mark.parametrize('name', ANIM_SAMPLE)
def test_matrix_animated(name, fmt, tmp_path):
    """动画矩阵:抽样 4 个代表类型 × GIF / MP4,覆盖三种动画实现。"""
    if fmt == 'mp4' and not HAS_FFMPEG:
        pytest.skip('未安装 ffmpeg,跳过 MP4')
    fn, kw = CASES[name]
    path, warns = _render(fn, kw, tmp_path, animate=True, fmt=fmt)
    _assert_ok(path, fmt, warns)


@pytest.mark.parametrize('style', list(THEMES))
def test_all_themes(style, tmp_path):
    """每个主题过一遍柱状 + 多系列折线(覆盖四边框/无脊线/双向网格/手绘等分支)。"""
    path, warns = _render(bar, dict(SINGLE, style=style), tmp_path)
    _assert_ok(path, 'png', warns)
    path, warns = _render(line_multi,
                          dict(categories=CATS, series=SERIES, style=style), tmp_path)
    _assert_ok(path, 'png', warns)


def test_sketch_theme_animated(tmp_path):
    """手绘草图风的 rc_context 需在动画逐帧绘制期间持续生效。"""
    path, warns = _render(bar, dict(SINGLE, style='sketch'), tmp_path,
                          animate=True, fmt='gif')
    _assert_ok(path, 'gif', warns)


def test_gif_default_plays_once(tmp_path):
    """默认 GIF 不写 NETSCAPE 循环扩展:播一遍停在末帧(PPT 里不重播)。"""
    path, warns = _render(bar, dict(SINGLE), tmp_path, animate=True, fmt='gif')
    assert b'NETSCAPE2.0' not in path.read_bytes()
    _assert_ok(path, 'gif', warns)


def test_gif_loop_infinite(tmp_path):
    """loop=True 写入 NETSCAPE 无限循环扩展。"""
    path, warns = _render(bar, dict(SINGLE, loop=True), tmp_path,
                          animate=True, fmt='gif')
    assert b'NETSCAPE2.0' in path.read_bytes()
    _assert_ok(path, 'gif', warns)


def test_gif_total_duration_constant(tmp_path, full_animation):
    """Pillow 丢弃相同帧时会把时长累加到保留帧:任何图表 GIF 总时长恒为 48 帧 × 50ms,
    分步生长的图(热力图等)帧数少但节奏不变。"""
    path, _ = _render(heatmap, dict(rows=['r1', 'r2'], cols=['c1', 'c2'],
                                    values=[[1, 2], [3, 4]]), tmp_path,
                      animate=True, fmt='gif')
    with Image.open(path) as im:
        total = 0
        for i in range(im.n_frames):
            im.seek(i)
            total += im.info['duration']
        assert im.n_frames >= 40  # 逐格渐入后几乎每帧都有变化(修复前仅 ~6 帧)
    assert total == FRAMES * int(1000 / GIF_FPS)


def test_stagger_finishes_at_one():
    """错峰动画的最后元素恰在 p=1 完成(修复前 p≈0.8~0.92 提前收尾,留下静止尾巴)。"""
    for n in (2, 3, 4, 8, 16):
        assert _stagger(1.0, n - 1, n) == 1.0
        assert _stagger(0.95, n - 1, n) < 1.0  # 完成点若提前,p<1 时就会到 1
        assert _stagger(0.0, n - 1, n) == 0.0


def test_heatmap_reveal_and_stroke():
    """热力图逐格渐入:最大/最小格描边随所在格淡入(p=0 无、p=1 全有),不再末帧突现。"""
    arr = np.array([[1, 9, 2], [3, 5, 4]])  # 最大 9 在第 2 列,最小 1 在第 1 列
    fig, ax = plt.subplots()
    try:
        draw = _heatmap_draw('t', ['r1', 'r2'], ['c1', 'c2', 'c3'], arr,
                             _theme('business'))
        draw(ax, 0.0)
        assert len(ax.patches) == 0
        ax.clear()
        draw(ax, 1.0)
        assert len(ax.patches) == 2  # 两条描边
        assert all(not r.get_fill() for r in ax.patches)
    finally:
        plt.close(fig)


def _stability_draws() -> dict:
    """各图表的 draw 构建器(坐标轴稳定性回归用);pie/radar/heatmap 无此问题不列。"""
    th = _theme('business')
    cats, vals = ['Q1', 'Q2', 'Q3', 'Q4'], [120, 200, 90, 160]
    series = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
    xs, ys = [1, 2, 3, 4, 5, 6], [120, 200, 90, 160, 210, 150]
    return {
        'bar': lambda: _bar_draw('t', cats, vals, th),
        'line': lambda: _line_draw('t', cats, vals, th),
        'line_multi': lambda: _line_multi_draw('t', cats, series, th),
        'combo': lambda: _combo_draw('t', cats, vals, [80, 140, 100, 180], th, '柱', '线'),
        'bar_multi': lambda: _bar_multi_draw('t', cats, series, th),
        'bar_multi_stacked': lambda: _bar_multi_draw('t', cats, series, th, stacked=True),
        'scatter': lambda: _scatter_draw('t', xs, ys, th),
        'bubble': lambda: _bubble_draw('t', xs, ys, [10, 40, 5, 25, 35, 15], th),
        'hist': lambda: _hist_draw('t', [68, 72, 70, 75, 77, 80, 82, 85], 8, th),
        'box': lambda: _box_draw('t', [('组A', [3, 5, 4, 6, 7]), ('组B', [8, 9, 7])], th),
        'waterfall': lambda: _waterfall_draw('t', cats, vals, th),
        'funnel': lambda: _funnel_draw('t', ['访问', '加购'], [1000, 420], th),
        'pareto': lambda: _pareto_draw('t', cats, vals, th),
    }


def test_axes_limits_stable_during_animation():
    """动画期间坐标轴固定:逐元素出现的图(散点/气泡/箱线/折线等)轴不得随数据扩张滑动。"""
    fig, axes = plt.subplots(2, 7, figsize=(21, 6))
    try:
        for ax, (name, build) in zip(axes.flat, _stability_draws().items()):
            draw = build()
            draw(ax, 0.0)
            lim0 = (tuple(ax.get_xlim()), tuple(ax.get_ylim()))
            ax.clear()
            draw(ax, 1.0)
            lim1 = (tuple(ax.get_xlim()), tuple(ax.get_ylim()))
            assert lim0 == lim1, f'{name} 坐标轴在动画中移动: {lim0} -> {lim1}'
    finally:
        plt.close(fig)


def test_xticks_auto_thinning():
    """类目 >25 自动抽稀到 ~10 个刻度(5000 类目标签不再叠成黑带),首尾保留。"""
    th = _theme('business')
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    try:
        _line_draw('t', [str(i) for i in range(5000)], list(range(5000)), th)(ax, 1.0)
        ticks = [int(t) for t in ax.get_xticks()]
        assert len(ticks) == 10
        assert ticks[0] == 0 and ticks[-1] == 4999
        labels = [t.get_text() for t in ax.get_xticklabels()]
        assert labels[0] == '0' and labels[-1] == '4999'
    finally:
        plt.close(fig)
    fig, ax = plt.subplots()
    try:
        _line_draw('t', [str(i) for i in range(25)], list(range(25)), th)(ax, 1.0)
        assert len(ax.get_xticks()) == 25  # 阈值内不抽稀
    finally:
        plt.close(fig)


def test_marker_thinning_markevery():
    """折线点数 >50 时标记隔点绘制(markevery),≤50 保持逐点;线体不受影响。"""
    th = _theme('business')
    fig, ax = plt.subplots()
    try:
        _line_draw('t', [str(i) for i in range(100)], list(range(100)), th)(ax, 1.0)
        assert ax.lines[0].get_markevery() == 2  # ceil(100 / 50)
        ax.clear()
        _line_draw('t', [str(i) for i in range(30)], list(range(30)), th)(ax, 1.0)
        assert ax.lines[0].get_markevery() == 1
    finally:
        plt.close(fig)


def test_lttb_and_downsample():
    """LTTB 降采样:保首尾、点数达标、尖峰不丢;多系列取并集同步截取;越界值原样返回。"""
    ys = [0.0] * 1000 + [100.0] + [0.0] * 1000
    keep = _lttb_indices(ys, 100)
    assert len(keep) == 100 and keep[0] == 0 and keep[-1] == 2000
    assert 1000 in keep  # 尖峰必须保留
    cats = [str(i) for i in range(1000)]
    s1 = [float(i) for i in range(1000)]
    s2 = [float(i % 7) for i in range(1000)]
    c2, (o1, o2) = _downsample(cats, 100, [s1, s2])
    assert len(c2) == len(o1) == len(o2) <= 300  # 并集 ≤ 各系列保留点之和
    assert c2[0] == '0' and c2[-1] == '999' and o1[-1] == 999.0
    c3, (o3,) = _downsample(cats[:50], 100, [s1[:50]])  # sample ≥ 点数:原样
    assert c3 == cats[:50] and o3 == s1[:50]


def test_line_big_data_sample(tmp_path):
    """5000 行 + sample=300:降采样后正常出图(刻度自动抽稀,渲染速度快)。"""
    cats = [str(i) for i in range(5000)]
    vals = [float(i % 97) for i in range(5000)]
    path, _ = _render(line, dict(categories=cats, values=vals, sample=300),
                      tmp_path, fmt='png')
    _assert_ok(path, 'png', [])


def test_waterfall_geometry():
    """瀑布图几何:正值柱从上一累计水平升起,负值柱向下悬挂,合计柱从 0 画到代数和(回归)。"""
    fig, ax = plt.subplots()
    try:
        draw = _waterfall_draw('t', ['A', 'B', 'C'], [100, -40, 50], _theme('business'))
        draw(ax, 1.0)  # 终态:p=1 时每个元素的错峰进度均为 1
        rects = sorted(ax.patches, key=lambda r: r.get_x())
        assert [(r.get_y(), r.get_height()) for r in rects] == pytest.approx(
            [(0, 100), (60, 40), (60, 50), (0, 110)])
    finally:
        plt.close(fig)


def test_hist_bins_edges_array():
    """bins 边界数组直通 np.histogram(P1-2:CLI/MCP 此前都送不进这个语义)。"""
    fig, ax = plt.subplots()
    try:
        _hist_draw('t', [1, 5, 12, 18, 25], [1, 10, 20], _theme('business'))(ax, 1.0)
        assert len(ax.patches) == 2  # 3 条边界 → 2 个箱
    finally:
        plt.close(fig)


def test_waterfall_total_false():
    """回归:total=False 曾与 total=True 产物逐字节相同(合计柱从不缺席)。"""
    fig, ax = plt.subplots()
    try:
        _waterfall_draw('t', ['A', 'B', 'C'], [100, -40, 50], _theme('business'),
                        False)(ax, 1.0)
        rects = sorted(ax.patches, key=lambda r: r.get_x())
        assert len(rects) == 3                      # 无「合计」柱
        assert [r.get_height() for r in rects] == pytest.approx([100, 40, 50])
    finally:
        plt.close(fig)


def test_bar_multi_stacked_geometry():
    """堆积柱几何:每段柱底 = 前系列终值累计;百分比堆积每类目柱顶合计 = 100。"""
    fig, ax = plt.subplots()
    try:
        _bar_multi_draw('t', CATS, SERIES, _theme('business'), stacked=True)(ax, 1.0)
        rects = ax.patches  # 逐系列成批:前 4 根 = 系列1,后 4 根 = 系列2
        assert len(rects) == 8
        for ci in range(4):
            assert rects[ci].get_x() + rects[ci].get_width() / 2 == pytest.approx(ci)
            assert rects[ci].get_y() == 0
            assert rects[4 + ci].get_y() == pytest.approx(SERIES[0][1][ci])
            assert rects[4 + ci].get_height() == pytest.approx(SERIES[1][1][ci])
    finally:
        plt.close(fig)
    fig, ax = plt.subplots()
    try:
        _bar_multi_draw('t', CATS, SERIES, _theme('business'), percent=True)(ax, 1.0)
        assert ax.get_ylim() == (0.0, 100.0)  # 百分比堆积轴固定 0–100
        for ci in range(4):
            top = max(r.get_y() + r.get_height() for r in ax.patches
                      if abs(r.get_x() + r.get_width() / 2 - ci) < 0.01)
            assert top == pytest.approx(100)
    finally:
        plt.close(fig)


def test_area_multi_and_stacked(tmp_path):
    """多系列面积三种模式(叠加 / 堆积 / 百分比堆积)全部出图;堆积校验契约。"""
    for sp in ({}, {'stacked': True}, {'percent': True}):
        path, warns = _render(area, dict(categories=CATS, series=SERIES, **sp), tmp_path)
        _assert_ok(path, 'png', warns)
    path, warns = _render(area, dict(categories=CATS, values=VALS, name='访问量'),
                          tmp_path)  # 单系列路径不回归
    _assert_ok(path, 'png', warns)
    with pytest.raises(ValueError, match='二选一'):
        area('t', CATS, VALS, series=SERIES)
    with pytest.raises(ValueError, match=r'values\(单系列\)'):
        area('t', CATS)
    with pytest.raises(ValueError, match='堆积面积图需要多系列'):
        area('t', CATS, VALS, stacked=True)
    with pytest.raises(ValueError, match='需 >=0'):
        area('t', CATS, series=[('a', [1, -2, 3, 4]), ('b', [1, 2, 3, 4])],
             stacked=True)


def test_area_stacked_geometry():
    """堆积面积分层:下层 0→系列1,上层系列1→两系列累计;百分比堆积轴 0–100。"""
    from matplotlib.collections import PolyCollection
    fig, ax = plt.subplots()
    try:
        _area_draw('t', CATS, SERIES, _theme('business'), stacked=True)(ax, 1.0)
        polys = [c for c in ax.collections if isinstance(c, PolyCollection)]
        assert len(polys) == 2
        ys0 = [y for poly in polys[0].get_paths() for pts in poly.to_polygons()
               for _, y in pts]
        ys1 = [y for poly in polys[1].get_paths() for pts in poly.to_polygons()
               for _, y in pts]
        assert min(ys0) == pytest.approx(0) and max(ys0) == pytest.approx(260)
        assert min(ys1) == pytest.approx(120)  # 上层底 = 系列1 的值序列
        assert max(ys1) == pytest.approx(370)  # 上层顶 = 两系列累计
    finally:
        plt.close(fig)
    fig, ax = plt.subplots()
    try:
        _area_draw('t', CATS, SERIES, _theme('business'), percent=True)(ax, 1.0)
        assert ax.get_ylim() == (0.0, 100.0)
    finally:
        plt.close(fig)


def test_sunburst_labels_and_validation(tmp_path):
    """旭日图:内外环标签齐备;层级数据校验契约(空/无子级/负值/全零/形状)。"""
    fig, ax = plt.subplots()
    try:
        _sunburst_draw('t', [('线上', [('直营', 40), ('分销', 25)]),
                             ('门店', [('直营', 20), ('加盟', 15)])],
                       _theme('business'))(ax, 1.0)
        texts = [t.get_text() for t in ax.texts]
        assert '线上' in texts and '门店' in texts          # 内环父类目
        assert '直营 40' in texts and '加盟 15' in texts    # 外环"子类目 数值"
    finally:
        plt.close(fig)
    path, warns = _render(sunburst, dict(hierarchy=HIERARCHY), tmp_path, animate=True,
                          fmt='gif')
    _assert_ok(path, 'gif', warns)  # 双环扇形展开动画
    with pytest.raises(ValueError, match='不能为空'):
        sunburst('t', {})
    with pytest.raises(ValueError, match='至少需要 1 个子类目'):
        sunburst('t', {'水果': {}})
    with pytest.raises(ValueError, match='需 >=0'):
        sunburst('t', {'水果': {'苹果': -5}})
    with pytest.raises(ValueError, match='需有正值'):
        sunburst('t', {'水果': {'苹果': 0}, '门店': {'直营': 0}})
    with pytest.raises(ValueError, match='子类目'):
        sunburst('t', [['水果', [30]]])
    with pytest.raises(ValueError, match='hierarchy 需为'):
        sunburst('t', [['水果', {'苹果': 30}, '多出来的']])


def test_pareto_sorted_and_cumulative():
    """帕累托:柱自动降序,右轴累计占比 = cumsum/total 且轴钉 0–100,80% 参考线存在。"""
    fig, ax = plt.subplots()
    try:
        _pareto_draw('t', ['a', 'b', 'c', 'd'], [40, 10, 30, 20], _theme('business'))(ax, 1.0)
        bars = sorted(ax.patches, key=lambda r: r.get_x())
        assert [r.get_height() for r in bars] == pytest.approx([40, 30, 20, 10])
        assert [t.get_text() for t in ax.get_xticklabels()] == ['a', 'c', 'd', 'b']
        right = fig.axes[1]  # twinx 右轴
        assert list(right.lines[0].get_ydata()) == pytest.approx([40, 70, 90, 100])
        assert right.get_ylim() == (0.0, 100.0)
        assert len(right.lines) == 2  # 累计线 + 80% 参考线
    finally:
        plt.close(fig)


def test_pareto_validation():
    """帕累托校验契约:负值拒绝;全零拒绝(累计占比无意义)。"""
    with pytest.raises(ValueError, match='帕累托图'):
        pareto('t', ['a', 'b'], [5, -3])
    with pytest.raises(ValueError, match='需有正值'):
        pareto('t', ['a', 'b'], [0, 0])


def test_bar_multi_percent_labels():
    """百分比堆积段内标签:占比 >=4% 的段标 'n%'(参考经典样式),过小段不标。"""
    fig, ax = plt.subplots()
    try:
        _bar_multi_draw('t', CATS, SERIES, _theme('business'), percent=True)(ax, 1.0)
        texts = [t.get_text() for t in ax.texts]
        assert '57%' in texts and '43%' in texts  # Q1: 120/210、90/210
    finally:
        plt.close(fig)
    tiny = [('甲', [1, 1]), ('乙', [50, 50]), ('丙', [0.5, 0.5])]
    fig, ax = plt.subplots()
    try:
        _bar_multi_draw('t', ['x', 'y'], tiny, _theme('business'), percent=True)(ax, 1.0)
        texts = [t.get_text() for t in ax.texts]
        assert any(t == '97%' for t in texts)   # 乙 50/51.5
        assert not any(t == '2%' for t in texts)  # 甲 1.94% < 4% 不标
    finally:
        plt.close(fig)


def test_pie_value_not_duplicated():
    """回归:饼图数值曾在外标签与扇区内重复出现(图例再列一遍类目)。
    修复后数值只保留在外标签,<6% 的小扇区也不丢数。"""
    fig, ax = plt.subplots()
    try:
        _pie_like_draw('t', ['A', 'B', '小'], [70, 25, 5],
                       _theme('business'))(ax, 1.0)
        assert not [t for t in ax.texts if t.get_text() == '70']  # 扇区内无重复数值
        assert any('A 70' in t.get_text() for t in ax.texts)      # 数值在外标签
        assert any('小 5' in t.get_text() for t in ax.texts)      # 小扇区不丢数
    finally:
        plt.close(fig)


def test_donut_show_values_false():
    """回归:donut(show_values=False) 曾因解包 ax.pie 的二元返回值直接 ValueError。"""
    fig, ax = plt.subplots()
    try:
        _pie_like_draw('t', ['A', 'B'], [70, 30], _theme('business'),
                       donut=True, show_values=False)(ax, 1.0)
        assert not [t for t in ax.texts if '70' in t.get_text()]  # 不标数值
        assert any(t.get_text() == 'A' for t in ax.texts)         # 只标类目名
    finally:
        plt.close(fig)


def test_theme_metadata():
    """13 主题分 4 包;每个主题都有中文名与一句话描述,包成员无遗漏无重复。"""
    assert len(THEMES) == 13
    assert sorted(THEME_PACKS) == ['其他风格包', '商务包', '学术包', '简约演示包']
    packed = [k for members in THEME_PACKS.values() for k in members]
    assert sorted(packed) == sorted(THEMES)
    assert set(THEME_LABELS) == set(THEMES) and set(THEME_DESCS) == set(THEMES)


def test_unknown_style_rejected():
    """回归:库调用传错主题名曾被静默兜底成 business;None / '' 的回退保留。"""
    with pytest.raises(ValueError, match='未知主题'):
        _theme('bussiness')
    assert _theme(None) == _theme('business')
    assert _theme('') == _theme('business')


@pytest.mark.parametrize('fmt', ['pdf', 'tif'])
def test_static_formats(fmt, tmp_path):
    path, warns = _render(bar, dict(SINGLE), tmp_path, fmt=fmt)
    _assert_ok(path, fmt, warns)


def test_bar_horizontal(tmp_path):
    path, warns = _render(bar, dict(SINGLE, horizontal=True), tmp_path)
    _assert_ok(path, 'png', warns)


def test_figsize_dpi_take_effect(tmp_path):
    path, warns = _render(line, dict(SINGLE, figsize=(6.4, 3.6), dpi=100), tmp_path)
    assert path.exists()
    with Image.open(path) as im:
        assert im.size == (640, 360)  # 6.4*100 x 3.6*100,参数确实生效
    path.unlink()


def test_filename_from_title(tmp_path):
    path, _ = _render(bar, dict(SINGLE), tmp_path)
    assert path.name == 'bar_中文标题验证.png'
    path.unlink()


def test_static_rejects_animated_fmt(tmp_path):
    with pytest.raises(ValueError, match='静态图支持'):
        bar('t', CATS, VALS, out_dir=tmp_path, fmt='gif')


def test_animated_rejects_static_fmt(tmp_path):
    with pytest.raises(ValueError, match='动画仅支持'):
        bar('t', CATS, VALS, out_dir=tmp_path, animate=True, fmt='png')


def test_loop_rejected_for_static(tmp_path):
    with pytest.raises(ValueError, match='loop 仅对动画'):
        bar('t', CATS, VALS, out_dir=tmp_path, loop=True)


def test_loop_rejected_for_mp4(tmp_path):
    """MP4 循环由播放器决定,loop=True + fmt='mp4' 直接报错(无需 ffmpeg)。"""
    with pytest.raises(ValueError, match='loop 仅对 GIF'):
        bar('t', CATS, VALS, out_dir=tmp_path, animate=True, fmt='mp4', loop=True)


def test_mismatched_lengths():
    with pytest.raises(ValueError, match='长度一致'):
        bar('t', ['Q1', 'Q2'], [1, 2, 3])


def test_empty_series_rejected():
    with pytest.raises(ValueError, match='series 不能为空'):
        line_multi('t', CATS, [])


def test_scatter_xy_mismatch():
    with pytest.raises(ValueError, match='x 与 y'):
        scatter('t', [1, 2], [1, 2, 3])


def test_bubble_sizes_mismatch():
    with pytest.raises(ValueError, match='sizes'):
        bubble('t', [1, 2], [3, 4], [10])


def test_heatmap_shape_mismatch():
    with pytest.raises(ValueError, match='矩阵'):
        heatmap('t', ['r1', 'r2'], ['c1', 'c2'], [[1, 2, 3], [4, 5, 6]])


def test_box_empty_samples():
    with pytest.raises(ValueError, match='样本'):
        box('t', [('组A', [1, 2]), ('组B', [])])


def test_funnel_negative_rejected():
    with pytest.raises(ValueError, match='漏斗图'):
        funnel('t', ['a', 'b'], [10, -5])


def test_negative_values_rejected():
    """负值校验契约:柱类与饼类从 0 起画,负值会静默出错误图,必须报中文错误。"""
    with pytest.raises(ValueError, match='柱状图'):
        bar('t', ['a', 'b'], [120, -30])
    with pytest.raises(ValueError, match='柱状图'):
        bar('t', ['a', 'b'], [120, -30], horizontal=True)
    with pytest.raises(ValueError, match='饼图'):
        pie('t', ['a', 'b'], [120, -30])
    with pytest.raises(ValueError, match='环形图'):
        donut('t', ['a', 'b'], [120, -30])
    with pytest.raises(ValueError, match='多系列柱状图'):
        bar_multi('t', ['a', 'b'], [('销售额', [120, -30])])
    with pytest.raises(ValueError, match='combo'):
        combo('t', ['a', 'b'], [120, -30], [80, 140])
    with pytest.raises(ValueError, match='玫瑰图'):
        rose('t', ['a', 'b'], [120, -30])


def test_band_validation():
    """区间带校验契约:lower/upper 必须成对、与 values 等长且 upper >= lower。"""
    with pytest.raises(ValueError, match='同时给出'):
        line('t', ['a', 'b', 'c'], [1, 2, 3], lower=[0, 1, 2])
    with pytest.raises(ValueError, match='等长'):
        line('t', ['a', 'b', 'c'], [1, 2, 3], lower=[0, 1], upper=[2, 3, 4])
    with pytest.raises(ValueError, match='upper 需 >= lower'):
        line('t', ['a', 'b', 'c'], [1, 2, 3], lower=[2, 3, 4], upper=[0, 1, 2])


def test_gantt_and_dumbbell_validation():
    """甘特图起止校验;哑铃图恰好 2 个系列校验。"""
    with pytest.raises(ValueError, match='甘特图'):
        gantt('t', ['a', 'b'], [3, 1], [2, 4])
    with pytest.raises(ValueError, match='恰好 2 个系列'):
        dumbbell('t', ['a', 'b'], [('s1', [1, 2])])
    with pytest.raises(ValueError, match='恰好 2 个系列'):
        dumbbell('t', ['a', 'b'], [('s1', [1, 2]), ('s2', [3, 4]), ('s3', [5, 6])])


def test_line_band_and_dumbbell_slope(tmp_path):
    """区间带跟随折线渲染;哑铃图 slope=True 出坡度图。"""
    path, warns = _render(line, dict(categories=CATS, values=VALS,
                                     lower=[100, 180, 70, 140],
                                     upper=[140, 220, 110, 180]), tmp_path)
    _assert_ok(path, 'png', warns)
    path, warns = _render(dumbbell, dict(categories=CATS, series=SERIES, slope=True),
                          tmp_path)
    _assert_ok(path, 'png', warns)


def test_line_band_draws_polygon():
    """区间带必须真正画出半透明多边形(回归:CLI 曾不透传 --lower/--upper 而静默丢失)。"""
    from matplotlib.collections import PolyCollection
    fig, ax = plt.subplots()
    try:
        _line_draw('t', CATS, VALS, _theme('business'),
                   band=([100, 180, 70, 140], [140, 220, 110, 180]))(ax, 1.0)
        assert [c for c in ax.collections if isinstance(c, PolyCollection)], '区间带未渲染'
    finally:
        plt.close(fig)


def test_squarify_tiling():
    """squarify 必须铺满画布且面积正比于值(回归:归一化错误会让全部格子塌缩成细条)。"""
    from chartmove.graph.style import _squarify
    vals = [420, 300, 180, 100, 60]
    sizes = [v / sum(vals) * 16.0 * 9.0 for v in vals]
    rects = _squarify(sizes, 0.0, 0.0, 16.0, 9.0)
    assert len(rects) == len(vals)
    assert sum(w * h for _, _, w, h in rects) == pytest.approx(144.0)
    assert all(w > 0.3 and h > 0.3 for _, _, w, h in rects)  # 无塌缩细条
    with pytest.raises(ValueError, match='矩形树图'):
        treemap('t', ['a', 'b'], [120, -30])
    with pytest.raises(ValueError, match='需有正值'):
        treemap('t', ['a', 'b'], [0, 0])


def test_numfmt_chinese_units():
    """数值格式化:万/亿分级、负数、percent 追加、plain 原样。"""
    assert _nf(500, _theme('business')) == '500'
    assert _nf(12345, _theme('business')) == '1.2345万'
    assert _nf(123456789, _theme('business')) == '1.23457亿'
    assert _nf(-20000, _theme('business')) == '-2万'
    assert _nf(9999, _theme('business')) == '9999'  # 万级门槛以下原样
    assert _nf(6.1, _theme('business', 'percent')) == '6.1%'
    assert _nf(123456, _theme('business', 'plain')) == '123456'


def test_numfmt_and_note_render(tmp_path):
    """numfmt / note 端到端:大数值 + 脚注正常出图。"""
    big = dict(categories=CATS, values=[12345678, 23456789, 8901234, 45000000])
    path, warns = _render(bar, big, tmp_path, note='数据来源:单元测试')
    _assert_ok(path, 'png', warns)


def test_vfmt_ticks_on_value_axis():
    """刻度格式化落在数值轴:纵向柱 y 轴、横向柱 x 轴出现中文单位,类目轴不受影响。"""
    for horizontal, value_axis in ((False, 'y'), (True, 'x')):
        fig, ax = plt.subplots()
        try:
            draw = _bar_draw('t', ['甲', '乙'], [20000, 30000], _theme('business'), horizontal)
            draw(ax, 1.0)
            fig.canvas.draw()
            axis = ax.yaxis if value_axis == 'y' else ax.xaxis
            labels = [t.get_text() for t in axis.get_ticklabels()]
            assert any('万' in lb for lb in labels), (horizontal, labels)
        finally:
            plt.close(fig)


def test_nan_inf_rejected():
    """nan / inf 静默渲染会产出 'inf亿' 标签,校验层必须拦截。"""
    with pytest.raises(ValueError, match='nan'):
        bar('t', ['a', 'b'], [1, float('nan')])
    with pytest.raises(ValueError, match='inf'):
        scatter('t', [1, float('inf')], [1, 2])
    with pytest.raises(ValueError, match='nan'):
        box('t', [('组A', [1, float('nan')])])
    with pytest.raises(ValueError, match='nan'):
        heatmap('t', ['r'], ['c'], [[float('nan')]])
    with pytest.raises(ValueError, match='nan'):
        hist('t', [1, 2, float('nan')])
    with pytest.raises(ValueError, match='nan'):
        bubble('t', [1, 2], [3, 4], [1, float('nan')])


def test_same_name_not_overwritten(tmp_path):
    """同名产物自动加序号(_2),不覆盖已有文件。"""
    p1, _ = _render(bar, dict(SINGLE), tmp_path)
    p2, _ = _render(bar, dict(SINGLE), tmp_path)
    p3, _ = _render(bar, dict(SINGLE), tmp_path)
    assert p1.exists() and p2.exists() and p3.exists()
    assert p2.stem == p1.stem + '_2' and p3.stem == p1.stem + '_3'
    p1.unlink(), p2.unlink(), p3.unlink()


def test_same_name_not_overwritten_animated(tmp_path):
    """动画路径(GIF)的同名不覆盖。"""
    p1, _ = _render(bar, dict(SINGLE), tmp_path, animate=True, fmt='gif')
    p2, _ = _render(bar, dict(SINGLE), tmp_path, animate=True, fmt='gif')
    assert p1.exists() and p2.exists() and p2.stem == p1.stem + '_2'
    p1.unlink(), p2.unlink()


def test_mp4_missing_ffmpeg(monkeypatch, tmp_path):
    import chartmove.graph.render as render
    monkeypatch.setattr(render.shutil, 'which', lambda _: None)
    with pytest.raises(RuntimeError, match='ffmpeg'):
        bar('t', CATS, VALS, out_dir=tmp_path, animate=True, fmt='mp4')
