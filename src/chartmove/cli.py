"""CLI 入口:22 种图表类型,一条命令出图(数据写法与参数表见 README.md)。

    chartmove bar "季度产量" Q1=120 Q2=200 Q3=90 --style mckinsey
    chartmove line-multi "对比" --categories 1月,2月,3月 --series series.json
    chartmove sunburst "销售构成" --data '{"水果": {"苹果": 30}}'
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from pathlib import Path

from ._version import __version__
from .table import file_box_groups, file_columns, file_matrix, file_samples, file_xy, parse_float
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS, THEMES

_MULTI_TYPES = ('line-multi', 'bar-multi', 'radar')
_XY_TYPES = ('scatter', 'bubble')


def _chart_fn(kind: str):
    """按类型名取 graph 里的绘图函数('line-multi' → 'line_multi',机械映射);
    延迟导入让 --help / themes 等纯文本入口不付 matplotlib 启动成本。
    """
    from . import graph
    return getattr(graph, kind.replace('-', '_'))


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
    return [parse_float(v, '(逗号分隔列表)')
            for v in str(src).replace('，', ',').split(',') if v.strip()]


def _str_list(src) -> list[str]:
    return [v for v in str(src).replace('，', ',').split(',') if v.strip()]


def _parse_pairs(items: list[str]) -> tuple[list[str], list[float]]:
    cats, vals = [], []
    for it in items:
        k, _, v = it.partition('=')
        if not k or not v:
            raise ValueError(f'数据格式应为 类目=数值,收到: {it!r}')
        cats.append(k)
        vals.append(parse_float(v, f'(类目「{k}」)'))
    return cats, vals


def _norm_series(raw) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...];接受 [[名, [值..]], ...] 或 {名: [值..]}。"""
    items = raw.items() if isinstance(raw, dict) else raw
    out = []
    for item in items:
        nm, vals = item
        out.append((str(nm), [parse_float(v, f'(系列「{nm}」)') for v in vals]))
    if not out:
        raise ValueError('series 不能为空')
    return out


def _figsize(text: str | None):
    if not text:
        return None
    for sep in ('x', 'X', '*'):
        if sep in text:
            w, _, h = text.partition(sep)
            return (parse_float(w, '(--figsize 宽度)'),
                    parse_float(h, '(--figsize 高度)'))
    raise ValueError(f'--figsize 格式应为 宽x高,收到: {text!r}')


def _common_kwargs(args) -> dict:
    return dict(style=args.style, animate=args.animate, fmt=args.fmt, out=args.out,
                out_dir=args.out_dir, loop=args.loop, numfmt=args.numfmt, note=args.note,
                figsize=_figsize(args.figsize), dpi=args.dpi)


def _sample_kw(args) -> dict:
    """--sample 仅 line / area / line-multi 支持:存在且非空时透传。"""
    return {'sample': args.sample} if getattr(args, 'sample', None) else {}


def _pairs_or_json(args) -> tuple[list[str], list[float]]:
    if args.data:
        d = _load_json(args.data)
        try:
            return ([str(c) for c in d['categories']],
                    [parse_float(v, '(--data values)') for v in d['values']])
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


def _file_cols(args, min_cols=1):
    """--file 数据:--cat-col 指定类目列(默认第 1 列),其余列为数值;
    --col 可挑选 1 个数值列(表头名或序号)。返回 (类目, [(列名, 数值列表)])。"""
    cats, cols = file_columns(args.file, getattr(args, 'cat_col', None),
                              getattr(args, 'col', None), getattr(args, 'sheet', None))
    if len(cols) < min_cols:
        raise ValueError(f'--file 至少需要 {min_cols} 列数值')
    return cats, cols


def _one_col(cols, t):
    if len(cols) != 1:
        raise ValueError(f'{t} 只支持 1 列数值,--file 里有 {len(cols)} 列'
                         '(可用 --col 指定其中一列)')


# ---------- 各类型的运行逻辑 ----------

