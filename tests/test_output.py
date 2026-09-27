"""output.py 单测:目录优先级(out_dir > CHARTGEN_OUT_DIR > ~/ChartGen)与文件名清洗。"""
from __future__ import annotations

from chartgen.output import resolve_out_dir, safe_stem


def test_priority_explicit_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv('CHARTGEN_OUT_DIR', str(tmp_path / 'env'))
    explicit = tmp_path / 'explicit'
    assert resolve_out_dir(explicit) == explicit.resolve()
    assert explicit.is_dir()


def test_priority_env_over_default(tmp_path, monkeypatch):
    monkeypatch.setenv('CHARTGEN_OUT_DIR', str(tmp_path / 'env'))
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    assert resolve_out_dir() == (tmp_path / 'env').resolve()


def test_default_results_dir(tmp_path, monkeypatch):
    monkeypatch.delenv('CHARTGEN_OUT_DIR', raising=False)
    monkeypatch.chdir(tmp_path)  # 默认 ./Results/,相对当前工作目录
    assert resolve_out_dir() == (tmp_path / 'Results').resolve()
    assert (tmp_path / 'Results').is_dir()


def test_safe_stem():
    assert safe_stem('bar', 'Q1:销售/额') == 'bar_Q1_销售_额'
    assert safe_stem('bar', 'x' * 100) == 'bar_' + 'x' * 56  # 截断 60 字符
    assert safe_stem('bar', '///') == 'bar'  # 前缀保留,仅尾部下划线被剥掉
    assert safe_stem('bar', 't', out='///') == 'chart'  # 整体清洗为空才回退
    assert safe_stem('bar', 't', out='my_chart') == 'my_chart'
