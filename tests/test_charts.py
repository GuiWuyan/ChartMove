"""M1 冒烟测试:9 种图表类型 × PNG / GIF / MP4 全过(验收标准,docs/plan.md M1)。

另覆盖:pdf / tif 静态格式、8 主题、横向条形、figsize / dpi 参数、
中文缺字检测与校验错误。产物写入 pytest 临时目录,断言后即删。
"""
from __future__ import annotations

import shutil
import warnings
from pathlib import Path

import pytest
from PIL import Image

from chartgen import (
    THEMES,
    area,
    bar,
    bar_multi,
    box,
    bubble,
    combo,
    donut,
    fonts,
    funnel,
    heatmap,
    hist,
    line,
    line_multi,
    pie,
    radar,
    scatter,
    waterfall,
)
from chartgen.themes import THEME_DESCS, THEME_LABELS, THEME_PACKS

HAS_FFMPEG = shutil.which('ffmpeg') is not None

CATS = ['Q1', 'Q2', 'Q3', 'Q4']
VALS = [120, 200, 90, 160]
SERIES = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
XS = [1, 2, 3, 4, 5, 6]
YS = [120, 200, 90, 160, 210, 150]
MATRIX = [[3, 7, 2, 5], [8, 1, 6, 4], [2, 5, 9, 3], [6, 2, 4, 8]]

SINGLE = dict(categories=CATS, values=VALS)
CASES: dict[str, tuple] = {
    'bar': (bar, dict(SINGLE)),
    'line': (line, dict(SINGLE)),
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


@pytest.mark.parametrize('fmt', ['png', 'gif', 'mp4'])
@pytest.mark.parametrize('name', list(CASES))
def test_matrix(name, fmt, tmp_path):
    """验收主体:9 种类型 × 3 种输出。"""
    if fmt == 'mp4' and not HAS_FFMPEG:
        pytest.skip('未安装 ffmpeg,跳过 MP4')
    fn, kw = CASES[name]
    path, warns = _render(fn, kw, tmp_path, animate=fmt in ('gif', 'mp4'), fmt=fmt)
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


def test_theme_metadata():
    """13 主题分 4 包;每个主题都有中文名与一句话描述,包成员无遗漏无重复。"""
    assert len(THEMES) == 13
    assert sorted(THEME_PACKS) == ['其他风格包', '商务包', '学术包', '简约演示包']
    packed = [k for members in THEME_PACKS.values() for k in members]
    assert sorted(packed) == sorted(THEMES)
    assert set(THEME_LABELS) == set(THEMES) and set(THEME_DESCS) == set(THEMES)


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


def test_mp4_missing_ffmpeg(monkeypatch, tmp_path):
    import chartgen.core as core
    monkeypatch.setattr(core.shutil, 'which', lambda _: None)
    with pytest.raises(RuntimeError, match='ffmpeg'):
        bar('t', CATS, VALS, out_dir=tmp_path, animate=True, fmt='mp4')
