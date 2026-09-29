"""共享 fixtures:动画测试轻量化。

48 帧全尺寸动画渲染是全量测试耗时的大头;默认把 core.FRAMES 降到 8 帧,
需要真实帧数做逐帧断言的专项测试,给参数加 full_animation 选择退出。
"""
import pytest

from vizkit import core

LIGHT_FRAMES = 8


@pytest.fixture
def full_animation():
    """选择退出轻量化:本测试以真实帧数渲染。"""


@pytest.fixture(autouse=True)
def _light_animation(request, monkeypatch):
    if 'full_animation' in request.fixturenames:
        return
    monkeypatch.setattr(core, 'FRAMES', LIGHT_FRAMES)


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
