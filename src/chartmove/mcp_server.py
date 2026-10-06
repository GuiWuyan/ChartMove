"""MCP Server(stdio):make_chart 出图 + list_themes 列主题;工具描述用英文,
数据校验错误保持中文 ToolError;返回 JSON 里的 path 即交付物。"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Literal, get_args

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ._version import __version__
from .table import (
    file_box_groups,
    file_columns,
    file_links,
    file_matrix,
    file_samples,
    file_xy,
    parse_float,
)
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS, THEMES

ChartType = Literal[
    'bar', 'line', 'line-multi', 'area', 'pie', 'donut', 'combo', 'bar-multi',
    'radar', 'scatter', 'bubble', 'hist', 'box', 'violin', 'heatmap', 'waterfall',
    'funnel', 'rose', 'treemap', 'gantt', 'dumbbell', 'sankey', 'sunburst',
    'pareto']
Fmt = Literal['png', 'pdf', 'tif', 'gif', 'mp4']


def _chart_fn(name: str):
    """按类型名取 graph 里的绘图函数('line-multi' → 'line_multi',机械映射),
    延迟导入让 MCP 握手阶段不付 matplotlib 启动成本。
    """
    from . import graph
    return getattr(graph, name.replace('-', '_'))

_PAIR_TYPES = ('bar', 'line', 'area', 'pie', 'donut', 'waterfall', 'funnel', 'rose',
               'treemap', 'pareto')
_SERIES_TYPES = ('line-multi', 'bar-multi', 'radar')
_XY_TYPES = ('scatter', 'bubble')

server = MCPServer(
    name='chartmove',
    version=__version__,
    instructions=(
        'Chinese chart generator: 24 chart types x 15 themes, no font configuration '
        'needed, output is a persistent file. Use list_themes to discover styles. '
        'Call make_chart with inline data or a CSV/Excel file path (file param); '
        'the returned "path" (absolute path to the image file) IS the deliverable - '
        'show/link that file to the user. '
        'Set animate=true to get a GIF that plays once and stops on the last frame '
        '(loop=true makes the GIF loop forever); '
        'use static png for documents. Errors are reported '
        'in Chinese and mean the data was invalid - fix the data and retry.'
    ),
)


def _require(cond, message: str) -> None:
    if not cond:
        raise ToolError(message)


def _norm_series(series) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...];接受 [[名, [值..]], ...] 或 {名: [值..]}。"""
    items = series.items() if isinstance(series, dict) else series
    return [(str(nm), [parse_float(v, f'(系列「{nm}」)') for v in vals])
            for nm, vals in items]


def _bins(bins):
    """bins 规范化:整数 / 'auto' / 严格递增边界(递增校验在此做,np.histogram 的异常是英文)。"""
    if isinstance(bins, str):
        if bins == 'auto':
            return 'auto'
        try:
            return int(bins)
        except ValueError:
            raise ToolError(f"bins 需为整数、'auto' 或边界数组,收到 {bins!r}") from None
    if isinstance(bins, list):
        if len(bins) < 2:
            raise ToolError(f'bins 分箱边界至少 2 个数,收到 {bins!r}')
        if any(b <= a for a, b in zip(bins, bins[1:])):
            raise ToolError(f'bins 分箱边界必须严格递增,收到 {bins}')
        return [parse_float(v) for v in bins]
    return bins  # int


