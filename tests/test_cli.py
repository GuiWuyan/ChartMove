"""验收测试:每种图表类型一条 CLI 命令出图 + themes 子命令 + 错误处理。

进程内调用 cli.main(argv)(退出码约定:0 成功 / 1 生成失败),
产物写入 pytest 临时目录并即测即删。
"""
from __future__ import annotations

import json

import pytest

from chartgen import cli

PAIRS = ['a=10', 'b=20', 'c=15']


def _run(tmp_path, *argv) -> None:
    assert cli.main([*argv, '--out-dir', str(tmp_path)]) == 0


def _expect_png(tmp_path, kind: str) -> None:
    f = tmp_path / f'{kind}_t.png'
    assert f.exists() and f.stat().st_size > 0
    f.unlink()


def _expect_file(tmp_path, filename: str) -> None:
    f = tmp_path / filename
    assert f.exists() and f.stat().st_size > 0, f'缺少产物 {filename}'
    f.unlink()


@pytest.mark.parametrize('name,argv', [
    ('bar', ('bar', 't', *PAIRS)),
    ('line', ('line', 't', *PAIRS)),
    ('area', ('area', 't', *PAIRS)),
    ('pie', ('pie', 't', *PAIRS)),
    ('donut', ('donut', 't', *PAIRS)),
    ('waterfall', ('waterfall', 't', 'a=10', 'b=-4', 'c=6')),
    ('funnel', ('funnel', 't', *PAIRS)),
    ('combo', ('combo', 't', *PAIRS, '--line', '5,8,6')),
    ('line-multi', ('line-multi', 't', '--categories', 'a,b,c', '--series',
                    json.dumps([['s1', [1, 2, 3]], ['s2', [4, 3, 2]]]))),
    ('bar-multi', ('bar-multi', 't', '--data',
                   json.dumps({'categories': ['a', 'b', 'c'],
                               'series': {'s1': [1, 2, 3], 's2': [4, 3, 2]}}))),
    ('radar', ('radar', 't', '--categories', 'a,b,c', '--series',
               json.dumps([['s1', [1, 2, 3]]]))),
    ('box', ('box', 't', '--series', json.dumps([['g1', [1, 2, 3, 4]],
                                                 ['g2', [5, 6, 7]]]))),
    ('scatter', ('scatter', 't', '--x', '1,2,3', '--y', '4,5,6', '--trend',
                 '--labels', '甲,乙,丙')),
    ('bubble', ('bubble', 't', '--x', '1,2', '--y', '3,4', '--sizes', '10,20')),
    ('hist', ('hist', 't', '1', '2', '2', '3', '3', '3', '--bins', '3')),
    ('heatmap', ('heatmap', 't', '--data',
                 json.dumps({'rows': ['r1', 'r2'], 'cols': ['c1', 'c2'],
                             'values': [[1, 2], [3, 4]]}))),
])
def test_cli_all_types(name, argv, tmp_path):
    """验收主体:16 种类型各一条命令出图。"""
    _run(tmp_path, *argv)
    _expect_png(tmp_path, name.replace('-', '_'))


def test_bar_horizontal_flag(tmp_path):
    _run(tmp_path, 'bar', 'Top 城市', '上海=30', '北京=25', '--horizontal')
    f = tmp_path / 'bar_Top_城市.png'
    assert f.exists() and f.stat().st_size > 0
    f.unlink()


def test_themes_subcommand(tmp_path, capsys):
    assert cli.main(['themes']) == 0
    out = capsys.readouterr().out
    assert '学术包' in out and 'business' in out and '麦肯锡风' in out


def test_bad_pairs_exit_1(tmp_path, capsys):
    assert cli.main(['bar', 't', 'bad-data', '--out-dir', str(tmp_path)]) == 1
    assert '类目=数值' in capsys.readouterr().err


def test_funnel_negative_exit_1(tmp_path, capsys):
    assert cli.main(['funnel', 't', 'a=-1', '--out-dir', str(tmp_path)]) == 1
    assert '漏斗图' in capsys.readouterr().err


def test_gif_via_cli(tmp_path):
    _run(tmp_path, 'bar', 't', 'a=1', 'b=2', '--animate')
    f = tmp_path / 'bar_t.gif'
    assert f.exists() and f.stat().st_size > 0
    assert b'NETSCAPE2.0' not in f.read_bytes()  # 默认播一遍停在末帧
    f.unlink()


def test_gif_loop_via_cli(tmp_path):
    _run(tmp_path, 'bar', 't', 'a=1', 'b=2', '--animate', '--loop')
    f = tmp_path / 'bar_t.gif'
    assert f.exists() and f.stat().st_size > 0
    assert b'NETSCAPE2.0' in f.read_bytes()
    f.unlink()


