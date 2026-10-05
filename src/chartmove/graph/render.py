"""渲染管线:draw(ax, p) 闭包同源输出静态图(p=1)与 48 帧动画;GIF 默认停末帧,
loop=True 才无限循环;MP4 需 ffmpeg;产物经 claim_path 原子占位,同名不覆盖。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from matplotlib import animation
from matplotlib import pyplot as plt

from ..output import claim_path, resolve_out_dir, safe_stem
from .style import _note, _sketch_rc_extra

FIGSIZE = (12.8, 7.2)   # 16:9;12.8 * DPI_PNG = 1920px
DPI_PNG = 150
DPI_GIF = 75            # 960px,控制 GIF 体积
DPI_MP4 = 150
DPI_TIF = 600           # 期刊投稿级
GIF_FPS, MP4_FPS, FRAMES = 20, 24, 48

STATIC_FMTS = ('png', 'pdf', 'tif')
ANIMATED_FMTS = ('gif', 'mp4')


def _ease(t: float) -> float:
    """ease-out 缓动:起步快、收尾慢。"""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def _stagger(p: float, i: int, n: int) -> float:
    """元素错峰进度(重叠 60%),整个动画恰在 p=1 收尾不留静止尾巴。"""
    if n <= 1:
        return _ease(p)
    span = 0.6
    last = span + (1 - span) * (n - 1) / n  # 未归一时最后元素的完成点(<1)
    start = (1 - span) * i / n
    return _ease((last * p - start) / span)


class _GifWriter(animation.PillowWriter):
    """默认不写循环扩展(播一遍停末帧),loop=True 才写;Pillow 丢重复帧会
    把时长累加到保留帧,总时长不变,分步生长的图无需处理。"""

    def __init__(self, fps: float = 5, loop: bool = False, **kwargs):
        super().__init__(fps=fps, **kwargs)
        self._loop = loop

    def finish(self):
        self._frames[0].save(
            self.outfile, save_all=True, append_images=self._frames[1:],
            duration=int(1000 / self.fps), **({'loop': 0} if self._loop else {}))


def _render(kind, title, draw, *, animate, fmt, out, out_dir=None, loop=False,
            polar: bool = False, figsize=None, dpi=None,
            th: dict | None = None) -> Path:
    th = th or {}
    face = th.get('face', 'white')
    fig_face = th.get('fig_face') or face
    rc_extra = _sketch_rc_extra(th, fig_face)  # 手绘风:路径抖动 + 西文手写体
    with plt.rc_context(rc_extra):
        out_path = resolve_out_dir(out_dir)
        stem = safe_stem(kind, title, out)
        fmt = (fmt or ('gif' if animate else 'png')).lower()
        fig_size = figsize or FIGSIZE

        if animate:
            if fmt not in ANIMATED_FMTS:
                raise ValueError(f'动画仅支持 {" / ".join(ANIMATED_FMTS)} 格式,收到 fmt={fmt!r};'
                                 f'静态图请用 animate=False(fmt 可选 {" / ".join(STATIC_FMTS)})')
            if fmt == 'mp4':
                if loop:
                    raise ValueError('loop 仅对 GIF 生效(MP4 是否循环由播放器决定);'
                                     '请改用 fmt="gif" 或去掉 loop')
                if not shutil.which('ffmpeg'):
                    raise RuntimeError('未找到 ffmpeg(MP4 需要)。'
                                       '安装:winget install Gyan.FFmpeg,或改用 fmt="gif"')
                writer = animation.FFMpegWriter(fps=MP4_FPS, codec='h264',
                                                extra_args=['-pix_fmt', 'yuv420p'])
                path, fps, dpi_eff = out_path / f'{stem}.mp4', MP4_FPS, (dpi or DPI_MP4)
            else:
                writer = _GifWriter(fps=GIF_FPS, loop=loop)
                path, fps, dpi_eff = out_path / f'{stem}.gif', GIF_FPS, (dpi or DPI_GIF)

            path = claim_path(path)  # 原子占位:并发下也保证"同名不覆盖"
            try:
                fig = plt.figure(figsize=fig_size, facecolor=fig_face)

                def update(i):
                    fig.clear()  # 连同 twinx 一起清空,避免帧间残留
                    draw(fig.add_subplot(111, polar=polar), i / (FRAMES - 1))
                    _note(fig, th)

                ani = animation.FuncAnimation(fig, update, frames=FRAMES,
                                              interval=1000 / fps)
                ani.save(path, writer=writer, dpi=dpi_eff,
                         savefig_kwargs={'facecolor': fig_face})
            except BaseException:
                path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
                raise
            finally:
                plt.close('all')
        else:
            if fmt not in STATIC_FMTS:
                raise ValueError(f'静态图支持 {" / ".join(STATIC_FMTS)},收到 fmt={fmt!r};'
                                 '动画请传 animate=True(仅 gif / mp4)')
            if loop:
                raise ValueError('loop 仅对动画生效,需 animate=True(仅 gif)')
            path = claim_path(out_path / f'{stem}.{fmt}')  # 原子占位:并发下不覆盖
            dpi_eff = dpi or (DPI_TIF if fmt == 'tif' else DPI_PNG)
            try:
                fig = plt.figure(figsize=fig_size, facecolor=fig_face)
                draw(fig.add_subplot(111, polar=polar), 1.0)
                _note(fig, th)
                fig.savefig(path, dpi=dpi_eff, facecolor=fig_face)
            except BaseException:
                path.unlink(missing_ok=True)   # 占位后失败:别留 0 字节垃圾
                raise
            finally:
                plt.close(fig)

        print(f'图表已生成: {path}')
        return path
