"""CLI 验收:每类型一条命令出图 + themes 子命令 + 错误处理(即测即删)。"""
from __future__ import annotations

import json

import pytest

from chartmove import cli

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
    ('rose', ('rose', 't', *PAIRS)),
    ('treemap', ('treemap', 't', *PAIRS)),
    ('waterfall', ('waterfall', 't', 'a=10', 'b=-4', 'c=6')),
    ('pareto', ('pareto', 't', *PAIRS)),
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
    ('violin', ('violin', 't', '--series', json.dumps([['g1', [1, 2, 3, 4]],
                                                       ['g2', [5, 6, 7]]]))),
    ('scatter', ('scatter', 't', '--x', '1,2,3', '--y', '4,5,6', '--trend',
                 '--labels', '甲,乙,丙')),
    ('bubble', ('bubble', 't', '--x', '1,2', '--y', '3,4', '--sizes', '10,20')),
    ('hist', ('hist', 't', '1', '2', '2', '3', '3', '3', '--bins', '3')),
    ('heatmap', ('heatmap', 't', '--data',
                 json.dumps({'rows': ['r1', 'r2'], 'cols': ['c1', 'c2'],
                             'values': [[1, 2], [3, 4]]}))),
    ('gantt', ('gantt', 't', '--categories', 'a,b,c', '--starts', '1,3,5',
               '--ends', '4,6,9')),
    ('dumbbell', ('dumbbell', 't', '--categories', 'a,b,c', '--series',
                  json.dumps([['2024', [1, 2, 3]], ['2025', [2, 3, 4]]]))),
    ('sunburst', ('sunburst', 't', '--data',
                  json.dumps({'水果': {'苹果': 30, '香蕉': 20},
                              '蔬菜': {'白菜': 10}}))),
    ('sankey', ('sankey', 't', '--data',
                json.dumps({'links': [['收入', '支出', 300],
                                      ['收入', '储蓄', 200],
                                      ['储蓄', '投资', 120]]}))),
])
def test_cli_all_types(name, argv, tmp_path):
    """验收主体:22 种类型各一条命令出图。"""
    _run(tmp_path, *argv)
    _expect_png(tmp_path, name.replace('-', '_'))


def test_bar_multi_stacked_flags(tmp_path):
    """--stacked / --percent 透传:堆积与百分比堆积柱状图出图。"""
    _run(tmp_path, 'bar-multi', '堆积', '--categories', 'a,b,c', '--series',
         json.dumps([['s1', [1, 2, 3]], ['s2', [4, 3, 2]]]), '--stacked')
    _expect_file(tmp_path, 'bar_multi_堆积.png')
    _run(tmp_path, 'bar-multi', '占比', '--data',
         json.dumps({'categories': ['a', 'b'],
                     'series': {'s1': [1, 2], 's2': [3, 4]}}), '--percent')
    _expect_file(tmp_path, 'bar_multi_占比.png')


def test_area_stacked_flags(tmp_path, capsys):
    """area 多系列:--series 叠加 / --stacked 堆积 / --file 多数值列自动升级。"""
    _run(tmp_path, 'area', '叠加', '--categories', 'a,b,c', '--series',
         json.dumps([['s1', [1, 2, 3]], ['s2', [4, 3, 2]]]))
    _expect_file(tmp_path, 'area_叠加.png')
    _run(tmp_path, 'area', '堆积', '--data',
         json.dumps({'categories': ['a', 'b'],
                     'series': {'s1': [1, 2], 's2': [3, 4]}}), '--stacked', '--percent')
    _expect_file(tmp_path, 'area_堆积.png')
    p = _csv(tmp_path, 'a.csv', '月份,线上,门店\n1月,10,8\n2月,20,12\n')
    _run(tmp_path, 'area', '自动升级', '--file', str(p), '--stacked')
    _expect_file(tmp_path, 'area_自动升级.png')
    assert cli.main(['area', 't', 'a=1', '--stacked', '--out-dir', str(tmp_path)]) == 1
    assert '需要多系列' in capsys.readouterr().err


def test_sunburst_errors(tmp_path, capsys):
    """sunburst:缺 --data 与误用 --file 都报中文错。"""
    assert cli.main(['sunburst', 't', '--out-dir', str(tmp_path)]) == 1
    assert '--data' in capsys.readouterr().err
    p = _csv(tmp_path, 'h.csv', '父,子,值\n水果,苹果,30\n')
    assert cli.main(['sunburst', 't', '--file', str(p),
                     '--out-dir', str(tmp_path)]) == 1
    assert '不支持 --file' in capsys.readouterr().err


def test_bar_horizontal_flag(tmp_path):
    _run(tmp_path, 'bar', 'Top 城市', '上海=30', '北京=25', '--horizontal')
    f = tmp_path / 'bar_Top_城市.png'
    assert f.exists() and f.stat().st_size > 0
    f.unlink()


