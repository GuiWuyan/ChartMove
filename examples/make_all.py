"""一条命令生成全部 9 种示例图,兼任用法文档(默认写入 ~/ChartGen/)。

    python examples/make_all.py                # 9 张 PNG,主题按序轮换
    python examples/make_all.py --animate      # 9 张 GIF(数据生长动画)
    python examples/make_all.py --out-dir D:/tmp/charts
"""
from __future__ import annotations

import argparse

from chartgen import THEMES, area, bar, bar_multi, combo, donut, line, line_multi, pie, radar

CATS = ['Q1', 'Q2', 'Q3', 'Q4']
VALS = [120, 200, 90, 160]
SERIES = [('销售额', [120, 200, 150, 260]), ('成本', [90, 120, 130, 110])]
MONTHS = ['1月', '2月', '3月', '4月']


def make_all(out_dir=None, animate=False) -> list:
    """依次生成 9 种类型,主题按序轮换,顺带展示 8 套风格。"""
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
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description='生成全部 9 种示例图(默认写 ~/ChartGen/)')
    ap.add_argument('--out-dir', default=None, help='输出目录(默认 CHARTGEN_OUT_DIR 或 ~/ChartGen)')
    ap.add_argument('--animate', action='store_true', help='出 GIF 动画(默认 PNG)')
    args = ap.parse_args()
    paths = make_all(args.out_dir, args.animate)
    print(f'共生成 {len(paths)} 张图表')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
