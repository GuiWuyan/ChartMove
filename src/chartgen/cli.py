"""CLI 入口(M2):16 种图表类型,一条命令出图。

    chartgen bar "季度产量" Q1=120 Q2=200 Q3=90 --style mckinsey
    chartgen line "月度增长" --data data.json        # {"categories": [...], "values": [...]}
    chartgen line-multi "对比" --categories 1月,2月,3月 --series series.json
    chartgen combo "销量与客单价" Q1=120 Q2=200 --line 86,92
    chartgen scatter "分布" --x 1,2,3 --y 5,7,6 --trend
    chartgen hist "响应时长" 12 15 18 22 --bins 8
    chartgen box "A/B 测试" --series samples.json    # [["对照组", [3.1, ...]], ...]
    chartgen heatmap "热力" --data heat.json
    #   heat.json: {"rows": [...], "cols": [...], "values": [[...], ...]}
    chartgen themes                                  # 列出全部主题(按风格包)

数据约定:单系列用"类目=值"内联;--data / --series 接内联 JSON 字符串或文件路径。
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from pathlib import Path

from .core import (
    area,
    bar,
    bar_multi,
    box,
    bubble,
    combo,
    donut,
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
from .table import read_table, to_float
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS, THEMES

_MULTI_TYPES = ('line-multi', 'bar-multi', 'radar')
_XY_TYPES = ('scatter', 'bubble')


# ---------- 入参解析 ----------

def _load_json(src: str):
    """接受内联 JSON 字符串或文件路径。"""
    p = Path(src)
    text = p.read_text(encoding='utf-8') if p.exists() else src
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON 解析失败: {e}') from e


def _num_list(src) -> list[float]:
    return [float(v) for v in str(src).replace('，', ',').split(',') if v.strip()]


def _str_list(src) -> list[str]:
    return [v for v in str(src).replace('，', ',').split(',') if v.strip()]


def _parse_pairs(items: list[str]) -> tuple[list[str], list[float]]:
    cats, vals = [], []
    for it in items:
        k, _, v = it.partition('=')
        if not k or not v:
            raise ValueError(f'数据格式应为 类目=数值,收到: {it!r}')
        cats.append(k)
        vals.append(float(v))
    return cats, vals


def _norm_series(raw) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...];接受 [[名, [值..]], ...] 或 {名: [值..]}。"""
    items = raw.items() if isinstance(raw, dict) else raw
    out = []
    for item in items:
        nm, vals = item
        out.append((str(nm), [float(v) for v in vals]))
    if not out:
        raise ValueError('series 不能为空')
    return out


def _figsize(text: str | None):
    if not text:
        return None
    for sep in ('x', 'X', '*'):
        if sep in text:
            w, _, h = text.partition(sep)
            return float(w), float(h)
    raise ValueError(f'--figsize 格式应为 宽x高,收到: {text!r}')


def _common_kwargs(args) -> dict:
    return dict(style=args.style, animate=args.animate, fmt=args.fmt, out=args.out,
                out_dir=args.out_dir, loop=args.loop,
                figsize=_figsize(args.figsize), dpi=args.dpi)


def _sample_kw(args) -> dict:
    """--sample 仅 line / area / line-multi 支持:存在且非空时透传。"""
    return {'sample': args.sample} if getattr(args, 'sample', None) else {}


def _pairs_or_json(args) -> tuple[list[str], list[float]]:
    if args.data:
        d = _load_json(args.data)
        try:
            return [str(c) for c in d['categories']], [float(v) for v in d['values']]
        except (KeyError, TypeError) as e:
            raise ValueError('--data JSON 需含 categories 与 values 字段') from e
    if getattr(args, 'items', None):
        return _parse_pairs(args.items)
    raise ValueError('请提供 类目=值 数据,或用 --data 传 JSON')


def _series_or_json(args):
    if args.data:
        d = _load_json(args.data)
        try:
            return [str(c) for c in d['categories']], _norm_series(d['series'])
        except (KeyError, TypeError) as e:
            raise ValueError('--data JSON 需含 categories 与 series 字段') from e
    if getattr(args, 'series', None) and getattr(args, 'categories', None):
        return _str_list(args.categories), _norm_series(_load_json(args.series))
    raise ValueError('请用 --categories + --series,或用 --data 传含 categories/series 的 JSON')


def _col_index(spec, header, default):
    """--cat-col / --col:表头名或从 1 数的序号;未指定返回 default。"""
    if spec is None:
        return default
    if spec in header:
        return header.index(spec)
    try:
        idx = int(spec) - 1
    except ValueError:
        raise ValueError(f'找不到列 {spec!r};可用列:{", ".join(header)}') from None
    if not 0 <= idx < len(header):
        raise ValueError(f'列序号 {spec} 超出范围,共 {len(header)} 列')
    return idx