@server.tool(
    name='make_chart',
    description=(
        'Generate a chart image with Chinese fonts preconfigured. '
        'Returns JSON string: {path (absolute path, THE deliverable), file_size, '
        'type, style, animated}. Data params by type - '
        'category charts (bar/line/line-multi/area/pie/donut/combo/bar-multi/'
        'rose/treemap/waterfall/funnel): categories + values, or '
        'series=[[name, [values]], ...] '
        'for multi-series (combo also needs line_values); '
        'radar: categories + series=[[name, [values]], ...] (values alone '
        'is rejected); '
        'bar-multi: stacked=true stacks the series vertically, percent=true '
        'normalizes each category to 100% (implies stacked); '
        'area with series: multi-series by default translucent overlaid, '
        'stacked=true layered stacking, percent=true 100% stacked; '
        'sunburst (two-level hierarchical composition): hierarchy = '
        '{parent: {child: value}, ...} (list of [parent, {child: value}] pairs '
        'also accepted), inner ring = parents (value = sum of children), '
        'outer ring = children; '
        'pareto: categories + values, auto-sorted descending with a cumulative '
        '% line and an 80% guide on the right axis; '
        'gantt: categories (task names) + starts + ends (numeric units); '
        'dumbbell: series with EXACTLY 2 entries (before/after), '
        'slope=true switches to a slope chart; '
        'sankey: links = [[source, target, value], ...] (each item may also be '
        'a {source, target, value} dict); flows left to right, node height = '
        'flow volume, cycles and non-positive values are rejected; '
        'line accepts lower + upper (same length as values) to draw a '
        'semi-transparent prediction/confidence band; '
        'scatter/bubble: x + y (+sizes for bubble, +labels optional); '
        'hist: values = raw samples, bins is an int, "auto", or a strictly '
        'increasing edge array (e.g. [1,10,20]); '
        'box: series = [[group_name, [samples]], ...]; '
        'violin: same series shape, KDE density shape per group with inner '
        'IQR bar + median dot, needs >=2 distinct values per group; '
        'heatmap: rows + cols + matrix (2-D numeric). '
        'file (optional): path to a CSV/Excel file (.csv/.xlsx, first row = header) '
        'to read data from - takes precedence over inline data params. '
        'cat_col / col select the category column / one value column '
        '(header name or 1-based index). '
        'sheet (Excel only, optional): worksheet name or 1-based index, '
        'default first sheet; ignored for CSV. File column layout: '
        'category charts use the 1st column as categories and the rest as value '
        'columns (bar/line/area auto-upgrade to bar-multi/line-multi/multi-series '
        'area with >=2 value columns; pie/donut/rose/waterfall/funnel need col '
        'to pick one); '
        'combo: 1st value col = bars, 2nd = line; '
        'box/violin: every column = one group of raw samples; '
        'sankey: 3 columns = source, target, value; '
        'scatter/bubble: columns x, y (, sizes) (, labels); '
        'hist: 1st column = raw samples; '
        'heatmap: 1st column = row names, remaining columns = matrix. '
        'animate=true gives a GIF (plays once, stops on last frame by default; '
        'loop=true makes it loop forever - GIF only, mp4 looping is decided by '
        'the video player so loop=true with fmt=mp4 is rejected); '
        'sample=N (line/area/line-multi only) LTTB-downsamples large series '
        'to ~N points (shape-preserving) before rendering; '
        'fmt chooses png/pdf/tif for static or gif/mp4 for animated. '
        'numfmt formats value labels and the value-axis ticks: auto (default) '
        'renders >=1e4 as 万 and >=1e8 as 亿 (Chinese units), plain shows raw '
        'numbers, percent appends % (data is already in percent units). '
        'note (optional): footnote text rendered small at the bottom-left '
        '(data source / remarks, consulting-report convention). '
        'Invalid data raises an error whose message is in Chinese.'
    ),
)
def make_chart(
    type: ChartType,
    title: str,
    categories: list[str] | None = None,
    values: list[float] | None = None,
    series: list[list[Any]] | dict[str, list[float]] | None = None,
    line_values: list[float] | None = None,
    x: list[float] | None = None,
    y: list[float] | None = None,
    sizes: list[float] | None = None,
    labels: list[str] | None = None,
    rows: list[str] | None = None,
    cols: list[str] | None = None,
    matrix: list[list[float]] | None = None,
    style: str = 'business',
    animate: bool = False,
    loop: bool = False,
    fmt: Fmt | None = None,
    out: str | None = None,
    out_dir: str | None = None,
    horizontal: bool = False,
    trend: bool = False,
    total: bool = True,
    stacked: bool = False,
    percent: bool = False,
    bins: int | str | list[float] = 10,
    sample: int | None = None,
    lower: list[float] | None = None,
    upper: list[float] | None = None,
    starts: list[float] | None = None,
    ends: list[float] | None = None,
    slope: bool = False,
    hierarchy: dict[str, dict[str, float]] | list | None = None,
    links: list | None = None,
    numfmt: Literal['auto', 'plain', 'percent'] = 'auto',
    note: str | None = None,
    file: str | None = None,
    cat_col: str | None = None,
    col: str | None = None,
    sheet: str | None = None,
) -> str:
    if style not in THEMES:  # 入口即校验:错误主题不许静默兜底成 business 再回显假答案
        raise ToolError(f'未知主题 {style!r};可选:{", ".join(THEMES)}')
    bins = _bins(bins)  # hist 专用:整数 / 'auto' / 严格递增边界(非法给中文错)
    common: dict[str, Any] = dict(style=style, animate=animate, fmt=fmt, loop=loop,
                                  out=out, out_dir=out_dir, numfmt=numfmt, note=note)
    if type in ('line', 'area', 'line-multi'):  # sample 仅折线类支持
        common['sample'] = sample
    if type == 'line':  # 区间带仅单系列折线支持
        common['lower'], common['upper'] = lower, upper
    try:
        # stdio 协议独占 stdout:内核里"图表已生成"等打印必须让道,否则污染 JSON-RPC 流
        with contextlib.redirect_stdout(sys.stderr):
            if file is not None:  # 文件数据优先于内联参数(与 CLI --file 一致)
                return _from_file(type, title, file, cat_col, col, sheet, common,
                                  horizontal=horizontal, trend=trend, total=total,
                                  stacked=stacked, percent=percent, bins=bins, slope=slope)
            if type == 'area' and (series is not None or stacked or percent):
                # 多系列面积(可堆积):series 给出,或单系列误传堆积开关时给出指路错误
                if series is None:
                    raise ToolError('堆积面积图需要 series(多系列数据);'
                                    '单系列面积图无需 stacked / percent')
                _require(categories is not None, 'area 多系列需要 categories')
                return _result(_chart_fn('area')(title, categories,
                                                 series=_norm_series(series),
                                                 stacked=stacked, percent=percent,
                                                 **common),
                               type, style, animate)
            if type in _PAIR_TYPES:
                _require(categories is not None and values is not None,
                         'categories 与 values 不能为空')
                if type == 'bar':
                    return _result(_chart_fn('bar')(title, categories, values,
                                                    horizontal=horizontal, **common),
                                   type, style, animate)
                if type == 'waterfall':
                    return _result(_chart_fn('waterfall')(title, categories, values,
                                                          total=total, **common),
                                   type, style, animate)
                return _result(_chart_fn(type)(title, categories, values, **common),
                               type, style, animate)
            if type == 'combo':
                _require(categories is not None and values is not None
                         and line_values is not None,
                         'combo 需要 categories、values(柱值)与 line_values(线值)')
                return _result(_chart_fn('combo')(title, categories, values,
                                                  line_values, **common),
                               type, style, animate)
            if type in _SERIES_TYPES:
                _require(categories is not None and series is not None,
                         '多系列图需要 categories 与 series')
                extra = ({'stacked': stacked, 'percent': percent}
                         if type == 'bar-multi' else {})
                return _result(_chart_fn(type)(title, categories,
                                               _norm_series(series), **extra, **common),
                               type, style, animate)
            if type in ('box', 'violin'):
                _require(series is not None,
                         f'{type} 需要 series=[[组名, [样本...]], ...]')
                return _result(_chart_fn(type)(title, _norm_series(series), **common),
                               type, style, animate)
            if type in _XY_TYPES:
                _require(x is not None and y is not None, 'scatter/bubble 需要 x 与 y')
                if type == 'bubble':
                    _require(sizes is not None, 'bubble 需要 sizes')
                    return _result(_chart_fn('bubble')(title, x, y, sizes,
                                                       labels=labels, **common),
                                   type, style, animate)
                return _result(_chart_fn('scatter')(title, x, y, trend=trend,
                                                    labels=labels, **common),
                               type, style, animate)
            if type == 'hist':
                _require(values is not None, 'hist 需要 values(原始样本)')
                return _result(_chart_fn('hist')(title, values, bins=bins, **common),
                               type, style, animate)
            if type == 'heatmap':
                _require(rows is not None and cols is not None and matrix is not None,
                         'heatmap 需要 rows、cols 与 matrix')
                return _result(_chart_fn('heatmap')(title, rows, cols, matrix, **common),
                               type, style, animate)
            if type == 'gantt':
                _require(categories is not None and starts is not None
                         and ends is not None,
                         'gantt 需要 categories(任务名)、starts 与 ends')
                return _result(_chart_fn('gantt')(title, categories, starts, ends,
                                                  **common),
                               type, style, animate)
            if type == 'dumbbell':
                _require(categories is not None and series is not None,
                         'dumbbell 需要 categories 与 series')
                ss = _norm_series(series)
                _require(len(ss) == 2,
                         f'dumbbell 需要恰好 2 个系列(期初/期末),收到 {len(ss)} 个')
                return _result(_chart_fn('dumbbell')(title, categories, ss,
                                                     slope=slope, **common),
                               type, style, animate)
            if type == 'sankey':
                _require(links is not None,
                         'sankey 需要 links=[[源, 目标, 数值], ...]')
                return _result(_chart_fn('sankey')(title, links, **common),
                               type, style, animate)
            if type == 'sankey':
                _require(links is not None,
                         'sankey 需要 links=[[源, 目标, 数值], ...]')
                return _result(_chart_fn('sankey')(title, links, **common),
                               type, style, animate)
            if type == 'sunburst':
                _require(hierarchy is not None,
                         'sunburst 需要 hierarchy(两级层级数据,'
                         '如 {"水果": {"苹果": 30}})')
                return _result(_chart_fn('sunburst')(title, hierarchy, **common),
                               type, style, animate)
            raise ToolError(f'未知图表类型 {type!r},'
                            f'可选:{", ".join(get_args(ChartType))}')
    except (ValueError, RuntimeError, OSError) as e:  # 中文校验消息 → ToolError
        raise ToolError(str(e)) from e


