"""math 域科学绘图:连续数值轴基础设施 + 六种图(funcplot 函数图像 / polar 极坐标
曲线 / param 参数曲线·相轨线 / vector 矢量场·流线·方向场 / contour 等高线 /
surface 三维曲面)+ 表达式引擎(asteval 封装)。
与商务图域隔离:类目轴助手(_xticks/_ylim)不适用,本模块自备最小轴助手;
数据入口为数值序列/矩阵,文件列解析在入口层(cli / mcp_server)。"""
from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
from asteval import Interpreter
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.ticker import FuncFormatter, MultipleLocator

from ..render import _ease, _render, _stagger
from ..style import _theme
from ..validate import _lttb_indices

MAX_POINTS = 100_000   # 单曲线点数上限:文件数据与表达式采样共用这道闸


# ==================== 基础设施(M1) ====================

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
    等比例;轴过原点由 _origin_spines 在 xlim/ylim 定稿后单独调用。
    仅适用直角 2D 轴;polar / 3D 轴没有 left/bottom 脊线,各图自绘。"""
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


# ==================== 数据助手(M2 共用) ====================

def _limits(vals, pad: float = 0.08) -> tuple[float, float]:
    """数值轴范围:数据范围(忽略 nan)加对称边距;动画首帧即定稿,轴不跳动。"""
    finite = np.asarray(vals)[np.isfinite(vals)]
    if finite.size == 0:
        raise ValueError('数据不含有限数值(全为 nan 断点),无法确定坐标轴范围')
    lo, hi = float(finite.min()), float(finite.max())
    if lo == hi:
        lo, hi = lo - 1.0, hi + 1.0
    span = hi - lo
    return lo - pad * span, hi + pad * span


def _axis_vec(a, name: str) -> np.ndarray:
    """场坐标轴向量校验:至少 2 个点的一维有限数值序列(x/y 长度可不同,矩阵布局)。"""
    try:
        arr = np.asarray(a, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError(f'{name} 坐标需为数值序列') from e
    if arr.ndim != 1 or arr.size < 2:
        raise ValueError(f'{name} 坐标需为至少 2 个点的一维数值序列')
    if not np.isfinite(arr).all():
        raise ValueError(f'{name} 坐标含 nan / inf 等非法数值,请检查数据')
    return arr


def _to_grid(x, y, v, *, what='数值') -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """长表 → 规则网格:返回 (唯一 x, 唯一 y, 网格[行=y]);缺格或重复点报中文错。"""
    ux, uy = np.unique(x), np.unique(y)
    need = int(ux.size) * int(uy.size)
    if v.size != need:
        raise ValueError(f'{what}数据需为完整规则网格({ux.size}×{uy.size}={need} 个点),'
                         f'收到 {v.size} 个;请补全网格或改用矩阵布局')
    grid = np.full((uy.size, ux.size), np.nan)
    grid[np.searchsorted(uy, y), np.searchsorted(ux, x)] = v
    if np.isnan(grid).any():
        raise ValueError(f'{what}网格存在缺失或重复的坐标点,请检查数据')
    return ux, uy, grid


def _field_grid(x, y, z, *, what='z') -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """contour / surface 共用数据规范:(x, y 为 1D 轴向量,z 为 (len(y)×len(x)) 矩阵)
    或(x/y/z 等长长表,自动还原规则网格)。返回 (ux, uy, Z)。"""
    x, y = _axis_vec(x, 'x'), _axis_vec(y, 'y')
    try:
        Z = np.asarray(z, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError(f'{what} 需为数值矩阵或与 x/y 等长的数值序列') from e
    if Z.ndim == 1:
        if Z.size != x.size or Z.size != y.size:
            raise ValueError(f'长表布局需 x / y / {what} 三者等长,'
                             f'收到 x {x.size} / y {y.size} / {what} {Z.size} 个')
        if not np.isfinite(Z).all():
            raise ValueError(f'{what} 含 nan / inf 等非法数值,请检查数据')
        return _to_grid(x, y, Z, what=what)
    if Z.ndim == 2:
        if Z.shape != (y.size, x.size):
            raise ValueError(f'{what} 矩阵形状 {Z.shape} 需为 (len(y), len(x)) = '
                             f'({y.size}, {x.size})')
        if not np.isfinite(Z).all():
            raise ValueError(f'{what} 含 nan / inf 等非法数值,请检查数据')
        return x, y, Z
    raise ValueError(f'{what} 需为一维序列或二维矩阵,收到 {Z.ndim} 维')


def _cmap(th: dict) -> LinearSegmentedColormap:
    """主题色板 → 连续色图(等高线填充 / 3D 曲面着色)。"""
    return LinearSegmentedColormap.from_list('chartmove_math', th['palette'])


def _curve_sample(curves: list, sample: int | None) -> list:
    """各曲线 LTTB 降采样(保留索引取自 y,同步作用到 x;nan 以 0 参与仅用于选点)。"""
    if not sample:
        return curves
    out = []
    for nm, xs, ys in curves:
        keep = _lttb_indices(np.nan_to_num(ys, nan=0.0), sample)
        out.append((nm, xs[keep], ys[keep]))
    return out


# ==================== funcplot 函数图像 ====================

def _funcplot_draw(title, curves, th, pi_ticks, equal, grid):
    """绘制闭包:轴范围按全量数据定稿(动画轴不跳动),曲线按错峰进度渐进画出。"""
    all_x = np.concatenate([xs for _, xs, _ in curves])
    all_y = np.concatenate([ys for _, _, ys in curves])
    x0, x1 = _limits(all_x)
    y0, y1 = _limits(all_y)
    n = len(curves)

    def draw(ax, p):
        _math_style(ax, title, th, pi_ticks=pi_ticks, equal=equal, grid=grid)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        _origin_spines(ax)
        for i, (nm, xs, ys) in enumerate(curves):
            k = max(2, int(round(xs.size * _stagger(p, i, n))))
            ax.plot(xs[:k], ys[:k], lw=2.2, label=nm,
                    color=th['palette'][i % len(th['palette'])])
        if any(nm for nm, _, _ in curves):
            ax.legend(frameon=False, fontsize=13, labelcolor=th['text'])
    return draw


def funcplot(title, x=None, y=None, *, curves=None, name=None, style='business',
             pi_ticks=False, equal=False, grid=True, sample=None,
             animate=False, fmt=None, loop=False, out=None, out_dir=None,
             figsize=None, dpi=None, numfmt='plain', note=None) -> Path:
    """函数图像:连续数值轴上画 y=f(x) 采样点,按 x 升序连线,nan 断线分段。
    curves=[(曲线名, x, y), ...] 叠加多条曲线(主题色轮转);单条用 x/y(可选 name)。
    sample=LTTB 降采样目标点数(超长采样);pi_ticks=True 用 π/2 步进刻度。"""
    if curves is not None:
        if x is not None or y is not None:
            raise ValueError('x/y 与 curves 不能同时给,请二选一')
    else:
        if x is None or y is None:
            raise ValueError('funcplot 需要数据:x/y(单条)或 curves(多条)二选一')
        curves = [(name, x, y)]
    if not curves:
        raise ValueError('curves 不能为空')
    norm = []
    for i, item in enumerate(curves):
        try:
            nm, xs, ys = item
        except (TypeError, ValueError) as e:
            raise ValueError('curves 每项需为 (名称, x, y) 三元组') from e
        nm = str(nm)
        what = f'曲线「{nm}」' if nm else f'第 {i + 1} 条曲线'
        xs, ys = _validate_xy(xs, ys, allow_nan=True, sort_x=True, what=what)
        norm.append((nm, xs, ys))
    norm = _curve_sample(norm, sample)
    th = _theme(style, numfmt, note)
    return _render('funcplot', title, _funcplot_draw(title, norm, th, pi_ticks, equal, grid),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   figsize=figsize, dpi=dpi, th=th)


# ==================== polar 极坐标曲线 ====================

def _polar_draw(title, name, theta, r, th, fill, theta_pi):
    """极坐标绘制闭包:r 范围首帧固定;theta 刻度按 π/2 渲染分数标签。"""
    rmin, rmax = _limits(r)   # 全 nan 在此报中文错
    span = (rmax - rmin) or max(abs(rmax), 1.0)
    color = th['palette'][0]

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        ax.spines['polar'].set_color(th['axis'])
        ax.grid(color=th['grid_color'], linestyle=th['grid_ls'],
                linewidth=th['grid_lw'])
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=12, colors=th['text'])
        if theta_pi:
            _pi_axis(ax, axis='x')
        ax.set_ylim(rmin - 0.08 * span, rmax + 0.15 * span)
        k = max(2, int(round(theta.size * _ease(p))))
        ax.plot(theta[:k], r[:k], lw=2.2, color=color, label=name)
        if fill:
            ax.fill_between(theta[:k], 0, r[:k], color=color, alpha=0.22)
        if name:
            ax.legend(frameon=False, fontsize=13, labelcolor=th['text'],
                      loc='lower right')
    return draw


def polar(title, theta, r, *, name=None, fill=False, theta_pi=True,
          style='business', animate=False, fmt=None, loop=False, out=None,
          out_dir=None, figsize=None, dpi=None, numfmt='plain', note=None) -> Path:
    """极坐标曲线 r=r(θ):theta 为弧度、保持数据顺序(不排序,θ 的几何序不可重排);
    fill=True 填充曲线到圆心;theta_pi=False 关闭 θ 轴的 π 分数刻度。"""
    theta, r = _validate_xy(theta, r, allow_nan=True, what='极坐标数据')
    th = _theme(style, numfmt, note)
    return _render('polar', title, _polar_draw(title, name, theta, r, th, fill, theta_pi),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   polar=True, figsize=figsize, dpi=dpi, th=th)


# ==================== param 参数曲线 / 相轨线 ====================

def _param_draw(title, name, x, y, th, arrows, pi_ticks, grid, equal):
    """参数曲线绘制闭包:等比例坐标(轨迹形状不失真),可选沿轨迹方向箭头。"""
    x0, x1 = _limits(x)
    y0, y1 = _limits(y)

    def draw(ax, p):
        _math_style(ax, title, th, pi_ticks=pi_ticks, equal=equal, grid=grid)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        _origin_spines(ax)
        k = max(2, int(round(x.size * _ease(p))))
        ax.plot(x[:k], y[:k], lw=2.2, color=th['palette'][0], label=name)
        if arrows and p >= 1.0:
            valid = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
            m = min(12, max(3, valid.size // 30))
            for a in np.linspace(0, valid.size - 2, m).astype(int):
                i0, i1 = valid[a], valid[a + 1]
                if i1 == i0 + 1:   # 只在连续点间画箭头,跨 nan 断口不画
                    ax.annotate('', xy=(x[i1], y[i1]), xytext=(x[i0], y[i0]),
                                arrowprops=dict(arrowstyle='-|>', color=th['text'],
                                                lw=1.4, mutation_scale=14))
        if name:
            ax.legend(frameon=False, fontsize=13, labelcolor=th['text'])
    return draw


def param(title, x, y, *, name=None, arrows=False, equal=True, pi_ticks=False,
          grid=True, style='business', animate=False, fmt=None, loop=False,
          out=None, out_dir=None, figsize=None, dpi=None, numfmt='plain',
          note=None) -> Path:
    """参数曲线/相轨线:x(t)-y(t) 逐点连线,保持数据顺序(时间序即几何序,不排序);
    等比例坐标默认开启;arrows=True 在轨迹末端帧叠加方向箭头。"""
    x, y = _validate_xy(x, y, allow_nan=True, what='轨迹数据')
    th = _theme(style, numfmt, note)
    return _render('param', title,
                   _param_draw(title, name, x, y, th, arrows, pi_ticks, grid, equal),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   figsize=figsize, dpi=dpi, th=th)


# ==================== vector 矢量场 / 流线 / 方向场 ====================

def _vector_draw(title, mode, data, th, equal, grid, density, arrowsize):
    """场图绘制闭包:quiver/dir 吃长表,stream 吃规则网格;动画各帧相同。"""
    x0, x1 = _limits(data[0])
    y0, y1 = _limits(data[1])

    def draw(ax, p):
        _math_style(ax, title, th, equal=equal, grid=grid)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        _origin_spines(ax)
        color = th['palette'][0]
        if mode == 'stream':
            ax.streamplot(data[0], data[1], data[2], data[3], density=density,
                          arrowsize=arrowsize, color=color, linewidth=1.3)
        else:
            ax.quiver(data[0], data[1], data[2], data[3], color=color, width=0.0035)
    return draw


def vector(title, x, y, u, v, *, mode='quiver', density=1.0, arrowsize=1.0,
           equal=True, grid=True, style='business', animate=False, fmt=None,
           loop=False, out=None, out_dir=None, figsize=None, dpi=None,
           numfmt='plain', note=None) -> Path:
    """矢量场:x/y/u/v 等长数值长表;mode='quiver' 箭头场 / 'stream' 流线 /
    'dir' 方向场(分量归一化,只看方向)。stream 自动还原规则网格并要求等间距采样;
    场图无渐进语义,建议静态(animate=True 各帧相同)。"""
    if mode not in ('quiver', 'stream', 'dir'):
        raise ValueError(f"mode 仅支持 quiver / stream / dir,收到 {mode!r}")
    x, y = _validate_xy(x, y, what='场坐标')
    u, v = _validate_xy(u, v, what='场分量')
    if len(x) != len(u):
        raise ValueError(f'u/v({len(u)} 个)需与 x/y({len(x)} 个)等长')
    if mode == 'stream':
        ux, uy, ug = _to_grid(x, y, u, what='u 分量')
        _, _, vg = _to_grid(x, y, v, what='v 分量')
        if ux.size < 2 or uy.size < 2:
            raise ValueError('stream 模式网格需 x / y 方向各至少 2 个不同坐标')
        dx, dy = np.diff(ux), np.diff(uy)
        if not (np.allclose(dx, dx.mean(), rtol=1e-3, atol=0)
                and np.allclose(dy, dy.mean(), rtol=1e-3, atol=0)):
            raise ValueError('stream 模式需等间距采样网格:x / y 请均匀取点'
                             '(quiver / dir 模式无此要求)')
        data = (ux, uy, ug, vg)
    else:
        if mode == 'dir':
            norm = np.hypot(u, v)
            norm[norm == 0] = 1.0   # 零向量无方向,保持原样不放大
            u, v = u / norm, v / norm
        data = (x, y, u, v)
    th = _theme(style, numfmt, note)
    return _render('vector', title, _vector_draw(title, mode, data, th, equal, grid,
                                                 density, arrowsize),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   figsize=figsize, dpi=dpi, th=th)


# ==================== contour 等高线 ====================

def _contour_draw(title, X, Y, Z, th, filled, colorbar, levels, pi_ticks):
    """等高线绘制闭包:主题色板生成连续色图;叠加细线等高;色块按主题着色。"""
    cmap = _cmap(th)

    def draw(ax, p):
        _math_style(ax, title, th, pi_ticks=pi_ticks, grid=False)
        if filled:
            cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap)
            ax.contour(X, Y, Z, levels=levels, colors=th['text'],
                       linewidths=0.6, alpha=0.35)
        else:
            cf = ax.contour(X, Y, Z, levels=levels,
                            colors=th['palette'][0], linewidths=1.6)
        if colorbar:
            cbar = ax.figure.colorbar(cf, ax=ax)
            cbar.ax.tick_params(colors=th['text'])
            cbar.outline.set_edgecolor(th['axis'])
    return draw


def contour(title, x, y, z=None, *, filled=True, colorbar=True, levels=None,
            pi_ticks=False, style='business', animate=False, fmt=None, loop=False,
            out=None, out_dir=None, figsize=None, dpi=None, numfmt='plain',
            note=None) -> Path:
    """等高线图:(x, y 为 1D 轴向量,z 为 (len(y)×len(x)) 矩阵)或(x/y/z 等长长表,
    自动还原规则网格);filled=True 填充 + 细线叠加;levels 给级数(int)或分级列表。"""
    ux, uy, Z = _field_grid(x, y, z)
    X, Y = np.meshgrid(ux, uy)
    th = _theme(style, numfmt, note)
    return _render('contour', title, _contour_draw(title, X, Y, Z, th, filled,
                                                   colorbar, levels, pi_ticks),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   figsize=figsize, dpi=dpi, th=th)


# ==================== surface 三维曲面 ====================

def _surface_draw(title, X, Y, Z, th, colorbar, elev, azim):
    """3D 曲面绘制闭包:动画=相机环绕一周(azim 线性推进);底色面板随主题。"""
    cmap = _cmap(th)
    pane = to_rgba(th['face'])

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        ax.set_title(title, fontsize=18, pad=6, color=th['text'])
        ax.view_init(elev=elev, azim=azim + 360.0 * p)
        for axis_ in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis_.set_pane_color(pane)
        ax.tick_params(colors=th['text'])
        surf = ax.plot_surface(X, Y, Z, cmap=cmap, rcount=64, ccount=64,
                               linewidth=0, antialiased=True)
        if colorbar:
            cbar = ax.figure.colorbar(surf, ax=ax, shrink=0.7, pad=0.08)
            cbar.ax.tick_params(colors=th['text'])
            cbar.outline.set_edgecolor(th['axis'])
    return draw


def surface(title, x, y, z=None, *, colorbar=True, elev=28.0, azim=-60.0,
            style='business', animate=False, fmt=None, loop=False, out=None,
            out_dir=None, figsize=None, dpi=None, numfmt='plain',
            note=None) -> Path:
    """三维曲面 f(x,y):数据形式同 contour(矩阵或等长长表);动画=相机环绕一周
    出 GIF / MP4(elev 仰角、azim 起始方位角)。"""
    ux, uy, Z = _field_grid(x, y, z)
    X, Y = np.meshgrid(ux, uy)
    th = _theme(style, numfmt, note)
    return _render('surface', title, _surface_draw(title, X, Y, Z, th, colorbar,
                                                   elev, azim),
                   animate=animate, fmt=fmt, out=out, out_dir=out_dir, loop=loop,
                   projection='3d', figsize=figsize, dpi=dpi, th=th)


# ==================== 表达式引擎(M3:asteval 求值 + AST 资源闸) ====================
# 安全模型:asteval 挡注入(禁 import/属性/下标等),本节 AST 白名单挡资源失控
# (连续幂 / 大指数 / 非数学成分),双层各管一半;asteval 作者声明其防误用不防
# 蓄意攻击者,对本工具"用户想画图"的威胁模型足够。

_EXPR_FUNCS: dict[str, object] = {
    'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
    'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan, 'atan2': np.arctan2,
    'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
    'asinh': np.arcsinh, 'acosh': np.arccosh, 'atanh': np.arctanh,
    'exp': np.exp, 'expm1': np.expm1, 'log': np.log, 'log10': np.log10,
    'log2': np.log2, 'log1p': np.log1p, 'sqrt': np.sqrt, 'cbrt': np.cbrt,
    'abs': np.abs, 'sign': np.sign, 'floor': np.floor, 'ceil': np.ceil,
    'round': np.round, 'clip': np.clip, 'where': np.where,
    'minimum': np.minimum, 'maximum': np.maximum, 'hypot': np.hypot,
    'heaviside': np.heaviside, 'sinc': np.sinc,
    'deg2rad': np.deg2rad, 'rad2deg': np.rad2deg, 'mod': np.mod,
}
_EXPR_CONSTS: dict[str, float] = {'pi': math.pi, 'e': math.e, 'tau': math.tau,
                                  'inf': np.inf, 'nan': np.nan}
_OK_NODES = (ast.Expression, ast.Load, ast.BinOp, ast.UnaryOp, ast.USub, ast.UAdd,
             ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.Call,
             ast.Name, ast.Constant)


def _ast_gate(expr: str, variables: set[str]) -> None:
    """表达式 AST 白名单扫描:语法错误 / 非数学成分 / 连续幂 / 大指数报中文错。"""
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f'表达式语法错误:{expr!r}(第 {e.offset} 列附近)') from e
    called: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _OK_NODES):
            raise ValueError(f'表达式含不允许的成分({type(node).__name__});'
                             '只支持算术运算、白名单数学函数与数值常量')
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in _EXPR_FUNCS):
                bad = getattr(node.func, 'id', type(node.func).__name__)
                raise ValueError(f'表达式只允许调用白名单数学函数,收到:{bad!r}')
            if node.keywords:
                raise ValueError('表达式函数调用不接受关键字参数')
            called.add(node.func.id)
        elif isinstance(node, ast.BinOp):
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div,
                                        ast.Pow, ast.Mod)):
                raise ValueError('表达式只支持 + - * / % 与 ** 运算')
            if (isinstance(node.op, ast.Pow) and isinstance(node.right, ast.BinOp)
                    and isinstance(node.right.op, ast.Pow)):
                raise ValueError('不支持连续幂 a**b**c(易失控),请拆开写')
            if (isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant)
                    and abs(float(node.right.value)) > 100):
                raise ValueError('幂指数过大(上限 100)')
        elif isinstance(node, ast.UnaryOp) and not isinstance(node.op, (ast.USub, ast.UAdd)):
            raise ValueError('表达式一元运算只支持正负号')
        elif isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(f'表达式只允许数值常量,收到:{node.value!r}')
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or node.id in called:
            continue
        if node.id in variables or node.id in _EXPR_CONSTS:
            continue
        if node.id in _EXPR_FUNCS:
            raise ValueError(f'函数 {node.id!r} 需带括号调用,如 {node.id}(x)')
        raise ValueError(f'表达式含未知符号 {node.id!r};'
                         f'可用变量:{", ".join(sorted(variables))},'
                         f'常量:{" / ".join(_EXPR_CONSTS)},'
                         f'函数:{" / ".join(sorted(_EXPR_FUNCS))}')


def _interpreter(var_map: dict) -> Interpreter:
    """asteval 求值器:仅注入本次用到的变量 + 白名单函数与常量。"""
    aeval = Interpreter()
    aeval.symtable.update(var_map)
    aeval.symtable.update(_EXPR_FUNCS)
    aeval.symtable.update(_EXPR_CONSTS)
    return aeval


def _eval_expr(expr: str, var_map: dict[str, np.ndarray]) -> np.ndarray:
    """单表达式在变量上求值;标量结果广播到变量形状;异常统一转中文。"""
    expr = str(expr)
    _ast_gate(expr, set(var_map))
    aeval = _interpreter(var_map)
    try:
        with np.errstate(all='ignore'):
            out = aeval.eval(expr)
    except (OverflowError, ZeroDivisionError, ValueError, TypeError, NameError) as e:
        raise ValueError(f'表达式求值失败:{expr!r} —— {e}') from e
    if aeval.error:
        err = aeval.error[0]
        detail = err.getmsg() if hasattr(err, 'getmsg') else str(err)
        raise ValueError(f'表达式求值失败:{expr!r} —— {detail}')
    out = np.asarray(out, dtype=float)
    if out.ndim == 0:   # 常量表达式(如 "2")广播成常值曲线/平面
        ref = next(iter(var_map.values()))
        out = np.full(ref.shape, float(out))
    return out


def _check_samples(samples) -> int:
    """采样点数闸:2 ≤ samples ≤ MAX_POINTS。"""
    if not isinstance(samples, (int, np.integer)) or not 2 <= int(samples) <= MAX_POINTS:
        raise ValueError(f'采样点数 samples 需为 2 ~ {MAX_POINTS} 的整数,收到 {samples!r}')
    return int(samples)


def _check_grid(n) -> int:
    """二维场每轴点数闸:n ≥ 2 且 n² ≤ MAX_POINTS。"""
    if not isinstance(n, (int, np.integer)) or not 2 <= int(n) \
            or int(n) * int(n) > MAX_POINTS:
        raise ValueError(f'二维场每轴点数 n 需满足 2 ≤ n 且 n² ≤ {MAX_POINTS}'
                         f'(即 n ≤ {math.isqrt(MAX_POINTS)}),收到 {n!r}')
    return int(n)


def sample_curves(exprs, *, xmin, xmax, samples=400, var='x') -> list:
    """表达式或表达式列表 → [(表达式文本, xs, ys)]:在 [xmin, xmax] 均匀采样,
    每个表达式一条曲线,图例即表达式本身。"""
    if isinstance(exprs, (str, bytes)):   # 单表达式直传,防按字符迭代
        exprs = [exprs]
    lo, hi = _check_range(xmin, xmax)
    xs = np.linspace(lo, hi, _check_samples(samples))
    return [(str(e), xs, _eval_expr(e, {var: xs})) for e in exprs]


def sample_param(ex, ey, *, tmin, tmax, samples=400) -> tuple:
    """参数曲线表达式对 → (xs, ys):x(t)、y(t) 在 [tmin, tmax] 均匀采样。"""
    _check_range(tmin, tmax, what='t 范围')
    ts = np.linspace(tmin, tmax, _check_samples(samples))
    return _eval_expr(ex, {'t': ts}), _eval_expr(ey, {'t': ts})


def sample_field(expr, *, xmin, xmax, ymin, ymax, n=50) -> tuple:
    """二元表达式 f(x,y) → (x 轴向量, y 轴向量, 网格[n 行 y × n 列 x])。"""
    lo, hi = _check_range(xmin, xmax, what='x 范围')
    vlo, vhi = _check_range(ymin, ymax, what='y 范围')
    n = _check_grid(n)
    xs, ys = np.linspace(lo, hi, n), np.linspace(vlo, vhi, n)
    X, Y = np.meshgrid(xs, ys)
    return xs, ys, _eval_expr(expr, {'x': X, 'y': Y})


def sample_vector_field(eu, ev, *, xmin, xmax, ymin, ymax, n=20) -> tuple:
    """二元表达式对 (u, v) → 长表 (x, y, u, v),与 vector() 数据入口一致。"""
    xs, ys, U = sample_field(eu, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, n=n)
    _, _, V = sample_field(ev, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, n=n)
    X, Y = np.meshgrid(xs, ys)
    return X.ravel(), Y.ravel(), U.ravel(), V.ravel()