def _file_cols(args, min_cols=1):
    """--file 数据:--cat-col 指定类目列(默认第 1 列),其余列为数值;
    --col 可挑选 1 个数值列(表头名或序号)。返回 (类目, [(列名, 数值列表)], 表头)。"""
    header, rows = read_table(args.file)
    cat_i = _col_index(getattr(args, 'cat_col', None), header, 0)
    cats = [r[cat_i] if len(r) > cat_i else '' for r in rows]
    if getattr(args, 'col', None):
        val_is = [_col_index(args.col, header, None)]
    else:
        val_is = [j for j in range(len(header)) if j != cat_i]
    cols = []
    for j in val_is:
        nm = header[j] or f'列{j + 1}'
        cols.append((nm, [to_float(r[j], f'(列「{nm}」)')
                          for r in rows if len(r) > j and r[j] != '']))
    if len(cols) < min_cols:
        raise ValueError(f'--file 至少需要 {min_cols} 列数值')
    return cats, cols, header


def _one_col(cols, t):
    if len(cols) != 1:
        raise ValueError(f'{t} 只支持 1 列数值,--file 里有 {len(cols)} 列'
                         '(可用 --col 指定其中一列)')


# ---------- 各类型的运行逻辑 ----------

def _run_bar(fn, args):
    kw = _common_kwargs(args)
    if args.file:
        cats, cols, _ = _file_cols(args)
        if len(cols) >= 2:  # 多数值列自动升级为分组柱状图
            return bar_multi(args.title, cats, cols, **kw)
        _one_col(cols, 'bar')
        return fn(args.title, cats, cols[0][1], horizontal=args.horizontal, **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, horizontal=args.horizontal, **kw)


def _run_line(fn, args):
    kw = _common_kwargs(args)
    if args.file:
        cats, cols, _ = _file_cols(args)
        if len(cols) >= 2:  # 多数值列自动升级为多系列折线
            return line_multi(args.title, cats, cols, **_sample_kw(args), **kw)
        _one_col(cols, 'line')
        return fn(args.title, cats, cols[0][1], name=cols[0][0],
                  **_sample_kw(args), **kw)  # 图例名 = 列表头
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, **_sample_kw(args), **kw)


def _run_waterfall(fn, args):
    kw = _common_kwargs(args)
    if args.file:
        cats, cols, _ = _file_cols(args)
        _one_col(cols, 'waterfall')
        return fn(args.title, cats, cols[0][1], total=not args.no_total, **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, total=not args.no_total, **kw)


def _run_combo(fn, args):
    kw = _common_kwargs(args)
    if args.file:  # 类目列之后的第 1 列柱值、第 2 列折线值
        cats, cols, _ = _file_cols(args, min_cols=2)
        bvals, lvals = cols[0][1], cols[1][1]
    else:
        cats, bvals = _pairs_or_json(args)
        lvals = _num_list(args.line)
    return fn(args.title, cats, bvals, lvals, bar_name=args.bar_name,
              line_name=args.line_name, **kw)


def _run_multi(fn, args):
    kw = _common_kwargs(args)
    if args.file:
        cats, cols, _ = _file_cols(args)
        ss = cols
    else:
        cats, ss = _series_or_json(args)
    vkw = {'value_labels': False} if getattr(args, 'no_value_labels', False) else {}
    return fn(args.title, cats, ss, **vkw, **_sample_kw(args), **kw)


def _run_box(fn, args):
    kw = _common_kwargs(args)
    if args.file:  # 每列一组,首行表头=组名,单元格为原始样本
        header, rows = read_table(args.file)
        groups = []
        for j, name in enumerate(header):
            samples = [to_float(r[j], f'(列「{name}」)')
                       for r in rows if len(r) > j and r[j] != '']
            groups.append((name or f'组{j + 1}', samples))
        return fn(args.title, groups, **kw)
    if not args.series:
        raise ValueError('box 需要 --series(JSON)或 --file(CSV/Excel,每列一组)')
    return fn(args.title, _norm_series(_load_json(args.series)), **kw)


