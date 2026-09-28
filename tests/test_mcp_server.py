"""验收测试:MCP Server 协议级实测(stdio 子进程 + 官方客户端握手)。

覆盖:tools/list 收敛为 2 个工具、make_chart 出图(静态 PNG 与动画 GIF)、
list_themes 内容、数据校验错误的中文 ToolError。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PARAMS = StdioServerParameters(command=sys.executable,
                               args=['-m', 'chartgen.mcp_server'])


def _call(tool_args: dict, name: str = 'make_chart'):
    """起子进程完成握手并调用工具,返回 (tools, result)。"""

    async def action(session):
        tools = await session.list_tools()
        result = await session.call_tool(name, tool_args)
        return tools, result

    async def runner():
        async with stdio_client(PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await action(session)

    return asyncio.run(runner())


def test_tools_listed():
    tools, _ = _call({}, name='list_themes')
    names = {t.name for t in tools.tools}
    assert names == {'make_chart', 'list_themes'}  # 工具面收敛为 2 个
    schema = next(t for t in tools.tools if t.name == 'make_chart').input_schema
    assert set(schema['properties']['type']['enum']) == {
        'bar', 'line', 'line-multi', 'area', 'pie', 'donut', 'combo', 'bar-multi',
        'radar', 'scatter', 'bubble', 'hist', 'box', 'heatmap', 'waterfall',
        'funnel'}


def test_make_chart_bar_png(tmp_path):
    _, result = _call({
        'type': 'bar', 'title': 'Q1-Q4 销售额',
        'categories': ['Q1', 'Q2', 'Q3', 'Q4'],
        'values': [120, 200, 90, 160],
        'style': 'cyberpunk', 'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'bar' and data['style'] == 'cyberpunk'
    assert data['animated'] is False
    p = Path(data['path'])
    assert p.is_absolute() and p.exists() and data['file_size'] == p.stat().st_size > 0
    p.unlink()


def test_make_chart_animated_gif(tmp_path):
    _, result = _call({
        'type': 'line', 'title': '增长', 'categories': ['1月', '2月', '3月'],
        'values': [10, 20, 15], 'animate': True, 'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['animated'] is True
    p = Path(data['path'])
    assert p.suffix == '.gif' and p.exists() and p.stat().st_size > 0
    p.unlink()


def test_make_chart_gif_loop(tmp_path):
    _, result = _call({
        'type': 'line', 'title': '循环', 'categories': ['1月', '2月', '3月'],
        'values': [10, 20, 15], 'animate': True, 'loop': True,
        'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert b'NETSCAPE2.0' in p.read_bytes()
    p.unlink()


def test_list_themes():
    _, result = _call({}, name='list_themes')
    assert not result.is_error
    text = result.content[0].text
    assert '学术包' in text and '商务包' in text
    assert 'business' in text and '麦肯锡风' in text and 'cyberpunk' in text


def test_validation_error_chinese(tmp_path):
    _, result = _call({
        'type': 'bar', 'title': 't', 'categories': ['Q1', 'Q2'],
        'values': [1, 2, 3], 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '长度一致' in result.content[0].text  # 中文报错,提示修数据重试
