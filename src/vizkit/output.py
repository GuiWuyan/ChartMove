"""输出目录解析与文件命名。

约定(docs/plan.md 第 4 节):输出目录持久化,绝不做 TTL 清理。
优先级:显式 out_dir 参数 > 环境变量 VIZKIT_OUT_DIR > 默认 ./Results/(相对当前
工作目录,项目内持久;桌宠等 CWD 不可预期的场景请设 VIZKIT_OUT_DIR)。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ENV_OUT_DIR = 'VIZKIT_OUT_DIR'
DEFAULT_DIR_NAME = 'Results'


def resolve_out_dir(out_dir=None) -> Path:
    """解析输出目录(不存在则创建),返回绝对路径。"""
    if out_dir:
        p = Path(out_dir)
    elif os.environ.get(ENV_OUT_DIR):
        p = Path(os.environ[ENV_OUT_DIR])
    else:
        p = Path(DEFAULT_DIR_NAME)
    p = p.expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def safe_stem(kind: str, title: str, out: str | None = None) -> str:
    """文件名清洗:"类型_标题"(或显式 out)去非法字符,截断 60 字符。"""
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', out or f'{kind}_{title}').strip('_')[:60]
    return stem or 'chart'


def next_path(p: Path) -> Path:
    """同名不覆盖:目标已存在时自动追加序号(bar_t.png → bar_t_2.png → _3 ...)。"""
    if not p.exists():
        return p
    i = 2
    while (cand := p.with_name(f'{p.stem}_{i}{p.suffix}')).exists():
        i += 1
    return cand
