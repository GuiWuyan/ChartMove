"""三方一致性:CLI 子命令 / MCP 类型枚举 / graph 公开函数,防新增类型漏接线。"""
from __future__ import annotations

EXPECTED = {'bar', 'line', 'line_multi', 'area', 'pie', 'donut', 'rose', 'treemap',
            'combo', 'bar_multi', 'radar', 'scatter', 'bubble', 'hist', 'box',
            'violin', 'heatmap', 'waterfall', 'funnel', 'gantt', 'dumbbell',
            'sankey', 'sunburst', 'pareto'}


def test_chart_types_consistent_across_entries():
    from chartmove import graph, mcp_server
    from chartmove.cli import _build_parser
    dashed = {t.replace('_', '-') for t in EXPECTED}
    # graph:24 个公开绘图函数一个不缺
    assert {t for t in EXPECTED if callable(getattr(graph, t, None))} == EXPECTED
    # CLI:子命令集合 = 24 类型 + themes(私有 API 取子命令名;若 argparse 内部变了再适配)
    sub = _build_parser()._subparsers._group_actions[0].choices
    assert set(sub) - {'themes'} == dashed
    # MCP:每个类型都能解析到可调用的绘图函数
    for t in dashed:
        assert callable(mcp_server._chart_fn(t))