def test_line_band_flag(tmp_path):
    _run(tmp_path, 'line', '预测', '1月=120', '2月=135', '3月=128',
         '--lower', '112,125,116', '--upper', '128,145,140')
    _expect_file(tmp_path, 'line_预测.png')


def test_line_band_args_reach_core(tmp_path, monkeypatch):
    """回归:--lower/--upper 必须透传给 graph.line(曾止步 argparse,区间带静默丢失)。"""
    from chartmove import graph
    got = {}
    real = graph.line

    def spy(title, cats, vals, **kw):
        got.update(kw)
        return real(title, cats, vals, **kw)

    monkeypatch.setattr(graph, 'line', spy)  # runner 出图时经 _chart_fn 读 graph 属性
    assert cli.main(['line', '预测', '1月=120', '2月=135', '3月=128',
                     '--lower', '112,125,116', '--upper', '128,145,140',
                     '--out-dir', str(tmp_path)]) == 0
    assert got['lower'] == [112.0, 125.0, 116.0]
    assert got['upper'] == [128.0, 145.0, 140.0]
    (tmp_path / 'line_预测.png').unlink()


def test_line_band_rejected_for_multi_series_file(tmp_path):
    """--file 多数值列升级多系列折线时不接受区间带(报中文错,不是 TypeError)。"""
    f = _csv(tmp_path, 'm.csv', '月份,实际,预测\n1月,120,112\n2月,135,125\n')
    assert cli.main(['line', 't', '--file', str(f),
                     '--lower', '1,2', '--upper', '3,4',
                     '--out-dir', str(tmp_path)]) == 1


def test_waterfall_no_total_reaches_core(tmp_path, monkeypatch):
    """回归:--no-total 曾是空参数(total=False 与 True 产物逐字节相同)。"""
    from chartmove import graph
    got = {}
    real = graph.waterfall

    def spy(title, cats, vals, **kw):
        got.update(kw)
        return real(title, cats, vals, **kw)

    monkeypatch.setattr(graph, 'waterfall', spy)
    assert cli.main(['waterfall', 't', 'a=10', 'b=-4', 'c=6', '--no-total',
                     '--out-dir', str(tmp_path)]) == 0
    assert got['total'] is False
    (tmp_path / 'waterfall_t.png').unlink()


def test_gantt_dumbbell_file(tmp_path):
    """--file 的 2 个数值列:甘特图 = 开始/结束,哑铃图 = 期初/期末。"""
    g = _csv(tmp_path, 'g.csv', '任务,开始,结束\n需求,1,5\n开发,4,11\n')
    _run(tmp_path, 'gantt', '排期', '--file', str(g))
    _expect_file(tmp_path, 'gantt_排期.png')
    d = _csv(tmp_path, 'd.csv', '渠道,2024,2025\n官网,3.2,4.1\n门店,5.1,4.8\n')
    _run(tmp_path, 'dumbbell', '对比', '--file', str(d), '--slope')
    _expect_file(tmp_path, 'dumbbell_对比.png')


def test_themes_subcommand(tmp_path, capsys):
    assert cli.main(['themes']) == 0
    out = capsys.readouterr().out
    assert '学术包' in out and 'business' in out and '麦肯锡风' in out


def test_themes_preview(tmp_path):
    _run(tmp_path, 'themes', '--preview')
    _expect_file(tmp_path, 'themes_预览.png')


def test_bad_pairs_exit_1(tmp_path, capsys):
    assert cli.main(['bar', 't', 'bad-data', '--out-dir', str(tmp_path)]) == 1
    assert '类目=数值' in capsys.readouterr().err


