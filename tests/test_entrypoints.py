"""入口点冒烟:子进程视角验证三个入口(P2-1 惰性 import 后,纯文本入口不拉起内核)。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _run(argv):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    return subprocess.run(argv, capture_output=True, text=True, encoding='utf-8',
                          env=env, timeout=120)


def test_cli_themes_via_module():
    """`python -m chartmove.cli themes` 只打印静态数据,应快且无需中文字体。"""
    out = _run([sys.executable, '-m', 'chartmove.cli', 'themes'])
    assert out.returncode == 0
    assert '学术包' in out.stdout and 'business' in out.stdout


def test_cli_version_flag():
    """P1-3 回归:--version 此前不存在,argparse 报「缺少 类型」。"""
    out = _run([sys.executable, '-m', 'chartmove.cli', '--version'])
    assert out.returncode == 0
    assert 'chartmove' in out.stdout


def test_cli_entry_point_installed():
    """控制台脚本入口(此前从未被任何测试调用过)。"""
    exe = shutil.which('chartmove')
    if not exe:
        import pytest
        pytest.skip('未安装 console script')
    out = _run([exe, 'themes'])
    assert out.returncode == 0


def test_mcp_server_importable():
    """MCP 入口可导入(登记在 pyproject 的 chartmove-mcp 指向它)。"""
    out = _run([sys.executable, '-c', 'import chartmove.mcp_server'])
    assert out.returncode == 0


def test_cli_piped_output_survives_non_utf8_locale():
    """PLAN §4-3 回归:非中文 locale 下管道输出此前在中文处 UnicodeEncodeError
    崩溃退出;现在 main 对非 tty 流降级为替换字符,退出码必须仍为 0。"""
    env = dict(os.environ, PYTHONIOENCODING='cp1252')
    out = subprocess.run([sys.executable, '-m', 'chartmove.cli', 'themes'],
                         capture_output=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr.decode('utf-8', errors='replace')
