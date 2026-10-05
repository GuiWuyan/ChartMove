"""输出目录解析与文件命名(产物持久化,绝不做 TTL 清理)。"""
from __future__ import annotations

import os
import re
from pathlib import Path

ENV_OUT_DIR = 'CHARTMOVE_OUT_DIR'
DEFAULT_DIR_NAME = 'Results'


def resolve_out_dir(out_dir=None) -> Path:
    """解析输出目录(不存在则创建):显式参数 > 环境变量 CHARTMOVE_OUT_DIR > ./Results/。"""
    if out_dir:
        p = Path(out_dir)
    elif os.environ.get(ENV_OUT_DIR):
        p = Path(os.environ[ENV_OUT_DIR])
    else:
        p = Path(DEFAULT_DIR_NAME)
    p = p.expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(
            f'无法创建输出目录「{p.resolve()}」:{e};目录可能被占用(杀软/同步盘/'
            f'资源管理器)或当前终端权限受限,请关闭占用后重试,'
            f'或用 --out-dir / out_dir= 换一个目录') from e
    return p.resolve()


def safe_stem(kind: str, title: str, out: str | None = None) -> str:
    """文件名清洗:"类型_标题"(或显式 out)去非法字符,截断 60 字符。"""
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', out or f'{kind}_{title}').strip('_')[:60]
    return stem or 'chart'


def next_path(p: Path) -> Path:
    """同名不覆盖的目标路径(追加 _2/_3);仅探测不占位,落盘请用 claim_path。"""
    if not p.exists():
        return p
    i = 2
    while (cand := p.with_name(f'{p.stem}_{i}{p.suffix}')).exists():
        i += 1
    return cand


def claim_path(p: Path, limit: int = 10000) -> Path:
    """原子占位(O_CREAT|O_EXCL)抢下文件名,并发下也同名不覆盖;
    返回已占位的空文件,调用方负责写入,渲染失败须删除占位文件。

    Windows 怪癖:已存在的隐藏/系统属性同名文件会让 O_EXCL 报 PermissionError
    而非 FileExistsError,此时换下一个序号;连续两个候选被拒视为目录级写入
    被安全软件过滤,报中文可操作错误。
    """
    last: PermissionError | None = None
    denied = 0
    for i in range(1, limit + 1):
        cand = p if i == 1 else p.with_name(f'{p.stem}_{i}{p.suffix}')
        try:
            os.close(os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        except PermissionError as e:
            last = e
            denied += 1
            if denied >= 2:
                break
            continue
        return cand
    if last is not None:
        raise RuntimeError(
            f'无法在「{p.parent}」创建文件「{p.name}」:{last};'
            '写入可能被安全软件/沙箱按程序或文件名过滤,'
            '请换一个输出目录(--out-dir / out_dir=)或将本程序加入安全软件白名单'
        ) from last
    raise OSError(f'无法为 {p.name} 申请唯一文件名(已尝试 {limit} 个序号)')
