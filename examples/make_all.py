"""一条命令生成全部类型示例图(23 类型 + 堆积变体,共 26 张),兼任用法文档。

    python examples/make_all.py [--animate] [--out-dir D:/tmp/charts]
默认输出到项目根 ./Results/(按本脚本位置定位,与运行时工作目录无关)。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from chartmove import (
    THEMES,
    area,
    bar,
    bar_multi,
    box,
    bubble,
    combo,
    donut,
    dumbbell,
    funnel,
    gantt,
    heatmap,
    hist,
    line,
    line_multi,
    pareto,
    pie,
    radar,
    rose,
    scatter,
    sunburst,
    treemap,
    violin,
    waterfall,
)

CATS = ['Q1', 'Q2', 'Q3', 'Q4']
VALS = [120, 200, 90, 160]
SERIES = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
SERIES3 = [('线上', [120, 200, 150, 260]), ('门店', [90, 120, 130, 110]),
           ('批发', [60, 80, 70, 90])]
HIERARCHY = {'线上': {'自营': 320, '分销': 210}, '门店': {'直营': 150, '加盟': 90}}
MONTHS = ['1月', '2月', '3月', '4月']
XS = [1, 2, 3, 4, 5, 6, 7, 8]
YS = [86, 92, 78, 105, 96, 118, 90, 110]
MATRIX = [[3, 7, 2, 5], [8, 1, 6, 4], [2, 5, 9, 3], [6, 2, 4, 8]]


def make_all(out_dir=None, animate=False) -> list:
    """依次生成 23 种类型 + 3 张堆积变体,主题按序轮换,顺带展示 13 套风格。"""
    styles = list(THEMES)

    def at(i):
        return styles[i % len(styles)]

    return [
        bar('季度产量', CATS, VALS, style=at(0), animate=animate, out_dir=out_dir),
        line('月度增长', MONTHS, [95, 130, 112, 178],
             lower=[82, 115, 97, 160], upper=[108, 145, 127, 196],
             style=at(1), animate=animate, out_dir=out_dir),
        area('访问量走势', MONTHS, [820, 932, 901, 1290], style=at(2),
             animate=animate, out_dir=out_dir),
        area('渠道流量堆积', MONTHS, series=SERIES3, stacked=True, style=at(3),
             animate=animate, out_dir=out_dir),
        pie('品类占比', ['线上', '门店', '批发'], [55, 30, 15], style=at(4),
            animate=animate, out_dir=out_dir),
        donut('费用构成', ['人力', '物料', '物流', '其他'], [42, 30, 18, 10], style=at(5),
              animate=animate, out_dir=out_dir),
        combo('销量与客单价', CATS, VALS, [86, 92, 78, 105], style=at(6),
              animate=animate, out_dir=out_dir),
        line_multi('销售额对比', MONTHS, SERIES, style=at(7), animate=animate,
                   out_dir=out_dir),
        bar_multi('分组销量', CATS, SERIES, style=at(8), animate=animate, out_dir=out_dir),
        bar_multi('渠道销量堆积', CATS, SERIES3, stacked=True, style=at(9),
                  animate=animate, out_dir=out_dir),
        bar_multi('渠道占比堆积', CATS, SERIES3, stacked=True, percent=True,
                  style=at(10), animate=animate, out_dir=out_dir),
        radar('能力对比', ['沟通', '编程', '设计', '数据'], SERIES, style=at(11),
              animate=animate, out_dir=out_dir),
        scatter('客单价分布', XS, YS, trend=True, labels=['a', 'b', 'c', 'd', 'e', 'f',
                                                           'g', 'h'],
                style=at(12), animate=animate, out_dir=out_dir),
        bubble('市场象限', XS, YS, [10, 40, 25, 60, 35, 80, 20, 55], style=at(13),
               animate=animate, out_dir=out_dir),
        hist('响应时长分布', [12, 15, 11, 18, 22, 30, 25, 17, 14, 9, 21, 26, 33, 19,
                              16, 13, 24, 28, 35, 20], bins=8, style=at(14),
             animate=animate, out_dir=out_dir),
        box('A/B 测试转化时长', [('对照组', [3.1, 4.2, 3.8, 5.0, 4.5, 3.9, 4.8, 5.2]),
                                 ('实验组', [2.1, 2.8, 2.5, 3.4, 3.0, 2.3, 2.9, 3.2])],
            style=at(15), animate=animate, out_dir=out_dir),
        heatmap('流量时段热力', ['周一', '周二', '周三', '周四'],
                ['上午', '中午', '下午', '晚间'], MATRIX, style=at(16),
                animate=animate, out_dir=out_dir),
        waterfall('利润变动', CATS, [120, -30, 50, -20], style=at(17),
                  animate=animate, out_dir=out_dir),
        pareto('缺陷原因帕累托', ['装配', '焊接', '喷涂', '加工', '其他'],
               [42, 25, 15, 10, 8], style=at(18), animate=animate, out_dir=out_dir),
        funnel('转化漏斗', ['访问', '加购', '下单', '付款'], [1000, 420, 180, 120],
               style=at(19), animate=animate, out_dir=out_dir),
        rose('品类销量玫瑰图', ['手机', '电脑', '平板', '配件'], [320, 210, 150, 90],
             style=at(20), animate=animate, out_dir=out_dir),
        treemap('预算构成', ['研发', '市场', '运营', '行政', '培训'],
                [420, 300, 180, 100, 60], style=at(21), animate=animate,
                out_dir=out_dir),
        gantt('项目排期', ['需求', '开发', '测试', '上线'], [1, 4, 12, 18],
              [5, 11, 17, 19], style=at(22), animate=animate, out_dir=out_dir),
        dumbbell('渠道转化率对比', ['官网', '门店', 'App', '小程序'],
                 [('2024', [3.2, 5.1, 8.4, 6.0]), ('2025', [4.1, 4.8, 11.2, 9.3])],
                 slope=True, style=at(23), animate=animate, out_dir=out_dir),
        sunburst('销售构成旭日图', HIERARCHY, style=at(24), animate=animate,
                 out_dir=out_dir),
        violin('新旧版本响应时长分布', [('新版本', [12, 15, 11, 18, 22, 30, 25, 17, 14,
                                                    9, 21, 26, 33, 19, 16]),
                                       ('旧版本', [21, 25, 19, 28, 32, 40, 35, 27, 24,
                                                   19, 31, 36, 43, 29, 26])],
               style=at(25), animate=animate, out_dir=out_dir),
    ]


ROOT_RESULTS = Path(__file__).resolve().parents[1] / 'Results'


def main() -> int:
    ap = argparse.ArgumentParser(description='生成全部类型示例图(默认写项目根 Results/)')
    ap.add_argument('--out-dir', default=None,
                    help=f'输出目录(默认 {ROOT_RESULTS})')
    ap.add_argument('--animate', action='store_true', help='出 GIF 动画(默认 PNG)')
    args = ap.parse_args()
    paths = make_all(args.out_dir or str(ROOT_RESULTS), args.animate)
    print(f'共生成 {len(paths)} 张图表')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
