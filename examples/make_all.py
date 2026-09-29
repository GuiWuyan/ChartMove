"""一条命令生成全部 20 种示例图,兼任用法文档(默认写入项目 ./Results/)。

    python examples/make_all.py                # 20 张 PNG,主题按序轮换
    python examples/make_all.py --animate      # 20 张 GIF(数据生长动画)
    python examples/make_all.py --out-dir D:/tmp/charts
"""
from __future__ import annotations

import argparse

from vizkit import (
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
    pie,
    radar,
    rose,
    scatter,
    treemap,
    waterfall,
)

CATS = ['Q1', 'Q2', 'Q3', 'Q4']
VALS = [120, 200, 90, 160]
SERIES = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
MONTHS = ['1月', '2月', '3月', '4月']
XS = [1, 2, 3, 4, 5, 6, 7, 8]
YS = [86, 92, 78, 105, 96, 118, 90, 110]
MATRIX = [[3, 7, 2, 5], [8, 1, 6, 4], [2, 5, 9, 3], [6, 2, 4, 8]]


def make_all(out_dir=None, animate=False) -> list:
    """依次生成 20 种类型,主题按序轮换,顺带展示 13 套风格。"""
    styles = list(THEMES)

    def at(i):
        return styles[i % len(styles)]

    return [
        bar('季度产量', CATS, VALS, style=at(0), animate=animate, out_dir=out_dir),
        line('月度增长', MONTHS, [95, 130, 112, 178], style=at(1),
             animate=animate, out_dir=out_dir),
        area('访问量走势', MONTHS, [820, 932, 901, 1290], style=at(2),
             animate=animate, out_dir=out_dir),
        pie('品类占比', ['线上', '门店', '批发'], [55, 30, 15], style=at(3),
            animate=animate, out_dir=out_dir),
        donut('费用构成', ['人力', '物料', '物流', '其他'], [42, 30, 18, 10], style=at(4),
              animate=animate, out_dir=out_dir),
        combo('销量与客单价', CATS, VALS, [86, 92, 78, 105], style=at(5),
              animate=animate, out_dir=out_dir),
        line_multi('销售额对比', MONTHS, SERIES, style=at(6), animate=animate,
                   out_dir=out_dir),
        bar_multi('分组销量', CATS, SERIES, style=at(7), animate=animate, out_dir=out_dir),
        radar('能力对比', ['沟通', '编程', '设计', '数据'], SERIES, style=at(8),
              animate=animate, out_dir=out_dir),
        scatter('客单价分布', XS, YS, trend=True, labels=['a', 'b', 'c', 'd', 'e', 'f',
                                                           'g', 'h'],
                style=at(9), animate=animate, out_dir=out_dir),
        bubble('市场象限', XS, YS, [10, 40, 25, 60, 35, 80, 20, 55], style=at(10),
               animate=animate, out_dir=out_dir),
        hist('响应时长分布', [12, 15, 11, 18, 22, 30, 25, 17, 14, 9, 21, 26, 33, 19,
                              16, 13, 24, 28, 35, 20], bins=8, style=at(11),
             animate=animate, out_dir=out_dir),
        box('A/B 测试转化时长', [('对照组', [3.1, 4.2, 3.8, 5.0, 4.5, 3.9, 4.8, 5.2]),
                                 ('实验组', [2.1, 2.8, 2.5, 3.4, 3.0, 2.3, 2.9, 3.2])],
            style=at(12), animate=animate, out_dir=out_dir),
        heatmap('流量时段热力', ['周一', '周二', '周三', '周四'],
                ['上午', '中午', '下午', '晚间'], MATRIX, style=at(13),
                animate=animate, out_dir=out_dir),
        waterfall('利润变动', CATS, [120, -30, 50, -20], style=at(14),
                  animate=animate, out_dir=out_dir),
        funnel('转化漏斗', ['访问', '加购', '下单', '付款'], [1000, 420, 180, 120],
               style=at(15), animate=animate, out_dir=out_dir),
        rose('品类销量玫瑰图', ['手机', '电脑', '平板', '配件'], [320, 210, 150, 90],
             style=at(16), animate=animate, out_dir=out_dir),
        treemap('预算构成', ['研发', '市场', '运营', '行政', '培训'],
                [420, 300, 180, 100, 60], style=at(17), animate=animate,
                out_dir=out_dir),
        gantt('项目排期', ['需求', '开发', '测试', '上线'], [1, 4, 12, 18],
              [5, 11, 17, 19], style=at(18), animate=animate, out_dir=out_dir),
        dumbbell('渠道转化率对比', ['官网', '门店', 'App', '小程序'],
                 [('2024', [3.2, 5.1, 8.4, 6.0]), ('2025', [4.1, 4.8, 11.2, 9.3])],
                 style=at(19), animate=animate, out_dir=out_dir),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description='生成全部 20 种示例图(默认写 ./Results/)')
    ap.add_argument('--out-dir', default=None, help='输出目录(默认 VIZKIT_OUT_DIR 或 ./Results)')
    ap.add_argument('--animate', action='store_true', help='出 GIF 动画(默认 PNG)')
    args = ap.parse_args()
    paths = make_all(args.out_dir, args.animate)
    print(f'共生成 {len(paths)} 张图表')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
