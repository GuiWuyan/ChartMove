"""table.py 单测:CSV(UTF-8 / GBK)与 Excel 读取、数值单元格清洗、各图表取数函数。"""
from __future__ import annotations

import pytest

from chartgen.table import (
    file_box_groups,
    file_columns,
    file_matrix,
    file_samples,
    file_xy,
    read_table,
    to_float,
)

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


def test_excel_sheet(tmp_path):
    """sheet 按工作表名或从 1 数的序号选择;缺省读第一个;CSV 误用报中文错。"""
    op = pytest.importorskip('openpyxl')
    p = tmp_path / 's.xlsx'
    wb = op.Workbook()
    wb.active.append(['类目', '销量'])
    wb.active.append(['一月', 120])
    ws2 = wb.create_sheet('2024')
    ws2.append(['类目', '销量'])
    ws2.append(['三月', 300])
    wb.save(p)
    assert read_table(p)[1] == [['一月', '120']]
    assert read_table(p, sheet='2024')[1] == [['三月', '300']]
    assert read_table(p, sheet='2')[1] == [['三月', '300']]
    with pytest.raises(ValueError, match='找不到工作表'):
        read_table(p, sheet='不存在')
    with pytest.raises(ValueError, match='超出范围'):
        read_table(p, sheet='9')
    with pytest.raises(ValueError, match='CSV 没有工作表概念'):
        read_table(_write(tmp_path, 't.csv', 'a,b\n1,2\n'), sheet='2024')


def test_unsupported_suffix(tmp_path):
    with pytest.raises(ValueError, match='不支持的表格格式'):
        read_table(tmp_path / 't.xls')


def test_to_float_tolerant():
    assert to_float('1,200') == 1200.0
    assert to_float(' 3.5 ') == 3.5
    with pytest.raises(ValueError, match='非数值单元格'):
        to_float('abc', '(列「销售额」)')


# ---------- 各图表取数函数(CLI --file 与 MCP file 共用) ----------

def test_file_columns(tmp_path):
    p = _write(tmp_path, 'c.csv', '月份,线上,门店\n1月,120,80\n2月,200,90\n')
    cats, cols = file_columns(p)
    assert cats == ['1月', '2月']
    assert cols == [('线上', [120.0, 200.0]), ('门店', [80.0, 90.0])]
    # cat_col / col 按表头名或从 1 数的序号选列
    cats2, cols2 = file_columns(p, cat_col='2', col='门店')
    assert cats2 == ['120', '200']
    assert cols2 == [('门店', [80.0, 90.0])]


def test_file_box_groups(tmp_path):
    p = _write(tmp_path, 'b.csv', '对照,实验\n3,2\n4,\n5,4\n')
    assert file_box_groups(p) == [('对照', [3.0, 4.0, 5.0]), ('实验', [2.0, 4.0])]


def test_file_xy(tmp_path):
    p = _write(tmp_path, 'xy.csv', 'x,y,size,名称\n1,4,10,甲\n2,6,,乙\n')
    xs, ys, sizes, labels = file_xy(p, sizes=True)
    assert (xs, ys) == ([1.0, 2.0], [4.0, 6.0])
    assert sizes == [10.0]  # 空单元格独立剔除,可能与 x/y 不对齐
    assert labels == ['甲', '乙']
    assert file_xy(p)[2] is None  # scatter 不读第 3 列


def test_file_samples_and_matrix(tmp_path):
    p = _write(tmp_path, 'h.csv', '样本\n12\n15\n18\n')
    assert file_samples(p) == [12.0, 15.0, 18.0]
    e = _write(tmp_path, 'e.csv', '样本\n')
    with pytest.raises(ValueError, match='数值样本'):
        file_samples(e)
    m = _write(tmp_path, 'm.csv', ',上午,下午\n周一,3,7\n周二,8,1\n')
    assert file_matrix(m) == (['周一', '周二'], ['上午', '下午'],
                              [[3.0, 7.0], [8.0, 1.0]])


def test_file_missing(tmp_path):
    with pytest.raises(ValueError, match='文件不存在'):
        read_table(tmp_path / 'nope.csv')
