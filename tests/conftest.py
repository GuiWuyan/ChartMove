"""共享 fixtures:动画测试轻量化。

48 帧全尺寸动画渲染是全量测试耗时的大头;默认把 core.FRAMES 降到 8 帧,
需要真实帧数做逐帧断言的专项测试,给参数加 full_animation 选择退出。
"""
import pytest

from chartgen import core

LIGHT_FRAMES = 8


@pytest.fixture
def full_animation():
    """选择退出轻量化:本测试以真实帧数渲染。"""


@pytest.fixture(autouse=True)
def _light_animation(request, monkeypatch):
    if 'full_animation' in request.fixturenames:
        return
    monkeypatch.setattr(core, 'FRAMES', LIGHT_FRAMES)
