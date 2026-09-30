"""验收测试:MCP Server 协议级实测(stdio 子进程 + 官方客户端握手)。

覆盖:tools/list 收敛为 2 个工具、make_chart 出图(静态 PNG 与动画 GIF,内联与
file 数据)、list_themes 内容、数据校验错误的中文 ToolError。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PARAMS = StdioServerParameters(command=sys.executable,
                               args=['-m', 'vizkit.mcp_server'])


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
        'funnel', 'rose', 'treemap', 'gantt', 'dumbbell'}


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


def test_invalid_style_rejected(tmp_path):
    """回归:拼错的 style 曾被静默当 business 使用,还在返回 JSON 里被确认。"""
    _, result = _call({'type': 'pie', 'title': 't', 'categories': ['a', 'b'],
                       'values': [3, 7], 'style': 'bussiness',
                       'out_dir': str(tmp_path)})
    assert result.is_error
    assert '未知主题' in result.content[0].text


def test_result_reports_requested_style(tmp_path):
    """返回 JSON 的 style 必须等于实际生效的主题(曾回显未生效的入参)。"""
    _, result = _call({'type': 'pie', 'title': 't', 'categories': ['a', 'b'],
                       'values': [3, 7], 'style': 'mckinsey',
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    assert json.loads(result.content[0].text)['style'] == 'mckinsey'


# ---------- file 数据(CSV / Excel 直读,列约定与 CLI --file 对齐) ----------

def _csv(tmp_path, text, name='d.csv'):
    p = tmp_path / name
    p.write_text(text, encoding='utf-8')
    return str(p)


def test_file_bar_single_col(tmp_path):
    f = _csv(tmp_path, '类目,销量\nQ1,120\nQ2,200\n')
    _, result = _call({'type': 'bar', 'title': '季度销量', 'file': f,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'bar'
    p = Path(data['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_file_bar_auto_upgrade(tmp_path):
    """多数值列自动升级为分组柱状图,返回的 type 如实报告。"""
    f = _csv(tmp_path, '类目,线上,门店\nQ1,120,80\nQ2,200,90\n')
    _, result = _call({'type': 'bar', 'title': '分组', 'file': f,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'bar-multi'
    assert Path(data['path']).stat().st_size > 0


def test_file_line_multi_col_upgrade(tmp_path):
    """回归:line + file 多数值列曾因 common 里的 lower/upper 关键字直接抛 TypeError
    (即使调用方没传区间带,common 也恒有 lower=None / upper=None)。"""
    f = _csv(tmp_path, '月份,线上,线下\n1月,120,80\n2月,200,90\n')
    _, result = _call({'type': 'line', 'title': '趋势', 'file': f,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'line-multi'
    p = Path(data['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_file_line_band_with_multi_col_rejected(tmp_path):
    """区间带只支持单系列折线:多列 + lower 必须给中文错误,不能是裸 TypeError
    (裸 TypeError 在 SDK 里只会变成无详情的 'Error executing tool make_chart')。"""
    f = _csv(tmp_path, '月份,线上,线下\n1月,120,80\n2月,200,90\n')
    _, result = _call({'type': 'line', 'title': 't', 'file': f,
                       'lower': [1, 2], 'upper': [3, 4], 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '区间带' in result.content[0].text


def test_file_combo_and_heatmap(tmp_path):
    f = _csv(tmp_path, '月份,销量,客单价\n1月,120,86\n2月,200,92\n')
    _, result = _call({'type': 'combo', 'title': '量价', 'file': f,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    assert Path(json.loads(result.content[0].text)['path']).exists()

    m = _csv(tmp_path, ',上午,下午\n周一,3,7\n周二,8,1\n', name='m.csv')
    _, result = _call({'type': 'heatmap', 'title': '热力', 'file': m,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_file_scatter_and_box(tmp_path):
    f = _csv(tmp_path, 'x,y\n1,4\n2,6\n3,5\n', name='xy.csv')
    _, result = _call({'type': 'scatter', 'title': '相关', 'file': f, 'trend': True,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    assert Path(json.loads(result.content[0].text)['path']).exists()

    b = _csv(tmp_path, '对照,实验\n3,2\n4,3\n5,4\n6,3\n', name='b.csv')
    _, result = _call({'type': 'box', 'title': 'AB', 'file': b,
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_file_col_picks_value_column(tmp_path):
    """pie 遇到 2 个数值列报错,用 col 挑 1 列后成功。"""
    f = _csv(tmp_path, '类目,线上,门店\nQ1,120,80\nQ2,200,90\n')
    _, result = _call({'type': 'pie', 'title': '占比', 'file': f,
                       'out_dir': str(tmp_path)})
    assert result.is_error
    assert 'col' in result.content[0].text

    _, result = _call({'type': 'pie', 'title': '占比', 'file': f, 'col': '门店',
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_file_missing_chinese_error(tmp_path):
    _, result = _call({'type': 'bar', 'title': 't',
                       'file': str(tmp_path / 'nope.csv'),
                       'out_dir': str(tmp_path)})
    assert result.is_error
    assert '文件不存在' in result.content[0].text


def test_file_sheet_and_rose(tmp_path):
    """sheet 按 Excel 工作表名取数;rose 走文件单数值列。"""
    op = pytest.importorskip('openpyxl')
    p = tmp_path / 'm.xlsx'
    wb = op.Workbook()
    wb.active.append(['类目', '销量'])
    wb.active.append(['Q1', 120])
    ws2 = wb.create_sheet('2024')
    ws2.append(['类目', '销量'])
    ws2.append(['手机', 320])
    ws2.append(['电脑', 210])
    wb.save(p)
    _, result = _call({'type': 'rose', 'title': '品类玫瑰', 'file': str(p),
                       'sheet': '2024', 'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'rose'
    assert Path(data['path']).stat().st_size > 0


def test_make_chart_new_types(tmp_path):
    """treemap 内联数据、dumbbell 两系列、dumbbell 系列数校验。"""
    _, result = _call({'type': 'treemap', 'title': '构成',
                       'categories': ['a', 'b', 'c'], 'values': [5, 3, 2],
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    assert json.loads(result.content[0].text)['type'] == 'treemap'

    _, result = _call({'type': 'dumbbell', 'title': '对比', 'categories': ['a', 'b'],
                       'series': [['2024', [1, 2]], ['2025', [3, 4]]],
                       'out_dir': str(tmp_path)})
    assert not result.is_error

    _, result = _call({'type': 'dumbbell', 'title': '错', 'categories': ['a'],
                       'series': [['s1', [1]]], 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '恰好 2 个系列' in result.content[0].text


def test_numfmt_and_note(tmp_path):
    """numfmt / note 透传:大数中文单位 + 脚注正常出图。"""
    _, result = _call({
        'type': 'bar', 'title': '大数', 'categories': ['a', 'b', 'c'],
        'values': [12345678, 23456789, 8901234], 'note': '数据来源:单元测试',
        'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()


def test_same_name_not_overwritten(tmp_path):
    """同名产物自动加序号:两次调用返回不同路径,两个文件都在。"""
    args = {'type': 'bar', 'title': 't', 'categories': ['a', 'b'],
            'values': [1, 2], 'out_dir': str(tmp_path)}
    _, r1 = _call(dict(args))
    _, r2 = _call(dict(args))
    p1 = json.loads(r1.content[0].text)['path']
    p2 = json.loads(r2.content[0].text)['path']
    assert p1 != p2 and Path(p1).exists() and Path(p2).exists()
    assert p2.removesuffix('.png').endswith('_2')
    Path(p1).unlink(), Path(p2).unlink()
