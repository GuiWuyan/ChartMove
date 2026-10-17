"""一条命令生成全部类型示例图(30 类型 + 堆积变体 + 误差线变体,共 42 张),兼任用法文档。

    python examples/make_all.py [--animate] [--out-dir D:/tmp/charts]
默认输出到项目根 ./Results/(按本脚本位置定位,与运行时工作目录无关)。
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from chartmove import (
    THEMES,
    area,
    bar,
    bar_multi,
    box,
    bubble,
    combo,
    contour,
    donut,
    dumbbell,
    funcplot,
    funnel,
    gantt,
    heatmap,
    hist,
    line,
    line_multi,
    param,
    pareto,
    pie,
    polar,
    radar,
    rose,
    sankey,
    scatter,
    sunburst,
    surface,
    treemap,
    vector,
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

# math 域示例数据(纯 stdlib 构造,避免 make_all 依赖 numpy)
MATH_XS = [i * 0.25 for i in range(33)]                     # 0 ~ 8
MATH_SIN = [math.sin(x) for x in MATH_XS]
MATH_DAMP = [math.exp(-0.25 * x) * math.sin(2 * x) for x in MATH_XS]
MATH_THETA = [i * 2 * math.pi / 120 for i in range(121)]
MATH_ROSE = [abs(math.sin(1.5 * t)) for t in MATH_THETA]     # 三瓣
MATH_TS = [i * 2 * math.pi / 100 for i in range(101)]
MATH_LX = [math.sin(3 * t) for t in MATH_TS]                 # 利萨如
MATH_LY = [math.sin(4 * t) for t in MATH_TS]
MATH_GRID = [i * 0.5 - 2 for i in range(9)]                  # -2 ~ 2
MATH_FX: list[float] = []
MATH_FY: list[float] = []
MATH_FU: list[float] = []
MATH_FV: list[float] = []
for _gy in MATH_GRID:
    for _gx in MATH_GRID:
        MATH_FX.append(_gx)
        MATH_FY.append(_gy)
        MATH_FU.append(-_gy)                                 # 辐旋场
        MATH_FV.append(_gx)
MATH_SX = [i * 0.25 - 2 for i in range(17)]                  # 曲面网格
MATH_SY = [i * 0.25 - 2 for i in range(17)]
MATH_SZ = [[math.sin(sx) * math.cos(sy) for sx in MATH_SX] for sy in MATH_SY]

# 误差线示例数据:重复测量(标准曲线)与各组对称误差
REPL_GROUPS = [[0, [0.021, 0.018, 0.025, 0.019, 0.023, 0.02, 0.022]],
               [4, [0.232, 0.255, 0.218, 0.245, 0.262, 0.15, 0.285]],
               [8, [0.462, 0.485, 0.505, 0.415, 0.375, 0.44, 0.49]],
               [12, [0.585, 0.61, 0.595, 0.655, 0.625, 0.52, 0.58]],
               [16, [0.735, 0.75, 0.715, 0.785, 0.69, 0.77, 0.745]],
               [20, [0.925, 0.995, 0.885, 0.9, 0.825, 0.955, 0.985]]]


def make_all(out_dir=None, animate=False) -> list:
    """依次生成 30 种类型 + 3 张堆积变体 + 9 张误差线变体,主题按序轮换,
    顺带展示 15 套风格。"""
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
        sankey('月度资金流向', [['月收入', '房租', 4500], ['月收入', '餐饮', 2800],
                                ['月收入', '储蓄', 3200], ['月收入', '交通', 900],
                                ['副业', '储蓄', 1500], ['储蓄', '基金定投', 2600],
                                ['储蓄', '应急备用金', 2100]],
               style=at(26), animate=animate, out_dir=out_dir),
        funcplot('正弦与阻尼振荡', curves=[('正弦', MATH_XS, MATH_SIN),
                                          ('阻尼振荡', MATH_XS, MATH_DAMP)],
                 pi_ticks=True, style=at(27), animate=animate, out_dir=out_dir),
        polar('三瓣玫瑰', MATH_THETA, MATH_ROSE, fill=True, style=at(28),
              animate=animate, out_dir=out_dir),
        param('利萨如轨迹', MATH_LX, MATH_LY, arrows=True, style=at(29),
              animate=animate, out_dir=out_dir),
        vector('辐旋流场', MATH_FX, MATH_FY, MATH_FU, MATH_FV, mode='stream',
               style=at(30), animate=animate, out_dir=out_dir),
        contour('波场等高线', MATH_SX, MATH_SY, MATH_SZ, style=at(31),
                animate=animate, out_dir=out_dir),
        surface('波场曲面', MATH_SX, MATH_SY, MATH_SZ, style=at(32),
                animate=animate, out_dir=out_dir),
        # ---- 误差线变体(8 张)----
        line('销量均值误差线', MONTHS, [95, 130, 112, 178], err=[12, 18, 9, 15],
             err_style='whisker', style=at(1), animate=animate, out_dir=out_dir),
        bar('季度产量SD', CATS, VALS, err=[15, 20, 12, 18], style=at(0),
            animate=animate, out_dir=out_dir),
        bar('渠道销量SD横条', ['线上', '门店', '批发', '直供'], [320, 210, 150, 90],
            err=[25, 18, 12, 8], horizontal=True, style=at(4),
            animate=animate, out_dir=out_dir),
        line_multi('双系列误差折线', MONTHS,
                   [('销售额', [120, 200, 150, 260]), ('成本', [90, 118, 125, 110])],
                   errs=[[10, 14, 8, 16], [6, 8, 5, 7]],
                   style=at(7), animate=animate, out_dir=out_dir),
        bar_multi('分组销量SD', CATS, SERIES, errs=[[8, 12, 9, 15], [6, 9, 11, 7]],
                  style=at(8), animate=animate, out_dir=out_dir),
        combo('销量客单价SD', CATS, VALS, [86, 80, 78, 105], bar_err=[12, 15, 9, 14],
              line_err=[4, 5, 3, 6], style=at(6), animate=animate, out_dir=out_dir),
        scatter('蛋白标准曲线', groups=REPL_GROUPS, trend=True, trend_eq=True,
                show_raw=True, style=at(12), animate=animate, out_dir=out_dir),
        violin('响应时长均值SD', [('新版本', [12, 15, 11, 18, 22, 30, 25, 17, 14, 9]),
                                  ('旧版本', [21, 25, 19, 28, 32, 40, 35, 27, 24, 19])],
               mean_sd=True, style=at(25), animate=animate, out_dir=out_dir),
        funcplot('标准曲线拟合', [i * 0.4 for i in range(51)],
                 [0.0418 * x + 0.087 for x in [i * 0.4 for i in range(51)]],
                 points=[[g[0], sum(g[1]) / len(g[1]),
                          max(g[1]) - min(g[1])] for g in REPL_GROUPS],
                 points_name='各管均值 ± 极差', points_fit=True, style=at(27),
                 animate=animate, out_dir=out_dir),
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
