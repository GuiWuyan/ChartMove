"""MCP Server 入口(M3):把 chartgen 暴露给 AI / agent,stdio 传输。

工具面收敛为 2 个(docs/plan.md 5.3):
    make_chart   生成图表,返回 JSON {path(绝对路径), file_size, type, style, animated}
    list_themes  列出 13 主题 × 4 风格包(名称 + 一句话描述)

约定:工具 schema 描述用英文(LLM 选工具靠它);数据校验错误转 ToolError,消息保持中文;
返回的 path 即交付物,桌宠/host 只需展示该文件;animate=true 默认出 GIF。
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

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
from .themes import THEME_DESCS, THEME_LABELS, THEME_PACKS

ChartType = Literal[
    'bar', 'line', 'line-multi', 'area', 'pie', 'donut', 'combo', 'bar-multi',
    'radar', 'scatter', 'bubble', 'hist', 'box', 'heatmap', 'waterfall', 'funnel']
Fmt = Literal['png', 'pdf', 'tif', 'gif', 'mp4']

_CHART_FNS = {
    'bar': bar, 'line': line, 'line-multi': line_multi, 'area': area, 'pie': pie,
    'donut': donut, 'combo': combo, 'bar-multi': bar_multi, 'radar': radar,
    'scatter': scatter, 'bubble': bubble, 'hist': hist, 'box': box,
    'heatmap': heatmap, 'waterfall': waterfall, 'funnel': funnel,
}
_PAIR_TYPES = ('bar', 'line', 'area', 'pie', 'donut', 'waterfall', 'funnel')
_SERIES_TYPES = ('line-multi', 'bar-multi', 'radar')
_XY_TYPES = ('scatter', 'bubble')

server = MCPServer(
    name='chartgen',
    version='0.1.0',
    instructions=(
        'Chinese chart generator: 16 chart types x 13 themes, no font configuration '
        'needed, output is a persistent file. Use list_themes to discover styles. '
        'Call make_chart with the data; the returned "path" (absolute path to the '
        'image file) IS the deliverable - show/link that file to the user. '
        'Set animate=true to get a GIF that plays once and stops on the last frame '
        '(chat-window friendly); use static png for documents. Errors are reported '
        'in Chinese and mean the data was invalid - fix the data and retry.'
    ),
)


def _require(cond, message: str) -> None:
    if not cond:
        raise ToolError(message)


def _norm_series(series) -> list[tuple[str, list[float]]]:
    """series 规范为 [(名称, 数值列表), ...];接受 [[名, [值..]], ...] 或 {名: [值..]}。"""
    items = series.items() if isinstance(series, dict) else series
    return [(str(nm), [float(v) for v in vals]) for nm, vals in items]


@server.tool(
    name='make_chart',
    description=(
        'Generate a chart image with Chinese fonts preconfigured. '
        'Returns JSON string: {path (absolute path, THE deliverable), file_size, '
        'type, style, animated}. Data params by type - '
        'category charts (bar/line/line-multi/area/pie/donut/combo/bar-multi/radar/'
        'waterfall/funnel): categories + values, or series=[[name, [values]], ...] '
        'for multi-series (combo also needs line_values); '
        'scatter/bubble: x + y (+sizes for bubble, +labels optional); '
        'hist: values = raw samples; box: series = [[group_name, [samples]], ...]; '
        'heatmap: rows + cols + matrix (2-D numeric). '
        'animate=true gives a GIF (plays once, stops on last frame); '
        'fmt chooses png/pdf/tif for static or gif/mp4 for animated. '
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
    fmt: Fmt | None = None,
    out: str | None = None,
    out_dir: str | None = None,
    horizontal: bool = False,
    trend: bool = False,
    total: bool = True,
    bins: int | str = 10,
) -> str:
    common: dict[str, Any] = dict(style=style, animate=animate, fmt=fmt, out=out,
                                  out_dir=out_dir)
    try:
        # stdio 协议独占 stdout:内核里"图表已生成"等打印必须让道,否则污染 JSON-RPC 流
        with contextlib.redirect_stdout(sys.stderr):
            if type in _PAIR_TYPES:
                _require(categories is not None and values is not None,
                         'categories 与 values 不能为空')
                if type == 'bar':
                    return _result(bar(title, categories, values,
                                       horizontal=horizontal, **common), type, style,
                                   animate)
                if type == 'waterfall':
                    return _result(waterfall(title, categories, values, total=total,
                                             **common), type, style, animate)
                return _result(_CHART_FNS[type](title, categories, values, **common),
                               type, style, animate)
            if type == 'combo':
                _require(categories is not None and values is not None
                         and line_values is not None,
                         'combo 需要 categories、values(柱值)与 line_values(线值)')
                return _result(combo(title, categories, values, line_values, **common),
                               type, style, animate)
            if type in _SERIES_TYPES:
                _require(categories is not None and series is not None,
                         '多系列图需要 categories 与 series')
                return _result(_CHART_FNS[type](title, categories,
                                                _norm_series(series), **common),
                               type, style, animate)
            if type == 'box':
                _require(series is not None,
                         'box 需要 series=[[组名, [样本...]], ...]')
                return _result(box(title, _norm_series(series), **common),
                               type, style, animate)
            if type in _XY_TYPES:
                _require(x is not None and y is not None, 'scatter/bubble 需要 x 与 y')
                if type == 'bubble':
                    _require(sizes is not None, 'bubble 需要 sizes')
                    return _result(bubble(title, x, y, sizes, labels=labels, **common),
                                   type, style, animate)
                return _result(scatter(title, x, y, trend=trend, labels=labels,
                                       **common), type, style, animate)
            if type == 'hist':
                _require(values is not None, 'hist 需要 values(原始样本)')
                return _result(hist(title, values, bins=bins, **common),
                               type, style, animate)
            if type == 'heatmap':
                _require(rows is not None and cols is not None and matrix is not None,
                         'heatmap 需要 rows、cols 与 matrix')
                return _result(heatmap(title, rows, cols, matrix, **common),
                               type, style, animate)
            raise ToolError(f'未知图表类型 {type!r},可选:{", ".join(_CHART_FNS)}')
    except (ValueError, RuntimeError) as e:  # 中文校验消息 → ToolError
        raise ToolError(str(e)) from e


def _result(path, chart_type: str, style: str, animated: bool) -> str:
    path = Path(path)
    return json.dumps({'path': str(path), 'file_size': path.stat().st_size,
                       'type': chart_type, 'style': style, 'animated': animated},
                      ensure_ascii=False)


@server.tool(
    name='list_themes',
    description=(
        'List the 13 available chart styles grouped in 4 packs (academic / business '
        '/ minimal-presentation / others). Returns one line per theme: '
        'key (use it as the "style" param of make_chart), Chinese label, '
        'and a one-line description. Default style is "business".'
    ),
)
def list_themes() -> str:
    lines = []
    for pack, members in THEME_PACKS.items():
        lines.append(f'[{pack}]')
        lines += [f'  {k} | {THEME_LABELS[k]} | {THEME_DESCS[k]}' for k in members]
    return '\n'.join(lines)


def main() -> None:
    server.run()  # stdio


if __name__ == '__main__':
    main()
