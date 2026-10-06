"""流程与进度类图表:漏斗(自动转化率)/ 甘特 / 哑铃(坡度)/ 桑基(流量走向)。"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon, Rectangle

from ..render import _render, _stagger
from ..style import (
    _has_spread,
    _legend_bottom,
    _nf,
    _style,
    _theme,
    _vfmt,
    _ylim,
)
from ..validate import _validate, _validate_links, _validate_series


def _funnel_draw(title, cats, vals, th):
    vmax = max(vals) or 1

    def draw(ax, p):
        ax.set_facecolor(th['face'])
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        ax.axis('off')  # 漏斗无坐标轴,标签直接画在图上
        n = len(cats)
        for i, (c, v) in enumerate(zip(cats, vals)):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            w = v * pr / vmax
            ax.barh(i, w, left=(1 - w) / 2, height=0.72,
                    color=th['palette'][i % len(th['palette'])])
            if pr > 0.6:
                rate = f'  ({v / vals[i - 1] * 100:.0f}%)' if i and vals[i - 1] else ''
                ax.text(1.02, i, f'{c} {_nf(v, th)}{rate}', va='center', ha='left',
                        fontsize=13, color=th['text'])
        ax.set_xlim(0, 1.55)
        ypad = 0.05 * (n - 1 + 0.72)  # 柱高 0.72 的 y 范围 + 5% 边距,轴从首帧固定
        ax.set_ylim(-0.36 - ypad, n - 1 + 0.36 + ypad)
        ax.invert_yaxis()
    return draw


def funnel(title: str, categories, values, *, style='business', animate=False, fmt=None, loop=False,
           out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
           note: str | None = None) -> Path:
    """漏斗图:按给定顺序从上到下,自动标注逐级转化率;values 需 >=0。"""
    cats, vals = _validate(categories, values)
    if min(vals) < 0:
        raise ValueError('漏斗图 values 需 >=0')
    th = _theme(style, numfmt, note)
    return _render('funnel', title, _funnel_draw(title, cats, vals, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _gantt_draw(title, tasks, starts, ends, th):
    n = len(tasks)
    lo, hi = min(starts), max(ends)
    span = (hi - lo) or 1.0
    durs = [e - s for s, e in zip(starts, ends)]

    def draw(ax, p):
        _style(ax, title, th, grid_axis='x')
        for i in range(n):
            pr = _stagger(p, i, n)
            if pr <= 0:
                continue
            col = th['palette'][0]
            if _has_spread(durs):  # 语义默认值:工期最长高亮、最短弱化
                col = (th['hi_max'] if i == durs.index(max(durs))
                       else th['hi_min'] if i == durs.index(min(durs)) else col)
            s, e = starts[i], starts[i] + durs[i] * pr  # 从起点向右生长
            ax.barh(i, e - s, left=s, height=0.55, color=col)
            if pr > 0.5:
                ax.text(e + span * 0.012, i, f'{_nf(starts[i], th)}–{_nf(ends[i], th)}',
                        va='center', ha='left', fontsize=12, color=th['text'])
        ax.set_yticks(range(n))
        ax.set_yticklabels(tasks)
        ax.invert_yaxis()  # 首任务在顶
        ax.set_xlim(lo - span * 0.02, hi + span * 0.14)  # 右侧留给起止标注
        _vfmt(ax, [*starts, *ends], th, axis='x')
    return draw


def gantt(title: str, tasks, starts, ends, *, style='business', animate=False, fmt=None,
          loop=False, out: str | None = None, out_dir=None,
          figsize=None, dpi=None, numfmt='auto',
          note: str | None = None) -> Path:
    """甘特图:tasks 为任务名,starts/ends 为数值(日期轴暂不支持),ends >= starts。"""
    tsks, ss = _validate(tasks, starts)
    _, es = _validate(tasks, ends)
    if any(e < s for s, e in zip(ss, es)):
        bad = next(i for i, (s, e) in enumerate(zip(ss, es)) if e < s)
        raise ValueError(f'甘特图 ends 需 >= starts(任务「{tsks[bad]}」结束早于开始)')
    th = _theme(style, numfmt, note)
    return _render('gantt', title, _gantt_draw(title, tsks, ss, es, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


def _dumbbell_draw(title, cats, name_a, va, name_b, vb, th, slope):
    n = len(cats)

    def draw(ax, p):
        _style(ax, title, th, grid_axis=None if slope else 'x')
        if slope:  # 坡度图:期初/期末两列,每类别一条斜线
            for i in range(n):
                pr = _stagger(p, i, n)
                if pr <= 0:
                    continue
                col = th['palette'][i % len(th['palette'])]
                ax.plot([0.0, pr], [va[i], va[i] + (vb[i] - va[i]) * pr],
                        color=col, linewidth=3, marker='o', markersize=11,
                        markeredgecolor=th['face'], markeredgewidth=1.2)
                if pr > 0.5:
                    ax.text(-0.03, va[i], _nf(va[i], th), ha='right', va='center',
                            fontsize=12, color=th['text'], zorder=7)
                    ax.text(1.03, vb[i], f'{cats[i]} {_nf(vb[i], th)}', ha='left',
                            va='center', fontsize=12, color=th['text'], zorder=7)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([name_a, name_b])
            ax.set_xlim(-0.32, 1.42)
            _ylim(ax, list(va) + list(vb), th)
            _vfmt(ax, list(va) + list(vb), th)
        else:  # 哑铃图:横向,类别在 y 轴
            all_vals = list(va) + list(vb)
            lo, hi = min(all_vals), max(all_vals)
            pad = (hi - lo) * 0.14 or 1.0
            off = (hi - lo) * 0.02 or 0.3  # 标签离开圆点,避免被压住
            for i in range(n):
                pr = _stagger(p, i, n)
                if pr <= 0:
                    continue
                mid = va[i] + (vb[i] - va[i]) * pr  # 连线从期初点长到期末点
                ax.plot([va[i], mid], [i, i], color=th['axis'], linewidth=3)
                ax.scatter([va[i]], [i], s=120, color=th['axis'], zorder=5,
                           edgecolors=th['face'], linewidths=1.2)
                ax.scatter([mid], [i], s=150, color=th['palette'][0], zorder=6,
                           edgecolors=th['face'], linewidths=1.2)
                if pr > 0.5:
                    ax.text(va[i] - off if va[i] <= vb[i] else va[i] + off, i,
                            _nf(va[i], th),
                            ha='right' if va[i] <= vb[i] else 'left',
                            va='center', fontsize=12, color=th['text'], zorder=7)
                    ax.text(vb[i] + off if va[i] <= vb[i] else vb[i] - off, i,
                            _nf(vb[i], th),
                            ha='left' if va[i] <= vb[i] else 'right',
                            va='center', fontsize=12, color=th['text'], zorder=7)
            ax.set_yticks(range(n))
            ax.set_yticklabels(cats)
            ax.invert_yaxis()  # 首条目在顶
            pad = (max(all_vals) - min(all_vals)) * 0.14 or 1.0
            ax.set_xlim(min(all_vals) - pad, max(all_vals) + pad)
            _vfmt(ax, all_vals, th, axis='x')
            _legend_bottom(ax, [
                Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                       markerfacecolor=th['axis'], label=name_a),
                Line2D([0], [0], linestyle='none', marker='o', markersize=12,
                       markerfacecolor=th['palette'][0], label=name_b)], th)
    return draw


def dumbbell(title: str, categories, series, *, slope=False, style='business',
             animate=False, fmt=None, loop=False, out: str | None = None, out_dir=None,
             figsize=None, dpi=None, numfmt='auto',
             note: str | None = None) -> Path:
    """哑铃图(两期对比):series 恰好 2 个;slope=True 出坡度图。"""
    cats = [str(c) for c in categories]
    ss = _validate_series(cats, series)
    if len(ss) != 2:
        raise ValueError(f'哑铃图需要恰好 2 个系列(期初/期末),收到 {len(ss)} 个;'
                         '坡度图同样只用两期数据')
    (name_a, va), (name_b, vb) = ss
    th = _theme(style, numfmt, note)
    return _render('dumbbell', title,
                   _dumbbell_draw(title, cats, name_a, va, name_b, vb, th, slope),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)


# ---------- 桑基图:自由画布布局(与 treemap 同一 16×9 归一约定) ----------

_SK_W, _SK_H = 16.0, 9.0   # 画布坐标
_SK_BAR = 0.75             # 节点条宽
_SK_NODE_PAD = 0.3         # 同列节点间距
_SK_MARGIN_X = 2.35        # 左右留白:首末列节点标签(尽量收窄,把宽度让给列间距)
_SK_MARGIN_Y = 0.75
_SK_SAMPLES = 36           # 缎带上下缘贝塞尔采样数(动画按此切片)


def _sankey_acyclic(links) -> None:
    """循环流向无法左右分层:Kahn 拓扑走不完即报错(自环一并拦)。"""
    adj: dict[str, list[str]] = {}
    indeg: dict[str, int] = {}
    for s, t, _ in links:
        if s == t:
            raise ValueError(f'流向不能指向自身:「{s}」')
        adj.setdefault(s, []).append(t)
        indeg.setdefault(s, 0)
        indeg[t] = indeg.get(t, 0) + 1
    queue = [n for n, d in indeg.items() if d == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj.get(n, ()):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if seen != len(indeg):
        raise ValueError('links 存在循环流向,桑基图要求流向单向(如 A→B→A)')


def _sankey_layout(links):
    """分列(最长路径)→ 列内重心排序(两轮扫,减交叉)→ 值缩放高度 →
    上下堆叠出缎带锚点。返回 (nodes, recs);nodes 按出现序:
    {名: dict(col, x, top, bot, val, cidx)};recs:缎带锚点 dict 列表。"""
    order, seen, adj, preds = [], set(), {}, {}
    for s, t, _ in links:
        for nm in (s, t):
            if nm not in seen:
                seen.add(nm)
                order.append(nm)
        adj.setdefault(s, []).append(t)
        preds.setdefault(t, []).append(s)
    # 列 = 从源起的最长入边路径(拓扑序递推;循环已在入口被拒)
    col = {nm: 0 for nm in order}
    indeg = {nm: len(preds.get(nm, ())) for nm in order}
    queue = [nm for nm in order if indeg[nm] == 0]
    while queue:
        n = queue.pop()
        for m in adj.get(n, ()):
            col[m] = max(col[m], col[n] + 1)
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    ncols = max(col.values()) + 1
    cols = [[] for _ in range(ncols)]
    for nm in order:
        cols[col[nm]].append(nm)
    # 节点值 = max(入流, 出流);列内初始按值降序(并列保持出现序)
    out_sum = {nm: 0.0 for nm in order}
    in_sum = {nm: 0.0 for nm in order}
    for s, t, v in links:
        out_sum[s] += v
        in_sum[t] += v
    val = {nm: max(in_sum[nm], out_sum[nm]) for nm in order}
    for c in cols:
        c.sort(key=lambda nm: -val[nm])
    idx = {nm: i for c in cols for i, nm in enumerate(c)}
    for _ in range(2):  # 重心扫减交叉;首列冻结保持值降序(大源在顶,避免小源压大源)
        for c in cols[1:]:  # 左→右:按前驱平均位(末列由此按源位排序)
            c.sort(key=lambda nm: sum(idx[p] for p in preds[nm]) / len(preds[nm]))
            for i, nm in enumerate(c):
                idx[nm] = i
        for c in reversed(cols[1:-1]):  # 右→左:中间列按后继平均位
            c.sort(key=lambda nm: sum(idx[t] for t in adj[nm]) / len(adj[nm])
                   if adj.get(nm) else idx[nm])
            for i, nm in enumerate(c):
                idx[nm] = i
    # 高度比例尺:最挤的一列(值合计 + 间距)须装进画布高
    scale = min((_SK_H - 2 * _SK_MARGIN_Y - (len(c) - 1) * _SK_NODE_PAD)
                / sum(val[nm] for nm in c) for c in cols)
    if scale <= 0:
        raise RuntimeError('桑基图同列节点过多,画布排布不下,请合并小流量节点')
    xstep = (_SK_W - 2 * _SK_MARGIN_X - _SK_BAR) / (ncols - 1)
    nodes = {}
    for ci, c in enumerate(cols):
        total_h = sum(val[nm] for nm in c) * scale + (len(c) - 1) * _SK_NODE_PAD
        y = (_SK_H + total_h) / 2  # 列整体垂直居中,自顶向下堆叠
        for pi, nm in enumerate(c):
            h = val[nm] * scale
            nodes[nm] = dict(col=ci, x=_SK_MARGIN_X + ci * xstep,
                             top=y, bot=y - h, val=val[nm], cidx=pi)
            y -= h + _SK_NODE_PAD

    def yc(nm):
        return (nodes[nm]['top'] + nodes[nm]['bot']) / 2

    # 缎带锚点:出边按目标高度降序自节点顶部堆叠,入边按源高度降序同法
    out_lists = {nm: [] for nm in nodes}
    in_lists = {nm: [] for nm in nodes}
    for s, t, v in links:
        out_lists[s].append((s, t, v))
        in_lists[t].append((s, t, v))
    recs = []
    for nm, nd in nodes.items():
        cur = nd['top']
        for s, t, v in sorted(out_lists[nm], key=lambda e: -yc(e[1])):
            thick = v * scale
            recs.append(dict(s=s, t=t, v=v, sy0=cur, sy1=cur - thick))
            cur -= thick
    for nm, nd in nodes.items():
        cur = nd['top']
        for r in sorted((r for r in recs if r['t'] == nm), key=lambda r: -yc(r['s'])):
            thick = r['v'] * scale
            r['ty0'], r['ty1'] = cur, cur - thick
            cur -= thick
    return nodes, recs


def _sankey_draw(title, links, th):
    nodes, recs = _sankey_layout(links)
    palette = th['palette']
    # 配色:全部节点取色板(按列内位置轮换,跨列重复靠标签定位),缎带一律继承
    # 源节点色——"每条流都有颜色可追"。中间列中性化的方案试过被否:中间节点
    # 本身是分析对象时,失去颜色线索的灰缎带在浅底上更难读(2026-10-06 用户反馈)
    for nm, nd in nodes.items():
        nd['color'] = palette[nd['cidx'] % len(palette)]
    ts = np.linspace(0.0, 1.0, _SK_SAMPLES)

    def bez(x0, x1, y0, y1):
        """三次贝塞尔(控制点在水平中点):缎带上下缘各一条,返回采样点列。"""
        u = 1 - ts
        xm = (x0 + x1) / 2
        return np.column_stack([
            u**3 * x0 + 3 * u**2 * ts * xm + 3 * u * ts**2 * xm + ts**3 * x1,
            u**3 * y0 + 3 * u**2 * ts * y0 + 3 * u * ts**2 * y1 + ts**3 * y1])

    for r in recs:
        x0, x1 = nodes[r['s']]['x'] + _SK_BAR, nodes[r['t']]['x']
        r['top'] = bez(x0, x1, r['sy0'], r['ty0'])
        r['bot'] = bez(x0, x1, r['sy1'], r['ty1'])
        r['color'] = nodes[r['s']]['color']
    # 透明度按重叠分层:同列间距内两条缎带若"左右端高低次序互换",中段必然交叠。
    # 异色互换重计权(颜色混在一起是区分度问题),同色互换轻计权(只留密度感),
    # 端点堆叠永不相交不计——密处自动让出对比度,稀处保持饱满
    by_gap = {}
    for r in recs:
        by_gap.setdefault(nodes[r['s']]['col'], []).append(r)
    for group in by_gap.values():
        for r in group:
            cs, ct = (r['sy0'] + r['sy1']) / 2, (r['ty0'] + r['ty1']) / 2
            weight = 0.0
            for o in group:
                if o is r:
                    continue
                if (cs - (o['sy0'] + o['sy1']) / 2) * (ct - (o['ty0'] + o['ty1']) / 2) < 0:
                    weight += 1.0 if o['color'] != r['color'] else 0.3
            r['alpha'] = max(0.15, 0.42 / (1 + 0.2 * weight))
    n_elem = len(nodes) + len(recs)

    def draw(ax, p):
        ax.set_title(title, fontsize=20, pad=18, color=th['text'])
        ax.set_facecolor(th['face'])
        ax.set_xlim(0, _SK_W)
        ax.set_ylim(0, _SK_H)
        ax.axis('off')  # 自由画布:无坐标轴(同漏斗);画布坐标首帧即最终范围
        for i, (nm, nd) in enumerate(nodes.items()):
            pr = _stagger(p, i, n_elem)
            if pr <= 0:
                continue
            h = (nd['top'] - nd['bot']) * pr  # 节点条自中心生长
            ymid = (nd['top'] + nd['bot']) / 2
            ax.add_patch(Rectangle((nd['x'], ymid - h / 2), _SK_BAR, h,
                                   facecolor=nd['color'], edgecolor='none', zorder=3))
            if pr > 0.5:  # 首列标签在左、其余列在节点条右侧(避免压上下相邻色条)
                lbl = f'{nm} {_nf(nd["val"], th)}'
                if nd['col'] == 0:
                    ax.text(nd['x'] - 0.18, ymid, lbl, ha='right', va='center',
                            fontsize=12, color=th['text'], zorder=5)
                else:
                    ax.text(nd['x'] + _SK_BAR + 0.18, ymid, lbl, ha='left',
                            va='center', fontsize=12, color=th['text'], zorder=5)
        for j, r in enumerate(recs):  # 缎带从源向目标逐段生长(采样点切片)
            pr = _stagger(p, len(nodes) + j, n_elem)
            if pr <= 0.02:
                continue
            k = max(2, math.ceil(pr * _SK_SAMPLES))
            poly = np.concatenate([r['top'][:k], r['bot'][:k][::-1]])
            ax.add_patch(Polygon(poly, closed=True, facecolor=r['color'],
                                 alpha=r['alpha'], edgecolor='none', zorder=2))
    return draw


def sankey(title: str, links, *, style='business', animate=False, fmt=None, loop=False,
           out: str | None = None, out_dir=None, figsize=None, dpi=None, numfmt='auto',
           note: str | None = None) -> Path:
    """桑基图:links=[[源, 目标, 数值], ...](每项也接受 {source, target, value});
    左→右单向流向,节点高度即流量,缎带即分流;不支持循环流向。
    animate=True 缎带从源向目标生长。"""
    ls = _validate_links(links)
    _sankey_acyclic(ls)
    th = _theme(style, numfmt, note)
    return _render('sankey', title, _sankey_draw(title, ls, th),
                   animate=animate, fmt=fmt, loop=loop, out=out, out_dir=out_dir,
                   th=th, figsize=figsize, dpi=dpi)