def _from_file(type, title, file, cat_col, col, sheet, common, *, horizontal, trend,
               total, stacked, percent, bins, slope) -> str:
    """file 数据出图:列约定与 CLI --file 一致,数据转换复用 table.py。"""

    def done(path, type_name: str):
        return _result(path, type_name, common['style'], common['animate'])

    if type in ('bar', 'line'):
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(cols, 'file 至少需要 1 列数值')
        if len(cols) >= 2:  # 多数值列自动升级为多系列(与 CLI --file 一致)
            if type == 'bar':
                return done(_chart_fn('bar-multi')(title, cats, cols, stacked=stacked,
                                                   percent=percent, **common),
                            'bar-multi')
            # 区间带只对单系列折线有意义:必须摘掉 lower/upper 再调 line-multi,
            # 否则未知关键字 TypeError 裸穿 except(它不在中文转换的异常元组里)
            if common.get('lower') is not None or common.get('upper') is not None:
                raise ToolError('区间带 lower/upper 仅支持单系列折线;'
                                'file 含多列数值时会升级为多系列折线,'
                                '请用 col 指定其中 1 列')
            multi_common = {k: v for k, v in common.items()
                            if k not in ('lower', 'upper')}
            return done(_chart_fn('line-multi')(title, cats, cols, **multi_common),
                        'line-multi')
        if type == 'bar':
            return done(_chart_fn('bar')(title, cats, cols[0][1],
                                         horizontal=horizontal, **common), type)
        return done(_chart_fn('line')(title, cats, cols[0][1], name=cols[0][0],
                                      **common), type)
    if type == 'area':
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(cols, 'file 至少需要 1 列数值')
        if len(cols) >= 2:  # 多数值列自动升级为多系列面积(可堆积)
            return done(_chart_fn('area')(title, cats, series=cols, stacked=stacked,
                                          percent=percent, **common), 'area')
        return done(_chart_fn('area')(title, cats, cols[0][1], **common), type)
    if type in ('pie', 'donut', 'rose', 'treemap', 'waterfall', 'funnel', 'pareto'):
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(len(cols) == 1,
                 f'{type} 只支持 1 列数值,file 里有 {len(cols)} 列(可用 col 挑 1 列)')
        if type == 'waterfall':
            return done(_chart_fn('waterfall')(title, cats, cols[0][1],
                                               total=total, **common), type)
        return done(_chart_fn(type)(title, cats, cols[0][1], **common), type)
    if type == 'combo':
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(len(cols) == 2,
                 f'combo 的 file 需要 2 列数值(第 1 列柱值、第 2 列折线值),'
                 f'收到 {len(cols)} 列')
        return done(_chart_fn('combo')(title, cats, cols[0][1], cols[1][1], **common),
                    type)
    if type in _SERIES_TYPES:  # line-multi / bar-multi / radar:各数值列 = 一个系列
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(cols, 'file 至少需要 1 列数值')
        extra = {'stacked': stacked, 'percent': percent} if type == 'bar-multi' else {}
        return done(_chart_fn(type)(title, cats, cols, **extra, **common), type)
    if type in ('box', 'violin'):
        return done(_chart_fn(type)(title, file_box_groups(file, sheet), **common),
                    type)
    if type == 'hist':
        return done(_chart_fn('hist')(title, file_samples(file, sheet),
                                      bins=bins, **common), type)
    if type in _XY_TYPES:
        xs, ys, sizes, labels = file_xy(file, sizes=type == 'bubble', sheet=sheet)
        if type == 'bubble':
            _require(sizes, 'bubble 的 file 需要第 3 列气泡大小')
            return done(_chart_fn('bubble')(title, xs, ys, sizes, labels=labels,
                                            **common), type)
        return done(_chart_fn('scatter')(title, xs, ys, trend=trend, labels=labels,
                                         **common), type)
    if type == 'heatmap':
        rlabels, col_names, matrix = file_matrix(file, cat_col, sheet)
        return done(_chart_fn('heatmap')(title, rlabels, col_names, matrix, **common),
                    type)
    if type == 'gantt':  # 2 个数值列 = 开始、结束
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(len(cols) == 2,
                 f'gantt 的 file 需要 2 列数值(第 1 列开始、第 2 列结束),'
                 f'收到 {len(cols)} 列')
        return done(_chart_fn('gantt')(title, cats, cols[0][1], cols[1][1], **common),
                    type)
    if type == 'dumbbell':  # 2 个数值列 = 期初、期末
        cats, cols = file_columns(file, cat_col, col, sheet)
        _require(len(cols) == 2,
                 f'dumbbell 的 file 需要 2 列数值(期初、期末),收到 {len(cols)} 列')
        return done(_chart_fn('dumbbell')(title, cats, [cols[0], cols[1]],
                                          slope=slope, **common), type)
    if type == 'sankey':
        return done(_chart_fn('sankey')(title, file_links(file, sheet), **common),
                    type)
    if type == 'sunburst':
        raise ToolError('sunburst 暂不支持 file 数据(层级数据请用 hierarchy 内联参数)')
    raise ToolError(f'未知图表类型 {type!r},可选:{", ".join(get_args(ChartType))}')