def _run_xy(fn, args):
    kw = _common_kwargs(args)
    if args.file:  # 列顺序:x, y(, sizes)(, labels)
        header, rows = read_table(args.file)
        xs = [to_float(r[0], '(列 1)') for r in rows if r and r[0] != '']
        ys = [to_float(r[1], '(列 2)') for r in rows if len(r) > 1 and r[1] != '']
        labels = [r[3] for r in rows if len(r) > 3 and r[3]] or None
        if args.type == 'bubble':
            sizes = [to_float(r[2], '(列 3)') for r in rows if len(r) > 2 and r[2] != '']
            if not sizes:
                raise ValueError('bubble 的 --file 需要第 3 列气泡大小')
            return fn(args.title, xs, ys, sizes, labels=labels, **kw)
        return fn(args.title, xs, ys, trend=args.trend, labels=labels, **kw)
    d = _load_json(args.data) if args.data else {}
    xs = _num_list(args.x) if args.x else d.get('xs')
    ys = _num_list(args.y) if args.y else d.get('ys')
    if not xs or not ys:
        raise ValueError('请用 --x/--y、--file 提供数据,或用 --data 传 {"xs": [...], "ys": [...]}')
    labels = _str_list(args.labels) if args.labels else d.get('labels')
    if args.type == 'bubble':
        sizes = _num_list(args.sizes) if args.sizes else d.get('sizes')
        if not sizes:
            raise ValueError('bubble 需要 --sizes / --file 第 3 列,或 --data 传 sizes 字段')
        return fn(args.title, xs, ys, sizes, labels=labels, **kw)
    return fn(args.title, xs, ys, trend=args.trend, labels=labels, **kw)


def _run_hist(fn, args):
    bins = args.bins if args.bins == 'auto' else int(args.bins)
    kw = _common_kwargs(args)
    if args.file:
        header, rows = read_table(args.file)
        vals = [to_float(r[0], f'(列「{header[0]}」)') for r in rows if r and r[0] != '']
        if not vals:
            raise ValueError('--file 第 1 列需为数值样本')
        return fn(args.title, vals, bins=bins, **kw)
    if args.data:
        vals = [float(v) for v in _load_json(args.data)['values']]
    elif getattr(args, 'items', None):
        vals = [float(v) for v in args.items]
    else:
        raise ValueError('请提供原始样本数值,或用 --data / --file 传数据')
    return fn(args.title, vals, bins=bins, **kw)


def _run_heatmap(fn, args):
    kw = _common_kwargs(args)
    if args.file:  # 类目列=行名(默认第 1 列),其余列为矩阵
        header, rows = read_table(args.file)
        cat_i = _col_index(getattr(args, 'cat_col', None), header, 0)
        rlabels = [r[cat_i] if len(r) > cat_i else '' for r in rows]
        val_is = [j for j in range(len(header)) if j != cat_i]
        cols = [header[j] or f'列{j + 1}' for j in val_is]
        matrix = [[to_float(r[j], f'(列「{header[j]}」)') for j in val_is] for r in rows]
        return fn(args.title, rlabels, cols, matrix, annotate=not args.no_annotate, **kw)
    d = _load_json(args.data) if args.data else {}
    if not all(k in d for k in ('rows', 'cols', 'values')):
        raise ValueError('heatmap 需要 --file 或 --data(JSON 含 rows / cols / values 字段)')
    return fn(args.title, d['rows'], d['cols'], d['values'],
              annotate=not args.no_annotate, **kw)


def _default_run(fn, args):
    kw = _common_kwargs(args)
    if args.file:
        cats, cols, _ = _file_cols(args)
        _one_col(cols, args.type)
        return fn(args.title, cats, cols[0][1], **_sample_kw(args), **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, **_sample_kw(args), **kw)


_RUNNERS = {
    'bar': _run_bar,
    'line': _run_line,
    'waterfall': _run_waterfall,
    'combo': _run_combo,
    'line-multi': _run_multi,
    'bar-multi': _run_multi,
    'radar': _run_multi,
    'box': _run_box,
    'scatter': _run_xy,
    'bubble': _run_xy,
    'hist': _run_hist,
    'heatmap': _run_heatmap,
}


def _themes_cmd(_args) -> int:
    for pack, members in THEME_PACKS.items():
        print(f'{pack}:')
        for key in members:
            print(f'  {key:<11} {THEME_LABELS[key]} —— {THEME_DESCS[key]}')
    print('\n用法:--style <主题名>(默认 business)')
    return 0


