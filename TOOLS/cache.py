"""Cache/ 目录 TTL 清理（中间产物默认 3 天过期）。

两种用法：
1. 惰性清理——生成脚本开头调用，每次干活顺手清：
       from TOOLS.cache import clean_cache
       clean_cache()
2. 独立执行——配合定时任务每天兜底：
       .venv/Scripts/python.exe TOOLS/cache.py
"""
import shutil
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / 'Cache'
TTL_HOURS = 72  # 3*24，与 README/AGENTS.md 约定一致


def clean_cache(ttl_hours: int = TTL_HOURS) -> int:
    """删除 Cache/ 里最后修改时间超过 ttl_hours 的文件/目录，返回删除数量。

    目录按内部最新文件的时间判断，整体过期才删；被占用的条目跳过，留给下次。
    """
    if not CACHE_DIR.is_dir():
        return 0
    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for entry in CACHE_DIR.iterdir():
        try:
            if entry.is_dir():
                newest = max(
                    (p.stat().st_mtime for p in entry.rglob('*') if p.is_file()),
                    default=entry.stat().st_mtime,
                )
                if newest < cutoff:
                    shutil.rmtree(entry)
                    removed += 1
            elif entry.stat().st_mtime < cutoff:
                entry.unlink()
                removed += 1
        except OSError:
            continue  # 文件被占用等原因删不掉，下次再试
    return removed


if __name__ == '__main__':
    n = clean_cache()
    print(f'Cache/ 清理完成：删除 {n} 个过期条目')
