"""math 域 M1 基础设施:数值校验(等长/有限性/点数上限/排序策略)、π 刻度、
原点脊线、render 的 projection 钩子(3D 静态 + 动画冒烟);产物即测即删。"""
from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.ticker import MultipleLocator

from chartmove import cli, contour, funcplot, param, polar, surface, vector
from chartmove.graph.charts.math import (
    MAX_POINTS,
    _check_range,
    _math_style,
    _origin_spines,
    _pi_axis,
    _pi_label,
    _validate_xy,
    sample_curves,
    sample_field,
    sample_param,
    sample_vector_field,
)
from chartmove.graph.render import _render
from chartmove.themes import THEMES

# ---- _validate_xy:等长 / 有限性 / 点数上限 / 排序策略 ----

def test_xy_rejects_uneven_lengths():
    with pytest.raises(ValueError, match='等长'):
        _validate_xy([1, 2, 3], [1, 2])


def test_xy_rejects_non_numeric():
    with pytest.raises(ValueError, match='数值序列'):
        _validate_xy(['a', 'b'], [1, 2])


def test_xy_rejects_nan_by_default():
    with pytest.raises(ValueError, match='非法数值'):
        _validate_xy([0, float('nan')], [0, 1])


def test_xy_allow_nan_keeps_nan_rejects_inf():
    x, y = _validate_xy([0, 1, 2], [0, float('nan'), 2], allow_nan=True)
    assert np.isnan(y[1]) and np.isfinite(x).all()
    with pytest.raises(ValueError, match='inf'):
        _validate_xy([0, 1], [0, float('inf')], allow_nan=True)


def test_xy_points_capped():
    n = MAX_POINTS + 1
    with pytest.raises(ValueError, match='上限'):
        _validate_xy(range(n), range(n))


def test_xy_sort_x_vs_order_preserved():
    _, y_sorted = _validate_xy([3, 1, 2], [30, 10, 20], sort_x=True)
    assert list(y_sorted) == [10, 20, 30]          # funcplot:x 升序连线
    x_raw, _ = _validate_xy([3, 1, 2], [30, 10, 20])
    assert list(x_raw) == [3, 1, 2]                # 相轨线:数据顺序即几何序,不动


# ---- _check_range:范围与对数轴 ----

def test_range_rejects_reversed_nonfinite_and_nonpositive_log():
    with pytest.raises(ValueError, match='下界'):
        _check_range(1, -1)
    with pytest.raises(ValueError, match='有限'):
        _check_range(0, math.inf)
    with pytest.raises(ValueError, match='正数'):
        _check_range(-1, 1, log=True)
    with pytest.raises(ValueError, match='数值'):
        _check_range('a', 1)
    assert _check_range(-math.pi, math.pi) == (-math.pi, math.pi)


# ---- π 刻度:标签约分与轴挂载 ----

@pytest.mark.parametrize('m,n,expect', [
    (0, 2, '0'), (1, 2, 'π/2'), (2, 2, 'π'), (3, 2, '3π/2'), (4, 2, '2π'),
    (-1, 2, '-π/2'), (2, 3, '2π/3'), (-4, 3, '-4π/3'), (5, 1, '5π'),
])
def test_pi_label(m, n, expect):
    assert _pi_label(m, n) == expect


def test_pi_axis_locator_and_labels():
    fig, ax = plt.subplots()
    try:
        ax.set_xlim(-math.pi, math.pi)
        _pi_axis(ax, axis='x')
        assert isinstance(ax.xaxis.get_major_locator(), MultipleLocator)
        fig.canvas.draw()
        texts = {t.get_text() for t in ax.get_xticklabels()}
        assert {'-π', '-π/2', '0', 'π/2', 'π'} <= texts
    finally:
        plt.close(fig)


# ---- 轴外观与原点脊线 ----