def _run_bar(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:
        cats, cols = _file_cols(args)
        if len(cols) >= 2:  # 多数值列自动升级为分组柱状图
            return _chart_fn('bar-multi')(args.title, cats, cols, **kw)
        _one_col(cols, 'bar')
        return fn(args.title, cats, cols[0][1], horizontal=args.horizontal, **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, horizontal=args.horizontal, **kw)


def _run_line(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    band = {'lower': _num_list(args.lower) if args.lower else None,
            'upper': _num_list(args.upper) if args.upper else None}
    if args.file:
        cats, cols = _file_cols(args)
        if len(cols) >= 2:  # 多数值列自动升级为多系列折线
            if any(band.values()):
                raise ValueError('区间带 --lower/--upper 仅支持单系列折线')
            return _chart_fn('line-multi')(args.title, cats, cols,
                                           **_sample_kw(args), **kw)
        _one_col(cols, 'line')
        return fn(args.title, cats, cols[0][1], name=cols[0][0],
                  **band, **_sample_kw(args), **kw)  # 图例名 = 列表头
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, **band, **_sample_kw(args), **kw)


def _run_waterfall(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:
        cats, cols = _file_cols(args)
        _one_col(cols, 'waterfall')
        return fn(args.title, cats, cols[0][1], total=not args.no_total, **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, total=not args.no_total, **kw)


def _run_combo(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:  # 类目列之后的第 1 列柱值、第 2 列折线值
        cats, cols = _file_cols(args, min_cols=2)
        if len(cols) > 2:
            raise ValueError(f'combo 的 --file 需要 2 列数值(第 1 列柱值、第 2 列折线值),'
                             f'收到 {len(cols)} 列(可用 --col 挑选)')
        bvals, lvals = cols[0][1], cols[1][1]
    else:
        cats, bvals = _pairs_or_json(args)
        lvals = _num_list(args.line)
    return fn(args.title, cats, bvals, lvals, bar_name=args.bar_name,
              line_name=args.line_name, **kw)


def _run_multi(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:
        cats, cols = _file_cols(args)
        ss = cols
    else:
        cats, ss = _series_or_json(args)
    vkw = {'value_labels': False} if getattr(args, 'no_value_labels', False) else {}
    extra = {'stacked': args.stacked, 'percent': args.percent} if kind == 'bar-multi' else {}
    return fn(args.title, cats, ss, **vkw, **extra, **_sample_kw(args), **kw)


def _run_area(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    sp = {'stacked': args.stacked, 'percent': args.percent}
    if args.file:
        cats, cols = _file_cols(args)
        if len(cols) >= 2:  # 多数值列自动升级为多系列面积(可堆积)
            return fn(args.title, cats, series=cols, **sp, **_sample_kw(args), **kw)
        return fn(args.title, cats, cols[0][1], name=cols[0][0], **sp,
                  **_sample_kw(args), **kw)
    d = _load_json(args.data) if args.data else None
    if (d is not None and 'series' in d) or getattr(args, 'series', None):
        cats, ss = _series_or_json(args)
        return fn(args.title, cats, series=ss, **sp, **_sample_kw(args), **kw)
    cats, vals = _pairs_or_json(args)
    return fn(args.title, cats, vals, **sp, **_sample_kw(args), **kw)


def _run_sunburst(kind, args):
    if args.file:
        raise ValueError('sunburst 暂不支持 --file(层级数据请用 --data 传 JSON)')
    fn = _chart_fn(kind)
    d = _load_json(args.data) if args.data else None
    if d is None:
        raise ValueError('sunburst 需要 --data 传两级层级 JSON,'
                         '如 \'{"水果": {"苹果": 30}}\'(也可含 hierarchy 字段)')
    return fn(args.title, d.get('hierarchy', d), **_common_kwargs(args))


def _run_box(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:  # 每列一组,首行表头=组名,单元格为原始样本
        return fn(args.title, file_box_groups(args.file, getattr(args, 'sheet', None)), **kw)
    if not args.series:
        raise ValueError('box 需要 --series(JSON)或 --file(CSV/Excel,每列一组)')
    return fn(args.title, _norm_series(_load_json(args.series)), **kw)


def _run_xy(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:  # 列顺序:x, y(, sizes)(, labels)
        xs, ys, sizes, labels = file_xy(args.file, sizes=args.type == 'bubble',
                                        sheet=getattr(args, 'sheet', None))
        if args.type == 'bubble':
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


def _bins(text: str):
    """--bins:整数 / 'auto' / 逗号分隔的分箱边界(对齐 core.hist 的 bins 语义)。"""
    if text == 'auto':
        return 'auto'
    if ',' in text or '，' in text:
        edges = _num_list(text)
        if len(edges) < 2:
            raise ValueError(f'--bins 分箱边界至少 2 个数,收到 {text!r}')
        if any(b <= a for a, b in zip(edges, edges[1:])):
            raise ValueError(f'--bins 分箱边界必须严格递增,收到 {edges}')
        return edges
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"--bins 需为整数、'auto' 或逗号分隔边界,收到 {text!r}") from None


def _run_hist(kind, args):
    fn = _chart_fn(kind)
    bins = _bins(args.bins)
    kw = _common_kwargs(args)
    if args.file:
        return fn(args.title, file_samples(args.file, getattr(args, 'sheet', None)),
                  bins=bins, **kw)
    if args.data:
        vals = [float(v) for v in _load_json(args.data)['values']]
    elif getattr(args, 'items', None):
        vals = [float(v) for v in args.items]
    else:
        raise ValueError('请提供原始样本数值,或用 --data / --file 传数据')
    return fn(args.title, vals, bins=bins, **kw)


def _run_heatmap(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:  # 类目列=行名(默认第 1 列),其余列为矩阵
        rlabels, col_names, matrix = file_matrix(args.file, getattr(args, 'cat_col', None),
                                                 getattr(args, 'sheet', None))
        return fn(args.title, rlabels, col_names, matrix,
                  annotate=not args.no_annotate, **kw)
    d = _load_json(args.data) if args.data else {}
    if not all(k in d for k in ('rows', 'cols', 'values')):
        raise ValueError('heatmap 需要 --file 或 --data(JSON 含 rows / cols / values 字段)')
    return fn(args.title, d['rows'], d['cols'], d['values'],
              annotate=not args.no_annotate, **kw)


def _run_gantt(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:  # 2 个数值列 = 开始、结束
        cats, cols = _file_cols(args, min_cols=2)
        if len(cols) != 2:
            raise ValueError(f'gantt 的 --file 需要 2 列数值(第 1 列开始、第 2 列结束),'
                             f'收到 {len(cols)} 列(可用 --col 挑选)')
        return fn(args.title, cats, cols[0][1], cols[1][1], **kw)
    d = _load_json(args.data) if args.data else {}
    cats = (_str_list(args.categories) if getattr(args, 'categories', None)
            else d.get('tasks') or d.get('categories'))
    starts = _num_list(args.starts) if getattr(args, 'starts', None) else d.get('starts')
    ends = _num_list(args.ends) if getattr(args, 'ends', None) else d.get('ends')
    if not cats or not starts or not ends:
        raise ValueError('gantt 需要 --categories + --starts + --ends,'
                         '或 --file(2 个数值列),或 --data JSON(tasks/categories、starts、ends)')
    return fn(args.title, cats, starts, ends, **kw)


def _run_dumbbell(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    slope = getattr(args, 'slope', False)
    if args.file:  # 2 个数值列 = 期初、期末
        cats, cols = _file_cols(args, min_cols=2)
        if len(cols) != 2:
            raise ValueError(f'dumbbell 的 --file 需要 2 列数值(期初、期末),'
                             f'收到 {len(cols)} 列(可用 --col 挑选)')
        return fn(args.title, cats, [cols[0], cols[1]], slope=slope, **kw)
    cats, ss = _series_or_json(args)
    return fn(args.title, cats, ss, slope=slope, **kw)


def _default_run(kind, args):
    fn = _chart_fn(kind)
    kw = _common_kwargs(args)
    if args.file:
        cats, cols = _file_cols(args)
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
    'area': _run_area,
    'sunburst': _run_sunburst,
    'box': _run_box,
    'scatter': _run_xy,
    'bubble': _run_xy,
    'hist': _run_hist,
    'heatmap': _run_heatmap,
    'gantt': _run_gantt,
    'dumbbell': _run_dumbbell,
}


def _themes_cmd(args) -> int:
    for pack, members in THEME_PACKS.items():
        print(f'{pack}:')
        for key in members:
            print(f'  {key:<11} {THEME_LABELS[key]} —— {THEME_DESCS[key]}')
    print('\n用法:--style <主题名>(默认 business)')
    if getattr(args, 'preview', False):
        from .graph import themes_preview  # 延迟导入:纯文本的 themes 不拉起 matplotlib
        themes_preview(out=getattr(args, 'out', None),
                       out_dir=getattr(args, 'out_dir', None))
    return 0


# ---------- 命令行组装 ----------

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog='chartmove', description='中文数据图表生成器(默认输出 ./Results/)')
    ap.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    sub = ap.add_subparsers(dest='type', required=True, metavar='类型')

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('title', help='图表标题')
    common.add_argument('--style', choices=list(THEMES), default='business',
                        help='主题(默认 business,chartmove themes 可查)')
    common.add_argument('--animate', action='store_true', help='生成动画(默认 GIF)')
    common.add_argument('--loop', action='store_true',
                        help='GIF 无限循环(默认播一遍停在末帧;MP4 循环由播放器决定,不支持)')
    common.add_argument('--fmt', choices=['png', 'gif', 'mp4', 'pdf', 'tif'], default=None,
                        help='输出格式;静态默认 png,动画默认 gif')
    common.add_argument('--out-dir', help='输出目录(默认 CHARTMOVE_OUT_DIR 或 ./Results/)')
    common.add_argument('--out', help='输出文件名(不含扩展名),默认 类型_标题')
    common.add_argument('--dpi', type=float, help='分辨率(默认静态 150 / tif 600 / GIF 75)')
    common.add_argument('--figsize', help='画幅 宽x高,如 12.8x7.2')
    common.add_argument('--numfmt', choices=['auto', 'plain', 'percent'], default='auto',
                        help="数值标签/刻度格式:auto 万/亿(默认)/ plain 原样 / percent 追加 %%")
    common.add_argument('--note', help='底部脚注(数据来源 / 备注)')
    common.add_argument('--data', help='JSON 入参(内联字符串或文件路径),可替代位置数据')
    common.add_argument('--file', help='CSV / Excel 数据文件(.csv/.xlsx,首行为表头;'
                                       '第 1 列类目,其余列数值,多数值列 bar/line 自动转多系列)')
    common.add_argument('--cat-col', help='--file 的类目列(表头名或从 1 数的序号,默认第 1 列)')
    common.add_argument('--col', help='--file 挑选 1 个数值列(表头名或序号;默认除类目列外全部)')
    common.add_argument('--sheet', help='--file 的 Excel 工作表(名称或从 1 数的序号,默认第一个)')

    sps = {}
    for name, text, items_help in (
        ('bar', '柱状图', '数据 类目=数值,如 Q1=120(或 --data JSON)'),
        ('line', '单系列折线', '数据 类目=数值(或 --data JSON)'),
        ('area', '面积图', '数据 类目=数值(或 --data JSON)'),
        ('pie', '饼图', '数据 类目=数值(或 --data JSON)'),
        ('donut', '环形图', '数据 类目=数值(或 --data JSON)'),
        ('rose', '玫瑰图(极坐标柱状)', '数据 类目=数值(或 --data JSON)'),
        ('treemap', '矩形树图(构成)', '数据 类目=数值(或 --data JSON)'),
        ('waterfall', '瀑布图(自动补合计柱)', '数据 类目=增减值,如 1月=20'),
        ('pareto', '帕累托图(降序柱+累计占比线+80%参考线)', '数据 类目=数值'),
        ('funnel', '漏斗图(自动标逐级转化率)', '数据 类目=数值'),
        ('combo', '双轴组合图', '柱值 类目=数值(折线值用 --line)'),
        ('line-multi', '多系列折线', None),
        ('bar-multi', '多系列柱状图(--stacked 堆积 / --percent 百分比堆积)', None),
        ('radar', '雷达图', None),
        ('box', '箱线图', None),
        ('scatter', '散点图', None),
        ('bubble', '气泡图', None),
        ('hist', '直方图', '原始样本数值,空格分隔(或 --data JSON)'),
        ('heatmap', '热力图', None),
        ('gantt', '甘特图', None),
        ('dumbbell', '哑铃图/坡度图(--slope)', None),
        ('sunburst', '旭日图(两级层级占比,--data 传层级 JSON)', None),
    ):
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
        if items_help:
            sp.add_argument('items', nargs='*', help=items_help)
        # 只把类型名交给 runner,core 函数在出图时才解析(入口保持轻量)
        sp.set_defaults(func=partial(_RUNNERS.get(name, _default_run), name))
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
    sps['bar-multi'].add_argument('--stacked', action='store_true',
                                  help='堆积柱状(各系列纵向堆叠)')
    sps['bar-multi'].add_argument('--percent', action='store_true',
                                  help='百分比堆积(每类目归一 100%%,隐含 --stacked)')
    sps['area'].add_argument('--series',
                             help='多系列 JSON:[[名称, [数值...]], ...](配 --categories;'
                                  '默认叠加,--stacked/--percent 堆积)')
    sps['area'].add_argument('--categories', help='类目,逗号分隔(也可放进 --data JSON)')
    sps['area'].add_argument('--stacked', action='store_true',
                             help='多系列堆积面积(需 --series 或 --file 多数值列)')
    sps['area'].add_argument('--percent', action='store_true',
                             help='百分比堆积(每类目归一 100%%,隐含 --stacked)')
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
    sps['hist'].add_argument('--bins', default='10',
                             help="分箱数:整数 / 'auto' / 逗号分隔边界(如 1,10,20)")
    sps['heatmap'].add_argument('--no-annotate', action='store_true', help='不在格子标数值')
    sps['gantt'].add_argument('--categories', help='任务名,逗号分隔(也可 --data / --file)')
    sps['gantt'].add_argument('--starts', help='各任务开始,逗号分隔,如 1,4,12')
    sps['gantt'].add_argument('--ends', help='各任务结束,逗号分隔,如 5,11,17')
    sps['dumbbell'].add_argument('--series',
                                 help='系列 JSON:[[期初名, [数值...]], [期末名, [数值...]]]'
                                      '(恰好 2 个;与 --file 二选一)')
    sps['dumbbell'].add_argument('--categories', help='类目,逗号分隔(也可放进 --data JSON)')
    sps['dumbbell'].add_argument('--slope', action='store_true',
                                 help='出坡度图(期初/期末两列斜线)')
    sps['line'].add_argument('--lower',
                             help='区间带下界,逗号分隔(与 --upper 成对使用)')
    sps['line'].add_argument('--upper', help='区间带上界,逗号分隔')

    themes_sp = sub.add_parser('themes', help='列出全部主题(按风格包)')
    themes_sp.add_argument('--preview', action='store_true',
                           help='同时生成主题预览拼版图(全部主题 × 同一组迷你柱状图)')
    themes_sp.add_argument('--out-dir', help='预览图输出目录(默认 CHARTMOVE_OUT_DIR 或 ./Results/)')
    themes_sp.add_argument('--out', help='预览图文件名(不含扩展名,默认 themes_预览)')
    themes_sp.set_defaults(func=_themes_cmd)
    return ap


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except (ValueError, RuntimeError, OSError) as e:
        print(f'生成失败: {e}', file=sys.stderr)
        return 1
    if isinstance(result, int):  # themes 等子命令直接返回退出码
        return result
    return 0 if result else 1


if __name__ == '__main__':
    raise SystemExit(main())
