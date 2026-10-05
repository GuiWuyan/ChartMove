"""图表子包:22 种图按语义域分 5 个模块,模块间禁止互相 import;包级放 themes_preview。"""
from __future__ import annotations

import math
from pathlib import Path

from matplotlib import pyplot as plt

from ...output import claim_path, resolve_out_dir, safe_stem
from ...themes import THEME_LABELS, THEMES
from ..render import DPI_PNG
from ..style import _sketch_rc_extra, _theme
from .categorical import _bar_draw


def themes_preview(*, out: str | None = None, out_dir=None, dpi=None) -> Path:
    """主题预览拼版图:全部主题各画一组相同数据的迷你柱状图,一张 PNG 对比选风格。"""
    cats, vals = ['一季度', '二季度', '三季度', '四季度'], [120, 200, 90, 160]
    names = list(THEMES)
    cols, rows = 4, math.ceil(len(names) / 4)
    fig = plt.figure(figsize=(cols * 4.2, rows * 2.9), facecolor='white')
    for i, name in enumerate(names):
        th = _theme(name)
        ax = fig.add_subplot(rows, cols, i + 1, facecolor=th.get('fig_face') or th['face'])
        with plt.rc_context(_sketch_rc_extra(th, 'white')):
            _bar_draw(THEME_LABELS[name], cats, vals, th)(ax, 1.0)
        # 格标题落在白色图底上,固定深灰(主题正文色在深色主题下是浅色,会看不清)
        ax.set_title(f'{THEME_LABELS[name]} · {name}', fontsize=13, color='#333333', pad=8)
    for j in range(len(names), rows * cols):
        fig.add_subplot(rows, cols, j + 1).axis('off')
    fig.subplots_adjust(left=0.04, right=0.985, top=0.93, bottom=0.04,
                        hspace=0.62, wspace=0.22)
    path = claim_path(resolve_out_dir(out_dir) / f'{safe_stem("themes", "预览", out)}.png')
    try:
        fig.savefig(path, dpi=dpi or DPI_PNG, facecolor='white')
    except BaseException:
        path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
        raise
    finally:
        plt.close(fig)
    print(f'主题预览图已生成: {path}')
    return path
