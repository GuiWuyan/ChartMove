"""fonts.py 单测:import vizkit 后字体环境即就绪(Windows 命中微软雅黑)。"""
from __future__ import annotations

import sys

import pytest
from matplotlib import rcParams

from vizkit import fonts


def test_rcparams_ready():
    assert rcParams['axes.unicode_minus'] is False
    assert rcParams['font.size'] == 14


def test_windows_font():
    if sys.platform != 'win32':
        pytest.skip('仅 Windows 校验微软雅黑')
    assert fonts.FAMILY == 'Microsoft YaHei'