def test_bad_number_error_is_chinese(tmp_path, capsys):
    """P1-1 回归:数值解析失败曾把英文原味异常(could not convert ...)拼进错误消息。"""
    assert cli.main(['bar', 't', 'Q1=abc', '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert 'could not convert' not in err and '需要数值' in err

    assert cli.main(['scatter', 't', '--x', '1,2,zz', '--y', '1,2,3',
                     '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert 'could not convert' not in err and '需要数值' in err

    assert cli.main(['bar', 't', '--data', '{"categories":["a"],"values":["x"]}',
                     '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert 'could not convert' not in err and '需要数值' in err

    assert cli.main(['line-multi', 't', '--categories', 'a,b', '--series',
                     '[["s", [1, "x"]]]', '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert 'could not convert' not in err and '系列「s」' in err

    assert cli.main(['line', 't', 'a=1', '--figsize', '宽x高',
                     '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert 'could not convert' not in err and '需要数值' in err


def test_hist_bins_edges(tmp_path, capsys):
    """P1-2 回归:--bins 边界数组曾送不进内核(int() 直接英文错);补齐后三类入参都可达。"""
    _run(tmp_path, 'hist', '分布', '1', '5', '12', '18', '25', '--bins', '1,10,20')
    _expect_file(tmp_path, 'hist_分布.png')
    assert cli.main(['hist', 't', '1', '2', '3', '--bins', '5,1',
                     '--out-dir', str(tmp_path)]) == 1
    assert '严格递增' in capsys.readouterr().err
    assert cli.main(['hist', 't', '1', '2', '3', '--bins', 'x',
                     '--out-dir', str(tmp_path)]) == 1
    assert '需为整数' in capsys.readouterr().err


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


def test_line_sample_via_cli(tmp_path):
    """--sample:600 行 CSV 降采样出图。"""
    p = tmp_path / 'big.csv'
    p.write_text('\n'.join(['日,值'] + [f'{i},{i % 13}' for i in range(600)]),
                 encoding='utf-8')
    _run(tmp_path, 'line', '大数据', '--file', str(p), '--sample', '60')
    _expect_file(tmp_path, 'line_大数据.png')


def test_numfmt_and_note_via_cli(tmp_path):
    """--numfmt / --note:大数中文单位 + 底部脚注正常出图。"""
    _run(tmp_path, 'bar', '大数', 'a=12345678', 'b=23456789', '--note', '数据来源:测试')
    _expect_file(tmp_path, 'bar_大数.png')
    _run(tmp_path, 'line', '占比', 'a=1', 'b=2', '--numfmt', 'percent')
    _expect_file(tmp_path, 'line_占比.png')


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


def test_file_xlsx_sheet(tmp_path):
    """--sheet 按名称或从 1 数的序号选 Excel 工作表。"""
    op = pytest.importorskip('openpyxl')
    p = tmp_path / 'multi.xlsx'
    wb = op.Workbook()
    wb.active.append(['类目', '2023销量'])
    wb.active.append(['Q1', 100])
    ws2 = wb.create_sheet('2024')
    ws2.append(['类目', '销量'])
    ws2.append(['Q1', 888])
    ws2.append(['Q2', 666])
    wb.save(p)
    _run(tmp_path, 'bar', '按名称', '--file', str(p), '--sheet', '2024')
    _expect_file(tmp_path, 'bar_按名称.png')
    _run(tmp_path, 'rose', '按序号', '--file', str(p), '--sheet', '2')
    _expect_file(tmp_path, 'rose_按序号.png')


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


# ---------- batch 子命令:多份 CSV/Excel 各出一张 ----------

def test_batch_glob_one_chart_per_file(tmp_path):
    """batch:通配符匹配多份 CSV,每份一张图,标题默认取文件名。"""
    for name in ('朝阳', '海淀', '丰台'):
        _csv(tmp_path, f'{name}.csv', '门店,销售额\nA,120\nB,200\n')
    assert cli.main(['batch', 'bar', str(tmp_path / '*.csv'), '--col', '销售额',
                     '--out-dir', str(tmp_path)]) == 0
    for name in ('朝阳', '海淀', '丰台'):
        _expect_file(tmp_path, f'bar_{name}.png')


def test_batch_title_template_and_explicit_paths(tmp_path):
    """--title 模板 {i}/{name};显式列多个文件(不经通配符)同样逐份出图。"""
    a = _csv(tmp_path, '1月.csv', '类目,值\na,1\n')
    b = _csv(tmp_path, '2月.csv', '类目,值\na,2\n')
    assert cli.main(['batch', 'bar', str(a), str(b), '--title', '{i}_{name}销量',
                     '--out-dir', str(tmp_path)]) == 0
    _expect_file(tmp_path, 'bar_1_1月销量.png')
    _expect_file(tmp_path, 'bar_2_2月销量.png')


def test_batch_failure_summary_exit_1(tmp_path, capsys):
    """单份失败不拖累其余:失败行进 stderr,最后汇总并以退出码 1 报告。"""
    _csv(tmp_path, '坏.csv', '类目\na\nb\n')          # 无数值列
    _csv(tmp_path, '好.csv', '类目,值\na,1\n')
    assert cli.main(['batch', 'pie', f'{tmp_path}/*.csv',
                     '--out-dir', str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert '×' in captured.err and '批量完成:成功 1 / 失败 1' in captured.out
    _expect_file(tmp_path, 'pie_好.png')


def test_batch_fail_fast_stops_early(tmp_path, capsys):
    """--fail-fast:首份失败即中止,后续文件不再出图。"""
    _csv(tmp_path, '坏.csv', '类目\na\n')
    _csv(tmp_path, '好.csv', '类目,值\na,1\n')
    assert cli.main(['batch', 'bar', f'{tmp_path}/*.csv', '--fail-fast',
                     '--out-dir', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert '批量中止' in err
    assert not (tmp_path / 'bar_好.png').exists()


def test_batch_no_match_and_sunburst_rejected(tmp_path, capsys):
    """通配符零命中与 sunburst 不适用批量,都报中文错、退出码 1。"""
    assert cli.main(['batch', 'bar', f'{tmp_path}/*.csv',
                     '--out-dir', str(tmp_path)]) == 1
    assert '未匹配到' in capsys.readouterr().err
    assert cli.main(['batch', 'sunburst', 'x.json', '--out-dir', str(tmp_path)]) == 1
    assert '层级' in capsys.readouterr().err
