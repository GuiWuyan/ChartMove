"""output.py 单测:目录优先级(out_dir > VIZKIT_OUT_DIR > ~/VizKit)、文件名清洗与同名不覆盖。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from vizkit.output import claim_path, next_path, resolve_out_dir, safe_stem


def test_priority_explicit_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv('VIZKIT_OUT_DIR', str(tmp_path / 'env'))
    explicit = tmp_path / 'explicit'
    assert resolve_out_dir(explicit) == explicit.resolve()
    assert explicit.is_dir()


def test_priority_env_over_default(tmp_path, monkeypatch):
    monkeypatch.setenv('VIZKIT_OUT_DIR', str(tmp_path / 'env'))
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    assert resolve_out_dir() == (tmp_path / 'env').resolve()


def test_default_results_dir(tmp_path, monkeypatch):
    monkeypatch.delenv('VIZKIT_OUT_DIR', raising=False)
    monkeypatch.chdir(tmp_path)  # 默认 ./Results/,相对当前工作目录
    assert resolve_out_dir() == (tmp_path / 'Results').resolve()
    assert (tmp_path / 'Results').is_dir()


def test_safe_stem():
    assert safe_stem('bar', 'Q1:销售/额') == 'bar_Q1_销售_额'
    assert safe_stem('bar', 'x' * 100) == 'bar_' + 'x' * 56  # 截断 60 字符
    assert safe_stem('bar', '///') == 'bar'  # 前缀保留,仅尾部下划线被剥掉
    assert safe_stem('bar', 't', out='///') == 'chart'  # 整体清洗为空才回退
    assert safe_stem('bar', 't', out='my_chart') == 'my_chart'


def test_next_path(tmp_path):
    """同名不覆盖:不存在原样返回;存在则 _2、_3 递增。"""
    p = tmp_path / 'bar_t.png'
    assert next_path(p) == p
    p.write_bytes(b'x')
    assert next_path(p) == tmp_path / 'bar_t_2.png'
    (tmp_path / 'bar_t_2.png').write_bytes(b'x')
    assert next_path(p) == tmp_path / 'bar_t_3.png'


def test_claim_path_serial_unique(tmp_path):
    """原子占位:重复占位拿唯一名字,先到者拿原名,后来者拿 _2/_3。"""
    p = tmp_path / 'same.png'
    claimed = [claim_path(p) for _ in range(5)]
    assert len(set(claimed)) == 5
    assert claimed[0] == p
    assert claimed[1] == tmp_path / 'same_2.png'
    assert all(c.exists() for c in claimed)  # 占位文件已创建


def test_claim_path_concurrent_unique(tmp_path):
    """回归:并发下"同名不覆盖"曾失效(8 进程写同名只落 1 个文件)。
    next_path 的探测与写入之间存在竞态;claim_path 用 O_CREAT|O_EXCL 原子占位。"""
    p = tmp_path / 'same.png'
    with ThreadPoolExecutor(8) as ex:
        claimed = list(ex.map(lambda _: claim_path(p), range(8)))
    assert len(set(claimed)) == 8


def test_claim_path_exhaustion(tmp_path):
    """序号耗尽(目录里已堆满同名序号)报 OSError,而不是静默覆盖。"""
    p = tmp_path / 'same.png'
    p.write_bytes(b'x')
    with pytest.raises(OSError, match='唯一文件名'):
        claim_path(p, limit=0)