def test_loop_without_animate_exit_1(tmp_path, capsys):
    assert cli.main(['bar', 't', 'a=1', '--loop', '--out-dir', str(tmp_path)]) == 1
    assert 'loop' in capsys.readouterr().err


# ---------- --file:CSV / Excel 入参(M2.5) ----------

def _csv(tmp_path, name, text, encoding='utf-8'):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return p


def test_file_csv_bar(tmp_path):
    p = _csv(tmp_path, 's.csv', '类目,销量\nQ1,120\nQ2,200\n')
    _run(tmp_path, 'bar', '季度销量', '--file', str(p))
    _expect_file(tmp_path, 'bar_季度销量.png')


def test_file_csv_gbk_bar(tmp_path):
    p = _csv(tmp_path, 'gbk.csv', '类目,销量\n一月,100\n二月,200\n', encoding='gbk')
    _run(tmp_path, 'bar', '中文编码', '--file', str(p))
    _expect_file(tmp_path, 'bar_中文编码.png')


def test_file_csv_bar_auto_multi(tmp_path):
    p = _csv(tmp_path, 's.csv', '类目,线上,门店\nQ1,120,80\nQ2,200,90\n')
    _run(tmp_path, 'bar', '分组销量', '--file', str(p))
    f = tmp_path / 'bar_multi_分组销量.png'
    assert f.exists() and f.stat().st_size > 0
    f.unlink()


def test_file_csv_line_auto_multi(tmp_path):
    p = _csv(tmp_path, 's.csv', '月份,销售额,成本\n1月,10,8\n2月,20,12\n3月,30,15\n')
    _run(tmp_path, 'line', '趋势', '--file', str(p))
    f = tmp_path / 'line_multi_趋势.png'
    assert f.exists() and f.stat().st_size > 0
    f.unlink()


def test_file_xlsx_bar(tmp_path):
    op = pytest.importorskip('openpyxl')
    p = tmp_path / 's.xlsx'
    wb = op.Workbook()
    ws = wb.active
    ws.append(['类目', '销量'])
    ws.append(['Q1', 120])
    ws.append(['Q2', 200])
    wb.save(p)
    _run(tmp_path, 'bar', '季度销量', '--file', str(p))
    _expect_file(tmp_path, 'bar_季度销量.png')


def test_file_csv_heatmap(tmp_path):
    p = _csv(tmp_path, 'm.csv', ',上午,下午\n周一,3,7\n周二,8,1\n')
    _run(tmp_path, 'heatmap', '热力', '--file', str(p))
    _expect_file(tmp_path, 'heatmap_热力.png')


def test_file_csv_scatter(tmp_path):
    p = _csv(tmp_path, 'xy.csv', 'x,y\n1,4\n2,6\n3,5\n')
    _run(tmp_path, 'scatter', '相关', '--file', str(p), '--trend')
    _expect_file(tmp_path, 'scatter_相关.png')


def test_file_csv_box(tmp_path):
    p = _csv(tmp_path, 'b.csv', '对照,实验\n3,2\n4,3\n5,4\n6,3\n')
    _run(tmp_path, 'box', 'AB 测试', '--file', str(p))
    _expect_file(tmp_path, 'box_AB_测试.png')  # 标题中的空格被文件名清洗为下划线


def test_file_csv_hist(tmp_path):
    p = _csv(tmp_path, 'h.csv', '样本\n12\n15\n18\n22\n30\n25\n')
    _run(tmp_path, 'hist', '分布', '--file', str(p), '--bins', '3')
    _expect_file(tmp_path, 'hist_分布.png')


def test_file_col_and_cat_col(tmp_path):
    """--cat-col / --col 按表头名或序号选列;单列折线的图例名取列表头。"""
    p = _csv(tmp_path, 'f.csv', '代码,名称,收益率\n001,A,6.1\n002,B,-3.2\n003,C,12.5\n')
    _run(tmp_path, 'line', '选列', '--file', str(p), '--cat-col', '名称', '--col', '收益率')
    _expect_file(tmp_path, 'line_选列.png')
    _run(tmp_path, 'line', '选列', '--file', str(p), '--cat-col', '2',
         '--col', '3', '--out', '按序号')
    _expect_file(tmp_path, '按序号.png')


def test_file_multi_col_rejects_without_select(tmp_path, capsys):
    """未选列时多数值列类型报错并提示用 --col。"""
    p = _csv(tmp_path, 'f.csv', '类目,a,b\nx,1,2\ny,3,4\n')
    assert cli.main(['pie', 't', '--file', str(p), '--out-dir', str(tmp_path)]) == 1
    assert '--col' in capsys.readouterr().err
