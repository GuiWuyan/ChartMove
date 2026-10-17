"""共享 fixtures:动画默认降到 8 帧,full_animation 标记选择退出轻量化。"""
import pytest

from chartmove.graph import render

LIGHT_FRAMES = 8


@pytest.fixture
def full_animation():
    """选择退出轻量化:本测试以真实帧数渲染。"""


@pytest.fixture(autouse=True)
def _light_animation(request, monkeypatch):
    if 'full_animation' in request.fixturenames:
        return
    monkeypatch.setattr(render, 'FRAMES', LIGHT_FRAMES)


def pytest_collection_modifyitems(config, items):
    """冒烟分层:重渲染用例自动打 slow 标记,测试文件无需手工维护清单。
    规则(命中其一即 slow):全速动画 fixture、名字含 gif/mp4/animated、
    全类型渲染矩阵(test_matrix_*)、MCP 会话文件(test_mcp_server.py)。
    CI 的 PR job 以 -m "not slow" 只跑冒烟;main push 与每周定时跑全量。"""
    for item in items:
        if ('full_animation' in item.fixturenames
                or item.path.name == 'test_mcp_server.py'
                or item.name.startswith('test_matrix')
                or any(k in item.name for k in ('gif', 'mp4', 'animated'))):
            item.add_marker(pytest.mark.slow)


# 进度显示稀疏化:pytest 失败/跳过/xfail 仍逐个显示;-v 等详细模式完全交还原生输出。
_session = None
_progress = {"seen": 0, "next": 0}


def pytest_sessionstart(session):
    global _session
    _session = session
    _progress.update(seen=0, next=0)


def pytest_report_teststatus(report, config):
    if report.when != 'call' or _session is None:
        return None
    total = _session.testscollected
    if config.get_verbosity(type(config).VERBOSITY_TEST_CASES) > 0 or not total:
        return None
    if not _progress["next"]:
        _progress["next"] = max(1, round(total / 20))
    _progress["seen"] += 1
    if report.outcome != 'passed' or hasattr(report, 'wasxfail'):
        return None  # F/E/s/x 交给 pytest 内置实现,不吞
    if _progress["seen"] < _progress["next"]:
        # word 必须非空:letter/word 全空会让该用例不计入进度百分比
        return "passed", "", "PASSED"
    _progress["next"] += max(1, round(total / 20))
    return "passed", f". [ {_progress['seen'] * 100 // total}%]", "PASSED"