# ---------- 命令行组装 ----------

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog='chartgen', description='中文数据图表生成器(默认输出 ./Results/)')
    sub = ap.add_subparsers(dest='type', required=True, metavar='类型')

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('title', help='图表标题')
    common.add_argument('--style', choices=list(THEMES), default='business',
                        help='主题(默认 business,chartgen themes 可查)')
    common.add_argument('--animate', action='store_true', help='生成动画(默认 GIF)')
    common.add_argument('--loop', action='store_true',
                        help='GIF 无限循环(默认播一遍停在末帧;MP4 循环由播放器决定,不支持)')
    common.add_argument('--fmt', choices=['png', 'gif', 'mp4', 'pdf', 'tif'], default=None,
                        help='输出格式;静态默认 png,动画默认 gif')
    common.add_argument('--out-dir', help='输出目录(默认 CHARTGEN_OUT_DIR 或 ./Results/)')
    common.add_argument('--out', help='输出文件名(不含扩展名),默认 类型_标题')
    common.add_argument('--dpi', type=float, help='分辨率(默认静态 150 / tif 600 / GIF 75)')
    common.add_argument('--figsize', help='画幅 宽x高,如 12.8x7.2')
    common.add_argument('--data', help='JSON 入参(内联字符串或文件路径),可替代位置数据')
    common.add_argument('--file', help='CSV / Excel 数据文件(.csv/.xlsx,首行为表头;'
                                       '第 1 列类目,其余列数值,多数值列 bar/line 自动转多系列)')
    common.add_argument('--cat-col', help='--file 的类目列(表头名或从 1 数的序号,默认第 1 列)')
    common.add_argument('--col', help='--file 挑选 1 个数值列(表头名或序号;默认除类目列外全部)')

    sps = {}
    for name, fn, text, items_help in (
        ('bar', bar, '柱状图', '数据 类目=数值,如 Q1=120(或 --data JSON)'),
        ('line', line, '单系列折线', '数据 类目=数值(或 --data JSON)'),
        ('area', area, '面积图', '数据 类目=数值(或 --data JSON)'),
        ('pie', pie, '饼图', '数据 类目=数值(或 --data JSON)'),
        ('donut', donut, '环形图', '数据 类目=数值(或 --data JSON)'),
        ('waterfall', waterfall, '瀑布图(自动补合计柱)', '数据 类目=增减值,如 1月=20'),
        ('funnel', funnel, '漏斗图(自动标逐级转化率)', '数据 类目=数值'),
        ('combo', combo, '双轴组合图', '柱值 类目=数值(折线值用 --line)'),
        ('line-multi', line_multi, '多系列折线', None),
        ('bar-multi', bar_multi, '多系列分组柱状图', None),
        ('radar', radar, '雷达图', None),
        ('box', box, '箱线图', None),
        ('scatter', scatter, '散点图', None),
        ('bubble', bubble, '气泡图', None),
        ('hist', hist, '直方图', '原始样本数值,空格分隔(或 --data JSON)'),
        ('heatmap', heatmap, '热力图', None),
    ):
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
        if items_help:
            sp.add_argument('items', nargs='*', help=items_help)
        sp.set_defaults(func=partial(_RUNNERS.get(name, _default_run), fn))
        sps[name] = sp

    sps['bar'].add_argument('--horizontal', action='store_true', help='横向条形(排名场景)')
    sps['waterfall'].add_argument('--no-total', action='store_true', help='不追加合计柱')
    sps['combo'].add_argument('--line', required=True, help='折线数值,逗号分隔,如 86,92')
    sps['combo'].add_argument('--bar-name', default='柱状', help='柱系列图例名')
    sps['combo'].add_argument('--line-name', default='折线', help='折线系列图例名')
    for name in _MULTI_TYPES:
        sps[name].add_argument('--series',
                               help='系列 JSON:[[名称, [数值...]], ...] 或 {名称: [数值...]}')
        sps[name].add_argument('--categories', help='类目,逗号分隔(也可放进 --data JSON)')
    sps['line-multi'].add_argument('--no-value-labels', action='store_true',
                                   help='关闭数值标注')
    sps['line'].add_argument('--sample', type=int,
                             help='大数据降采样目标点数(LTTB 保形,如 300)')
    sps['area'].add_argument('--sample', type=int, help='同 line:LTTB 降采样目标点数')
    sps['line-multi'].add_argument('--sample', type=int,
                                   help='同 line:LTTB 降采样(各系列取保留点并集)')
    sps['box'].add_argument('--series',
                            help='样本 JSON:[[组名, [样本...]], ...](与 --file 二选一)')
    for name in _XY_TYPES:
        sps[name].add_argument('--x', help='x 数值,逗号分隔')
        sps[name].add_argument('--y', help='y 数值,逗号分隔')
        sps[name].add_argument('--labels', help='逐点标注,逗号分隔')
    sps['scatter'].add_argument('--trend', action='store_true', help='叠加线性趋势线')
    sps['bubble'].add_argument('--sizes', help='气泡大小,逗号分隔(面积自动归一)')
    sps['hist'].add_argument('--bins', default='10', help="分箱数,整数或 'auto'")
    sps['heatmap'].add_argument('--no-annotate', action='store_true', help='不在格子标数值')

    themes_sp = sub.add_parser('themes', help='列出全部主题(按风格包)')
    themes_sp.set_defaults(func=_themes_cmd)
    return ap


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except (ValueError, RuntimeError) as e:
        print(f'生成失败: {e}', file=sys.stderr)
        return 1
    if isinstance(result, int):  # themes 等子命令直接返回退出码
        return result
    return 0 if result else 1


if __name__ == '__main__':
    raise SystemExit(main())
