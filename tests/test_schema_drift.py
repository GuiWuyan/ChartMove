"""三方一致性:CLI 子命令 / MCP 类型枚举 / core 公开函数。

新增图表类型时最容易漏接线(core 加了函数、CLI/MCP 忘加,或反之);此测试守住三方一致。
"""
from __future__ import annotations

EXPECTED = {'bar', 'line', 'line_multi', 'area', 'pie', 'donut', 'rose', 'treemap',
            'combo', 'bar_multi', 'radar', 'scatter', 'bubble', 'hist', 'box',
            'heatmap', 'waterfall', 'funnel', 'gantt', 'dumbbell'}


def test_chart_types_consistent_across_entries():
    from vizkit import core, mcp_server
    from vizkit.cli import _build_parser
    dashed = {t.replace('_', '-') for t in EXPECTED}
    # core:20 个公开绘图函数一个不缺
    assert {t for t in EXPECTED if callable(getattr(core, t, None))} == EXPECTED
    # CLI:子命令集合 = 20 类型 + themes(私有 API 取子命令名;若 argparse 内部变了再适配)
    sub = _build_parser()._subparsers._group_actions[0].choices
    assert set(sub) - {'themes'} == dashed
    # MCP:每个类型都能解析到可调用的绘图函数
    for t in dashed:
        assert callable(mcp_server._chart_fn(t))
