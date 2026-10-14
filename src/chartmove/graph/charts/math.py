"""math 域科学绘图:连续数值轴基础设施 + 六种图(funcplot 函数图像 / polar 极坐标
曲线 / param 参数曲线·相轨线 / vector 矢量场·流线·方向场 / contour 等高线 /
surface 三维曲面,逐型落地)。
与商务图域隔离:类目轴助手(_xticks/_ylim)不适用,本模块自备最小轴助手。"""
from __future__ import annotations

import math

import numpy as np
from matplotlib.ticker import FuncFormatter, MultipleLocator

MAX_POINTS = 100_000   # 单曲线点数上限:文件数据与表达式采样共用这道闸


def _check_range(lo, hi, *, what='范围', log=False) -> tuple[float, float]:
    """采样/表达式范围校验:两端有限且下界 < 上界;log 轴额外要求全为正。"""
    try:
        lo, hi = float(lo), float(hi)
    except (TypeError, ValueError) as e:
        raise ValueError(f'{what}端点需为数值,收到 {lo!r} / {hi!r}') from e
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ValueError(f'{what}端点需为有限数值')
    if not lo < hi:
        raise ValueError(f'{what}需下界 < 上界,收到 [{lo}, {hi}]')
    if log and lo <= 0:
        raise ValueError(f'对数轴的{what}需全为正数,收到 [{lo}, {hi}]')
    return lo, hi


def _validate_xy(xs, ys, *, allow_nan=False, sort_x=False,
                 what='数据') -> tuple[np.ndarray, np.ndarray]:
    """数值对校验:非空等长一维、点数封顶 MAX_POINTS、有限性(allow_nan=True 时
    nan 作分段断点放行,inf 仍拒);sort_x=True 按 x 升序排序(funcplot 函数图像),
    False 保持数据顺序(param 相轨线:时间序即几何序,不得重排)。"""
    try:
        x = np.asarray(xs, dtype=float)
        y = np.asarray(ys, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError(f'{what}需为数值序列') from e
    if x.ndim != 1 or y.ndim != 1 or x.size == 0 or x.size != y.size:
        raise ValueError(f'{what}的 x 与 y 必须是非空且等长的一维数值序列')
    if x.size > MAX_POINTS:
        raise ValueError(f'{what}共 {x.size} 个点,超过上限 {MAX_POINTS},请先降采样')
    if allow_nan:
        if np.isinf(x).any() or np.isinf(y).any():
            raise ValueError(f'{what}含 inf(仅允许 nan 作分段断点),请检查数据')
    elif not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError(f'{what}含 nan / inf 等非法数值,请检查数据')
    if sort_x:
        order = np.argsort(x)   # nan 排到末尾,断点自然落在曲线末端
        x, y = x[order], y[order]
    return x, y


def _pi_label(m: int, n: int = 2) -> str:
    """mπ/n 的紧凑写法:约分、省略系数 1、分母 1 省略;0 → '0'。"""
    if m == 0:
        return '0'
    g = math.gcd(abs(m), n)
    m, n = m // g, n // g
    sign, m = ('-' if m < 0 else ''), abs(m)
    coef = '' if m == 1 else str(m)
    return f'{sign}{coef}π/{n}' if n != 1 else f'{sign}{coef}π'


def _pi_axis(ax, axis: str = 'both', denom: int = 2) -> None:
    """刻度按 π/denom 步进,标签渲染为 π 分数(数学坐标轴惯例)。"""
    for name in (('x', 'y') if axis == 'both' else (axis,)):
        ax_ = ax.xaxis if name == 'x' else ax.yaxis
        ax_.set_major_locator(MultipleLocator(math.pi / denom))
        ax_.set_major_formatter(FuncFormatter(
            lambda v, _, _n=denom: _pi_label(round(v * _n / math.pi), _n)))


def _math_style(ax, title: str, th: dict, *, pi_ticks: bool = False,
                equal: bool = False, grid: bool = True) -> None:
    """math 域统一轴外观:藏顶右脊线、标题/刻度/网格按主题着色,可选 π 刻度与
    等比例;轴过原点由 _origin_spines 在 xlim/ylim 定稿后单独调用。"""
    ax.set_title(title, fontsize=20, pad=18, color=th['text'])
    ax.set_facecolor(th['face'])
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(th['axis'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if grid:
        ax.grid(color=th['grid_color'], linestyle=th['grid_ls'],
                linewidth=th['grid_lw'])
        ax.set_axisbelow(True)
    ax.tick_params(labelsize=13, colors=th['text'])
    if pi_ticks:
        _pi_axis(ax)
    if equal:
        ax.set_aspect('equal', adjustable='box')


def _origin_spines(ax) -> None:
    """轴过原点:0 在轴范围内时脊线移到 0 位置,否则贴边
    (需在 set_xlim/set_ylim 之后调用)。"""
    if ax.get_xlim()[0] <= 0 <= ax.get_xlim()[1]:
        ax.spines['bottom'].set_position('zero')
    if ax.get_ylim()[0] <= 0 <= ax.get_ylim()[1]:
        ax.spines['left'].set_position('zero')
