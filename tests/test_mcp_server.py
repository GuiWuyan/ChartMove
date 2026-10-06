"""MCP 协议级测试(stdio + 官方客户端握手)。

xdist_group 单 worker 串行:Windows 的 Proactor spawn 并发建会话有概率性卡死
(第三方问题);会话模块级常驻,省去每次调用的握手开销。
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import sys
import threading
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

pytestmark = pytest.mark.xdist_group('mcp')

PARAMS = StdioServerParameters(command=sys.executable,
                               args=['-m', 'chartmove.mcp_server'])
# MCP 子进程 stderr 的去向:默认 errlog=sys.stderr 在 pytest 下是捕获对象(须带
# fileno 的真实流,故不能用 StringIO/内存缓冲),导到 devnull 免得污染输出
_DEVNULL = open(os.devnull, 'w', encoding='utf-8')


class _McpSession:
    """持有整个模块共用的 stdio 会话;调用经队列在常驻任务内串行执行。

    async with 的生命周期必须在同一任务内完成(anyio 任务亲和),所以由一个
    后台事件循环线程运行持有会话的 task;对外用 concurrent.futures.Future
    桥接(线程安全、可带超时阻塞),测试线程从不直接跨任务碰会话。
    """

    def __init__(self, timeout: float = 60):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._ready = threading.Event()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._task = self._loop.create_task(self._lifetime())
        if not self._ready.wait(timeout=timeout):
            # 超时先看 lifetime 任务是否已崩:把真实异常翻出来,别只留"初始化超时"
            if self._task.done():
                raise self._task.exception()
            raise RuntimeError('MCP 测试会话初始化超时(lifetime 任务仍在运行)')

    async def _lifetime(self):
        async with stdio_client(PARAMS, errlog=_DEVNULL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._tools = await session.list_tools()
                self._session = session
                self._ready.set()
                while True:
                    job = await self._queue.get()
                    if job is None:
                        break
                    await job()

    def _submit(self, factory, timeout: float = 300):
        """把 factory() 投递进常驻任务执行,阻塞至完成。"""
        cf: concurrent.futures.Future = concurrent.futures.Future()

        async def job():
            try:
                cf.set_result(await factory())
            except BaseException as e:
                cf.set_exception(e)

        async def put():
            await self._queue.put(job)

        asyncio.run_coroutine_threadsafe(put(), self._loop).result(timeout=30)
        return cf.result(timeout=timeout)

    def call(self, tool_args: dict, name: str = 'make_chart'):
        async def action():
            return await self._session.call_tool(name, tool_args)
        return self._submit(action)

    def close(self):
        on_done = threading.Event()
        self._task.add_done_callback(lambda _t: on_done.set())

        async def put_none():
            await self._queue.put(None)

        asyncio.run_coroutine_threadsafe(put_none(), self._loop).result(timeout=30)
        if not on_done.wait(timeout=120):
            raise RuntimeError('MCP 测试会话关闭超时')
        exc = self._task.exception()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=30)
        self._loop.close()
        if exc is not None:
            raise exc


_SESSION: _McpSession | None = None


@pytest.fixture(scope='module', autouse=True)
def _shared_session():
    """模块级常驻会话(P4-1):23 次 per-call 子进程 ≈ 40–70s 纯开销,复用后单文件 55s→17s。

    配合模块级 xdist_group('mcp') + CI 的 --dist loadgroup:本模块全部用例固定在
    同一 worker,会话只建一次,等价于已验证稳定的串行条件。会话初始化最多重试
    一次;两次都失败(极小概率的第三方 spawn 竞态)则放弃会话,回退到逐调用
    子进程模式(CI 的历史稳定路径)——最坏情况是慢,不是红。
    """
    global _SESSION
    for _ in range(2):
        try:
            _SESSION = _McpSession()
            break
        except Exception as e:  # noqa: BLE001 - 兜底路径必须接住任何初始化失败
            print(f'MCP 共享会话初始化失败,重试: {e!r}', file=sys.stderr)
            _SESSION = None
    yield
    if _SESSION is not None:
        _SESSION.close()
        _SESSION = None


def _call_oneoff(tool_args: dict, name: str) -> tuple:
    """逐调用子进程模式(共享会话不可用时的兜底):每次握手后即弃,稳健但慢。"""

    async def action(session):
        tools = await session.list_tools()
        result = await session.call_tool(name, tool_args)
        return tools, result

    async def runner():
        async with stdio_client(PARAMS, errlog=_DEVNULL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await asyncio.wait_for(action(session), timeout=120)

    return asyncio.run(asyncio.wait_for(runner(), timeout=300))


def _call(tool_args: dict, name: str = 'make_chart'):
    """复用常驻会话调用工具,返回 (tools, result);tools 在建会话时取一次。"""
    if _SESSION is None:
        return _call_oneoff(tool_args, name)
    return _SESSION._tools, _SESSION.call(tool_args, name)


def test_tools_listed():
    tools, _ = _call({}, name='list_themes')
    names = {t.name for t in tools.tools}
    assert names == {'make_chart', 'list_themes'}  # 工具面收敛为 2 个
    schema = next(t for t in tools.tools if t.name == 'make_chart').input_schema
    assert set(schema['properties']['type']['enum']) == {
        'bar', 'line', 'line-multi', 'area', 'pie', 'donut', 'combo', 'bar-multi',
        'radar', 'scatter', 'bubble', 'hist', 'box', 'violin', 'heatmap',
        'waterfall', 'funnel', 'rose', 'treemap', 'gantt', 'dumbbell', 'sankey',
        'sunburst', 'pareto'}


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


def test_violin_inline_and_constant_rejected(tmp_path):
    """violin 内联 series 出图;每组需 ≥2 个不同取值(KDE 零方差),中文 ToolError。"""
    _, result = _call({'type': 'violin', 'title': '分布',
                       'series': [['新', [3, 4, 3.5, 5, 4.8]], ['旧', [6, 7, 6.5, 8, 7.2]]],
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'violin'
    p = Path(data['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()

    _, result = _call({'type': 'violin', 'title': 't',
                       'series': [['g', [5, 5, 5]]], 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '2 个不同的取值' in result.content[0].text


def test_sankey_links_and_cycle_rejected(tmp_path):
    """sankey 内联 links 出图;循环流向与非法流量给中文 ToolError。"""
    _, result = _call({'type': 'sankey', 'title': '资金流向',
                       'links': [['收入', '支出', 300], ['收入', '储蓄', 200],
                                 ['储蓄', '投资', 120]],
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'sankey'
    p = Path(data['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()

    for bad, msg in (([['A', 'B', 10], ['B', 'A', 5]], '循环流向'),
                     ([['A', 'B', -3]], '需 > 0'),
                     ([['A', 'B']], '每项需为')):
        _, result = _call({'type': 'sankey', 'title': 't', 'links': bad,
                           'out_dir': str(tmp_path)})
        assert result.is_error
        assert msg in result.content[0].text


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


def test_make_chart_stacked_and_sunburst(tmp_path):
    """bar-multi 堆积 / 百分比堆积、area 多系列堆积、sunburst 层级数据与校验。"""
    _, result = _call({'type': 'bar-multi', 'title': '渠道堆积',
                       'categories': ['Q1', 'Q2'],
                       'series': [['线上', [120, 200]], ['门店', [80, 90]]],
                       'stacked': True, 'percent': True, 'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()

    _, result = _call({'type': 'area', 'title': '堆积面积',
                       'categories': ['Q1', 'Q2'],
                       'series': [['线上', [120, 200]], ['门店', [80, 90]]],
                       'stacked': True, 'out_dir': str(tmp_path)})
    assert not result.is_error
    Path(json.loads(result.content[0].text)['path']).unlink()

    _, result = _call({'type': 'sunburst', 'title': '层级占比',
                       'hierarchy': {'水果': {'苹果': 30, '香蕉': 20},
                                     '蔬菜': {'白菜': 10}},
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data['type'] == 'sunburst'
    p = Path(data['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()

    _, result = _call({'type': 'sunburst', 'title': '错', 'out_dir': str(tmp_path)})
    assert result.is_error
    assert 'hierarchy' in result.content[0].text

    _, result = _call({'type': 'pareto', 'title': '二八分析',
                       'categories': ['a', 'b', 'c'], 'values': [5, 3, 2],
                       'out_dir': str(tmp_path)})
    assert not result.is_error
    assert json.loads(result.content[0].text)['type'] == 'pareto'
    Path(json.loads(result.content[0].text)['path']).unlink()

    _, result = _call({'type': 'area', 'title': '错', 'categories': ['a'],
                       'values': [1], 'stacked': True, 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '需要 series' in result.content[0].text


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


def test_hist_bins_edges(tmp_path):
    """P1-2:bins 边界数组直达 np.histogram;乱序边界报中文错(不是英文 ValueError)。"""
    _, result = _call({'type': 'hist', 'title': 't', 'values': [1, 5, 12, 18, 25],
                       'bins': [1, 10, 20], 'out_dir': str(tmp_path)})
    assert not result.is_error
    p = Path(json.loads(result.content[0].text)['path'])
    assert p.exists() and p.stat().st_size > 0
    p.unlink()

    _, result = _call({'type': 'hist', 'title': 't', 'values': [1, 2, 3],
                       'bins': [5, 1], 'out_dir': str(tmp_path)})
    assert result.is_error
    assert '严格递增' in result.content[0].text


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