def test_math_style_theme_colors_and_equal_aspect():
    th = dict(THEMES['academic'], palette=list(THEMES['academic']['palette']))
    fig, ax = plt.subplots()
    try:
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        _math_style(ax, '测试标题', th, equal=True, pi_ticks=True)
        assert ax.get_aspect() == 1.0
        assert not ax.spines['top'].get_visible()
        assert not ax.spines['right'].get_visible()
        assert ax.get_title() == '测试标题'
    finally:
        plt.close(fig)


def test_origin_spines_follow_limits():
    fig, ax = plt.subplots()
    try:
        ax.set_xlim(-2, 2)
        ax.set_ylim(1, 5)          # y 范围不含 0:left 脊线保持贴边
        _origin_spines(ax)
        assert ax.spines['bottom'].get_position() in ('zero', ('data', 0))
        assert ax.spines['left'].get_position() not in ('zero', ('data', 0))
        ax.set_ylim(-3, 3)
        _origin_spines(ax)
        assert ax.spines['left'].get_position() in ('zero', ('data', 0))
    finally:
        plt.close(fig)


# ---- render projection 钩子:3D 静态 + 动画 ----

def test_render_projection_3d_static(tmp_path):
    seen = {}

    def draw(ax, p):
        seen['name'] = ax.name
        ax.plot([0, 1], [0, 1], [0, p])

    path = _render('3d冒烟', '三维曲线', draw, animate=False, fmt='png',
                   out='m1_3d', out_dir=tmp_path, projection='3d', th={})
    assert path.exists() and seen['name'] == '3d'
    path.unlink()


def test_render_projection_3d_animated_gif(tmp_path):
    seen = {}

    def draw(ax, p):
        seen['name'] = ax.name
        ax.plot([0, 1], [0, 1], [0, p])

    path = _render('3d动画冒烟', '三维环绕', draw, animate=True, fmt='gif',
                   out='m1_3d_anim', out_dir=tmp_path, projection='3d', th={})
    assert path.exists() and seen['name'] == '3d'
    path.unlink()


# ==================== M2:六种图渲染冒烟(产物即测即删) ====================

