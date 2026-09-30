"""输出目录解析与文件命名。

输出目录持久化,绝不做 TTL 清理。
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
    """同名不覆盖:目标已存在时自动追加序号(bar_t.png → bar_t_2.png → _3 ...)。

    仅探测,不创建文件:exists() 与后续写入之间存在竞态,并发场景不保证唯一;
    真正落盘请用 claim_path(原子占位)。保留本函数用于命名预演与测试。
    """
    if not p.exists():
        return p
    i = 2
    while (cand := p.with_name(f'{p.stem}_{i}{p.suffix}')).exists():
        i += 1
    return cand


def claim_path(p: Path, limit: int = 10000) -> Path:
    """原子占位:并发下也保证"同名不覆盖"。

    与 next_path 的区别:next_path 只探测(存在竞态),claim_path 用
    O_CREAT|O_EXCL 真正把文件名抢下来 —— 先到者拿原名,后来者拿 _2/_3...
    返回已被占位的空文件路径,调用方负责写入内容;渲染失败时调用方须删除
    占位文件,否则留下 0 字节垃圾。
    """
    for i in range(1, limit + 1):
        cand = p if i == 1 else p.with_name(f'{p.stem}_{i}{p.suffix}')
        try:
            os.close(os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        return cand
    raise OSError(f'无法为 {p.name} 申请唯一文件名(已尝试 {limit} 个序号)')
