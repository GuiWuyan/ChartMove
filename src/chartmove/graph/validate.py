"""纯数据校验与降采样:错误消息一律中文,禁止 import matplotlib。"""
from __future__ import annotations

import math

import numpy as np


def _check_finite(vals, what: str = 'values') -> None:
    """拒绝 nan / inf:静默渲染会产出 'nan' / 'inf亿' 标签。"""
    if any(not math.isfinite(v) for v in vals):
        raise ValueError(f'{what} 含 nan / inf 等非法数值,请检查数据')


def _validate(categories, values) -> tuple[list, list]:
    """非空、等长、可转 float、无 nan/inf。"""
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
    """x/y 均为数值、非空且等长。"""
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    if not x or len(x) != len(y):
        raise ValueError('x 与 y 必须非空且长度一致')
    _check_finite(x, 'x')
    _check_finite(y, 'y')
    return x, y


def _validate_labels(labels, n: int) -> list[str] | None:
    """逐点标注与数据等长;未给返回 None。"""
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
    """values 必须是 (行数 × 列数) 的二维有限数值矩阵。"""
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


def _validate_hierarchy(hierarchy) -> list[tuple[str, list[tuple[str, float]]]]:
    """旭日图层级数据规范:{父类目: {子类目: 数值}}(或对应列表形式),父值 = 子值合计。"""
    items = hierarchy.items() if isinstance(hierarchy, dict) else hierarchy
    out = []
    for item in items:
        try:
            pname, kids = item
        except (TypeError, ValueError) as e:
            raise ValueError('hierarchy 需为 {父类目: {子类目: 数值}} '
                             '或 [[父类目, {子类目: 数值}], ...]') from e
        if isinstance(kids, dict):
            kids = list(kids.items())
        if not kids:
            raise ValueError(f'父类目「{pname}」至少需要 1 个子类目')
        kk = []
        for kv in kids:
            try:
                cname, v = kv
            except (TypeError, ValueError) as e:
                raise ValueError(f'父类目「{pname}」的子类目需为 {{子类目: 数值}} '
                                 '或 [[子类目, 数值], ...]') from e
            fv = float(v)
            if not math.isfinite(fv):
                raise ValueError('hierarchy 含 nan / inf 等非法数值,请检查数据')
            if fv < 0:
                raise ValueError('旭日图数值需 >=0(扇区面积即占比),请检查数据')
            kk.append((str(cname), fv))
        out.append((str(pname), kk))
    if not out:
        raise ValueError('hierarchy 不能为空')
    if sum(v for _, kids in out for _, v in kids) <= 0:
        raise ValueError('旭日图 hierarchy 需有正值(扇区面积即占比)')
    return out


def _validate_links(links) -> list[tuple[str, str, float]]:
    """桑基图 links=[[源, 目标, 数值], ...],每项也接受 {source, target, value} 字典。"""
    try:
        items = list(links)
    except TypeError as e:
        raise ValueError('links 需为 [[源, 目标, 数值], ...] 列表') from e
    out = []
    for item in items:
        try:
            if isinstance(item, dict):
                src, tgt = item['source'], item['target']
                fv = float(item['value'])
            else:
                src, tgt, v = item
                fv = float(v)
        except (TypeError, ValueError, KeyError) as e:
            raise ValueError('links 每项需为 [源, 目标, 数值] 或 '
                             '{source, target, value} 字典') from e
        if not math.isfinite(fv):
            raise ValueError('links 含 nan / inf 等非法数值,请检查数据')
        if fv <= 0:
            raise ValueError('桑基图 links 的流量值需 > 0')
        out.append((str(src), str(tgt), fv))
    if not out:
        raise ValueError('links 不能为空')
    return out


def _lttb_indices(ys, target: int) -> list[int]:
    """LTTB 降采样保留索引:保首尾与尖峰,抽到 ~target 个点。"""
    n = len(ys)
    if target >= n or target < 3:
        return list(range(n))
    ys_ = np.asarray(ys, dtype=float)
    keep, a = [0], 0
    step = (n - 2) / (target - 2)
    for i in range(1, target - 1):
        s, e = int((i - 1) * step) + 1, int(i * step) + 1      # 候选桶 [s, e)
        ns, ne = e, int((i + 1) * step) + 1                    # 下一桶取均值作参照
        avg_x, avg_y = (ns + ne - 1) / 2, float(ys_[ns:ne].mean())
        xs = np.arange(s, e)
        area = np.abs((avg_x - a) * (ys_[s:e] - ys_[a]) - (xs - a) * (avg_y - ys_[a]))
        a = s + int(np.argmax(area))
        keep.append(a)
    keep.append(n - 1)
    return keep


def _downsample(cats: list[str], sample: int | None,
                series: list[list[float]]) -> tuple[list[str], list[list[float]]]:
    """多系列 LTTB 降采样:取各系列保留索引并集并同步截取;sample 无效时原样返回。"""
    n = len(cats)
    if not sample or sample >= n or sample < 3:
        return cats, series
    idx = sorted(set().union(*(_lttb_indices(v, sample) for v in series)))
    return [cats[i] for i in idx], [[v[i] for i in idx] for v in series]