def _result(path, chart_type: str, style: str, animated: bool) -> str:
    path = Path(path)
    return json.dumps({'path': str(path), 'file_size': path.stat().st_size,
                       'type': chart_type, 'style': style, 'animated': animated},
                      ensure_ascii=False)


@server.tool(
    name='list_themes',
    description=(
        'List the 15 available chart styles grouped in 4 packs (academic / business '
        '/ minimal-presentation / others). Returns one line per theme: '
        'key (use it as the "style" param of make_chart), Chinese label, '
        'and a one-line description. Default style is "business". '
        'preview=true additionally renders a montage image (every theme drawing '
        'the same mini bar chart) for visual comparison and returns its path; '
        'out_dir (optional, with preview=true) places that montage image in the '
        'given directory instead of the default output location.'
    ),
)
def list_themes(preview: bool = False, out_dir: str | None = None) -> str:
    lines = []
    for pack, members in THEME_PACKS.items():
        lines.append(f'[{pack}]')
        lines += [f'  {k} | {THEME_LABELS[k]} | {THEME_DESCS[k]}' for k in members]
    if preview:
        from .graph import themes_preview  # 延迟导入:纯文本的 list_themes 不拉起 matplotlib
        with contextlib.redirect_stdout(sys.stderr):
            path = themes_preview(out_dir=out_dir)
        lines.append(f'\n主题预览拼版图(每主题同一组迷你柱状图):{path}')
    return '\n'.join(lines)


def main() -> None:
    server.run()  # stdio


if __name__ == '__main__':
    main()