def test_funcplot_static_sorts_and_nan_gaps(tmp_path):
    x = [3.0, 1.0, 2.0, float('nan'), 4.5]   # 乱序 + nan 断点
    y = [9, 1, 4, 2.0, 20]
    path = funcplot('函数图像', x, y, out='m2_func', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_funcplot_multi_curves_with_pi_ticks(tmp_path):
    xs = np.linspace(-math.pi, math.pi, 200)
    path = funcplot('三角函数', curves=[('sin', xs, np.sin(xs)), ('cos', xs, np.cos(xs))],
                    pi_ticks=True, out='m2_func2', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_funcplot_rejects_conflicting_input():
    with pytest.raises(ValueError, match='不能同时'):
        funcplot('t', [1, 2], [1, 2], curves=[('a', [1], [1])])
    with pytest.raises(ValueError, match='二选一'):
        funcplot('t')


def test_funcplot_animated_gif(tmp_path):
    xs = np.linspace(0, 2 * math.pi, 100)
    path = funcplot('正弦生长', xs, np.sin(xs), animate=True, fmt='gif',
                    out='m2_func_gif', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_polar_static_fill_and_animated(tmp_path):
    t = np.linspace(0, 4 * math.pi, 400)
    r = np.sin(2 * t)                        # 含负 r
    path = polar('玫瑰线', t, r, fill=True, out='m2_polar', out_dir=tmp_path)
    assert path.exists()
    path.unlink()
    path = polar('玫瑰线动画', t, r, animate=True, fmt='gif',
                 out='m2_polar_gif', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_param_static_with_arrows(tmp_path):
    t = np.linspace(0, 2 * math.pi, 200)
    path = param('单位圆轨迹', np.cos(t), np.sin(t), arrows=True,
                 out='m2_param', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_vector_three_modes(tmp_path):
    n = 10
    xs = np.linspace(-2.0, 2.0, n)
    X, Y = np.meshgrid(xs, xs)
    x, y = X.ravel(), Y.ravel()
    u, v = np.sin(Y).ravel(), np.cos(X).ravel()
    for mode in ('quiver', 'dir', 'stream'):
        path = vector('向量场', x, y, u, v, mode=mode,
                      out=f'm2_vec_{mode}', out_dir=tmp_path)
        assert path.exists()
        path.unlink()


def test_vector_stream_rejects_uneven_grid():
    xs = np.array([0.0, 0.1, 0.5, 2.0])      # 等格数但不等间距
    X, Y = np.meshgrid(xs, xs)
    x, y = X.ravel(), Y.ravel()
    with pytest.raises(ValueError, match='等间距'):
        vector('场', x, y, np.ones_like(x), np.zeros_like(x), mode='stream')


def test_vector_stream_rejects_incomplete_grid():
    with pytest.raises(ValueError, match='规则网格'):
        vector('场', [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1, 1, 1], [0, 0, 0],
               mode='stream')


def test_vector_mode_validated():
    with pytest.raises(ValueError, match='mode'):
        vector('场', [0, 1], [0, 1], [1, 1], [0, 0], mode='bad')


def test_contour_matrix_long_form_and_dark_theme(tmp_path):
    xs = np.linspace(-2, 2, 30)
    X, Y = np.meshgrid(xs, xs)
    Z = np.sin(X) * np.cos(Y)
    path = contour('波场矩阵', xs, xs, Z, out='m2_contour', out_dir=tmp_path)
    assert path.exists()
    path.unlink()
    path = contour('波场长表', X.ravel(), Y.ravel(), Z.ravel(), style='terminal',
                   out='m2_contour_long', out_dir=tmp_path)   # 暗色主题过色板/色带着色
    assert path.exists()
    path.unlink()


def test_contour_rejects_shape_mismatch():
    with pytest.raises(ValueError, match='形状'):
        contour('bad', [0, 1, 2], [0, 1], [[1, 2]])


def test_surface_static(tmp_path):
    xs = np.linspace(-2, 2, 40)
    X, Y = np.meshgrid(xs, xs)
    path = surface('鞍面', xs, xs, np.sin(X) * np.cos(Y), out='m2_surf', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


def test_surface_orbit_gif(tmp_path):
    xs = np.linspace(-2, 2, 40)
    X, Y = np.meshgrid(xs, xs)
    path = surface('鞍面环绕', xs, xs, np.sin(X) * np.cos(Y), animate=True, fmt='gif',
                   out='m2_surf_gif', out_dir=tmp_path)
    assert path.exists()
    path.unlink()


# ==================== M4:CLI 入口接线(文件/内联双入口) ====================

def _csv(tmp_path, text, name='d.csv'):
    p = tmp_path / name
    p.write_text(text, encoding='utf-8')
    return str(p)


def test_cli_funcplot_inline_and_piticks(tmp_path):
    assert cli.main(['funcplot', '正弦', '--x', '0,0.5,1', '--y', '0,1,0',
                     '--pi-ticks', '--out-dir', str(tmp_path), '--out', 'm4_f']) == 0
    assert (tmp_path / 'm4_f.png').exists()


def test_cli_polar_inline(tmp_path):
    assert cli.main(['polar', '玫瑰', '--x', '0,0.79,1.57', '--y', '0,1,0',
                     '--fill', '--out-dir', str(tmp_path), '--out', 'm4_p']) == 0
    assert (tmp_path / 'm4_p.png').exists()


def test_cli_param_file_three_columns(tmp_path):
    f = _csv(tmp_path, 't,x,y\n0,1,0\n1,0.54,0.84\n2,0,1\n')
    assert cli.main(['param', '相轨线', '--file', f, '--arrows',
                     '--out-dir', str(tmp_path), '--out', 'm4_param']) == 0
    assert (tmp_path / 'm4_param.png').exists()


def test_cli_vector_file_stream(tmp_path):
    rows = ['x,y,u,v']
    for i in range(4):
        for j in range(4):
            x, y = -1.5 + i, -1.5 + j
            rows.append(f'{x},{y},{-y},{x}')
    f = _csv(tmp_path, '\n'.join(rows) + '\n', name='field.csv')
    assert cli.main(['vector', '流线', '--file', f, '--mode', 'stream',
                     '--out-dir', str(tmp_path), '--out', 'm4_v']) == 0
    assert (tmp_path / 'm4_v.png').exists()


def test_cli_vector_stream_uneven_grid_fails(tmp_path):
    f = _csv(tmp_path, 'x,y,u,v\n0,0,0,1\n0.1,0,0,1\n0.5,0,0,1\n2,0,0,1\n')
    assert cli.main(['vector', '场', '--file', f, '--mode', 'stream',
                     '--out-dir', str(tmp_path)]) == 1


def test_cli_contour_matrix_file(tmp_path):
    f = _csv(tmp_path, ',0,1,2\n0,0,0,0\n1,0,1,2\n2,0,2,4\n', name='grid.csv')
    assert cli.main(['contour', 'z=xy', '--file', f,
                     '--out-dir', str(tmp_path), '--out', 'm4_c']) == 0
    assert (tmp_path / 'm4_c.png').exists()


def test_cli_surface_long_file(tmp_path):
    f = _csv(tmp_path, 'x,y,z\n0,0,0\n1,0,0\n0,1,0\n1,1,1\n')
    assert cli.main(['surface', '曲面', '--file', f, '--long',
                     '--out-dir', str(tmp_path), '--out', 'm4_s']) == 0
    assert (tmp_path / 'm4_s.png').exists()


def test_cli_funcplot_batch_multi_files(tmp_path):
    _csv(tmp_path, 'x,y\n0,0\n1,1\n2,4\n', name='a.csv')
    _csv(tmp_path, 'x,y\n0,1\n1,0\n2,1\n', name='b.csv')
    out = tmp_path / 'batch'
    assert cli.main(['batch', 'funcplot', str(tmp_path / '*.csv'),
                     '--title', '{name}曲线', '--out-dir', str(out)]) == 0
    names = {p.name for p in out.glob('*.png')}
    assert any('a' in n for n in names) and any('b' in n for n in names)


# ==================== M3:表达式引擎(asteval + AST 资源闸) ====================

def test_sample_curves_values_and_labels():
    curves = sample_curves(['sin(x)', '2'], xmin=0.0, xmax=math.pi, samples=5)
    xs = np.linspace(0.0, math.pi, 5)
    assert curves[0][0] == 'sin(x)'                      # 图例 = 表达式本身
    assert np.allclose(curves[0][2], np.sin(xs))
    assert np.allclose(curves[1][2], 2.0)                # 常量表达式广播成常值曲线


def test_sample_param_and_field():
    ts, ys = sample_param('t', 't ** 2', tmin=0.0, tmax=2.0, samples=3)
    assert np.allclose(ts, [0, 1, 2]) or np.allclose(ys, [0, 1, 4])
    xs, grid_y, zs = sample_field('sin(x) * cos(y)', xmin=-1.0, xmax=1.0,
                                  ymin=-1.0, ymax=1.0, n=6)
    assert zs.shape == (6, 6) and len(xs) == len(grid_y) == 6
    gx, gy, us, vs = sample_vector_field('-y', 'x', xmin=-2.0, xmax=2.0,
                                         ymin=-2.0, ymax=2.0, n=4)
    assert len(gx) == len(gy) == len(us) == len(vs) == 16   # 长表形式
    assert np.allclose(us, -gy) and np.allclose(vs, gx)


def test_sample_range_and_samples_gates():
    with pytest.raises(ValueError, match='下界'):
        sample_curves(['x'], xmin=1, xmax=-1)
    with pytest.raises(ValueError, match='采样点数'):
        sample_curves(['x'], xmin=0, xmax=1, samples=MAX_POINTS + 1)


@pytest.mark.parametrize('bad', [
    "__import__('os')",          # 非白名单函数
    '().__class__',              # 属性访问
    'lambda: 1',                 # lambda
    '9**9**9',                   # 连续幂(资源闸)
    '2**999',                    # 大指数(资源闸)
    'x = 1',                     # 语句不是表达式
    'sin(1);cos(1)',             # 多语句
    'y + 1',                     # 未知符号(变量只有 x)
    'sin + 1',                   # 函数未带括号调用
    "[1, 2, 3]",                 # 列表字面量
])
def test_expression_gate_rejects_unsafe(bad):
    with pytest.raises(ValueError):
        sample_curves([bad], xmin=0, xmax=1)


def test_expression_gate_known_symbols_accepted():
    curves = sample_curves(['sin(pi * x) + e ** (-x)'], xmin=0.0, xmax=1.0,
                           samples=4)
    assert np.all(np.isfinite(curves[0][2]))


def test_expression_chinese_error_messages():
    with pytest.raises(ValueError, match='语法错误'):
        sample_curves(['sin('], xmin=0, xmax=1)
    with pytest.raises(ValueError, match='白名单'):
        sample_curves(['foo(x)'], xmin=0, xmax=1)
    with pytest.raises(ValueError, match='未知符号'):
        sample_curves(['foo + 1'], xmin=0, xmax=1)


# ==================== M3:CLI / MCP 表达式入口 ====================

def test_cli_funcplot_expression(tmp_path):
    assert cli.main(['funcplot', '正弦', 'sin(x)', 'cos(x)',
                     '--xmin', '-6.28', '--xmax', '6.28', '--pi-ticks',
                     '--out-dir', str(tmp_path), '--out', 'm3_f']) == 0
    assert (tmp_path / 'm3_f.png').exists()


def test_cli_polar_expression_default_range(tmp_path):
    assert cli.main(['polar', '三叶玫瑰', 'cos(3 * theta)',
                     '--out-dir', str(tmp_path), '--out', 'm3_p']) == 0
    assert (tmp_path / 'm3_p.png').exists()


def test_cli_param_expression(tmp_path):
    assert cli.main(['param', '利萨如', 'sin(3 * t)', 'sin(4 * t)',
                     '--xmin', '0', '--xmax', '6.28', '--samples', '600',
                     '--arrows', '--out-dir', str(tmp_path), '--out', 'm3_pa']) == 0
    assert (tmp_path / 'm3_pa.png').exists()


def test_cli_vector_expression_stream(tmp_path):
    # 表达式以 - 开头时,选项须写在前面并用 "--" 分隔(argparse 规则)
    assert cli.main(['vector', '旋转场', '--mode', 'stream',
                     '--xmin', '-2', '--xmax', '2', '--ymin', '-2', '--ymax', '2',
                     '--out-dir', str(tmp_path), '--out', 'm3_v',
                     '--', '-y', 'x']) == 0
    assert (tmp_path / 'm3_v.png').exists()


def test_cli_contour_expression(tmp_path):
    assert cli.main(['contour', '波场', 'sin(x) * cos(y)',
                     '--xmin', '-3', '--xmax', '3', '--ymin', '-3', '--ymax', '3',
                     '--out-dir', str(tmp_path), '--out', 'm3_c']) == 0
    assert (tmp_path / 'm3_c.png').exists()


def test_cli_surface_expression(tmp_path):
    assert cli.main(['surface', '波面', 'sin(x) * cos(y)',
                     '--xmin', '-3', '--xmax', '3', '--ymin', '-3', '--ymax', '3',
                     '--out-dir', str(tmp_path), '--out', 'm3_s']) == 0
    assert (tmp_path / 'm3_s.png').exists()


def test_cli_expression_conflicts_rejected(tmp_path):
    # 表达式与 --x/--y 内联互斥
    assert cli.main(['funcplot', 't', 'sin(x)', '--x', '0,1', '--y', '0,1',
                     '--xmin', '0', '--xmax', '1',
                     '--out-dir', str(tmp_path)]) == 1
    # 缺范围
    assert cli.main(['funcplot', 't', 'sin(x)',
                     '--out-dir', str(tmp_path)]) == 1
    # vector 表达式需要恰好 2 个
    assert cli.main(['vector', 't', 'x', '--xmin', '0', '--xmax', '1',
                     '--ymin', '0', '--ymax', '1',
                     '--out-dir', str(tmp_path)]) == 1
