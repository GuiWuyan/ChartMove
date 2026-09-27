"""表格文件读取:CSV / Excel → 表头 + 行数据,供 CLI --file 与后续 MCP 使用。

CSV 兼容 UTF-8(-sig)与 GBK(Excel 中文导出常见);Excel 仅支持 .xlsx / .xlsm。
首行一律视为表头。
"""
from __future__ import annotations

import csv
from pathlib import Path

__all__ = ['read_table', 'to_float']


def read_table(path: str | Path) -> tuple[list[str], list[list[str]]]:
    """读取表格,返回 (表头, 数据行);空行剔除,单元格已去空白。"""
    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        header, rows = _read_csv(path)
    elif suffix in ('.xlsx', '.xlsm'):
        header, rows = _read_excel(path)
    else:
        raise ValueError(f'不支持的表格格式 {suffix!r}(支持 .csv / .xlsx)')
    if not header:
        raise ValueError('表格为空')
    return header, rows


def to_float(cell, where: str = '') -> float:
    """单元格转数值:容忍千分位逗号与空白;失败时报出位置便于定位。"""
    text = str(cell).replace(',', '').strip()
    try:
        return float(text)
    except ValueError as e:
        raise ValueError(f'数值列出现非数值单元格: {cell!r}{where}') from e


def _read_csv(path) -> tuple[list[str], list[list[str]]]:
    raw = Path(path).read_bytes()
    for enc in ('utf-8-sig', 'gbk'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('CSV 编码无法识别(支持 UTF-8 / GBK)')
    rows = [r for r in csv.reader(text.splitlines()) if any(c.strip() for c in r)]
    if not rows:
        return [], []
    return [c.strip() for c in rows[0]], [[c.strip() for c in r] for r in rows[1:]]


def _read_excel(path) -> tuple[list[str], list[list[str]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as e:  # 延迟导入:纯 CSV 用户无需 openpyxl
        raise ValueError('读取 Excel 需要安装 openpyxl') from e
    ws = load_workbook(path, read_only=True, data_only=True).active
    rows = [['' if v is None else str(v).strip() for v in row]
            for row in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return [], []
    return rows[0], rows[1:]
