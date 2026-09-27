"""table.py 单测:CSV(UTF-8 / GBK)与 Excel 读取、数值单元格清洗。"""
from __future__ import annotations

import pytest

from chartgen.table import read_table, to_float

CSV_UTF8 = '类目,销售额,成本\n1月,"1,200",800\n2月,"3,400","1,100"\n'
CSV_GBK = '类目,销售额\n一月,100\n二月,200\n'


def _write(tmp_path, name: str, text: str, encoding='utf-8'):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return p


def test_csv_utf8(tmp_path):
    p = _write(tmp_path, 't.csv', CSV_UTF8)
    header, rows = read_table(p)
    assert header == ['类目', '销售额', '成本']
    assert rows == [['1月', '1,200', '800'], ['2月', '3,400', '1,100']]


def test_csv_gbk(tmp_path):
    p = _write(tmp_path, 'gbk.csv', CSV_GBK, encoding='gbk')  # Excel 中文导出常见编码
    header, rows = read_table(p)
    assert header == ['类目', '销售额']
    assert rows == [['一月', '100'], ['二月', '200']]


def test_excel_xlsx(tmp_path):
    op = pytest.importorskip('openpyxl')
    p = tmp_path / 't.xlsx'
    wb = op.Workbook()
    ws = wb.active
    ws.append(['类目', '销量'])
    ws.append(['一月', 120])
    ws.append(['二月', 200])
    wb.save(p)
    header, rows = read_table(p)
    assert header == ['类目', '销量']
    assert rows == [['一月', '120'], ['二月', '200']]


def test_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match='不支持的表格格式'):
        read_table(tmp_path / 't.xls')


def test_to_float_tolerant():
    assert to_float('1,200') == 1200.0
    assert to_float(' 3.5 ') == 3.5
    with pytest.raises(ValueError, match='非数值单元格'):
        to_float('abc', '(列「销售额」)')
