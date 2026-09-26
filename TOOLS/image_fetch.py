"""网络配图抓取：按关键词下载图片到 Cache/images/<关键词>/，供 PPT 插图使用。

用法：
    命令行:  python TOOLS/image_fetch.py 城市夜景 --n 6
    模块化:  from TOOLS.image_fetch import fetch_images
             folder = fetch_images('城市夜景', n=6)

来源与回退：
    1) Openverse API（CC 授权图，官方接口，含作者/许可信息；国内网络多不可达，6 秒超时自动跳过）
    2) 必应图片整页搜索（国内可直连、无需 key；实际主力来源）
下载后经 Pillow 校验（可解码、最小边长、方向），WEBP 等非常规格式自动转 PNG，
保证 python-pptx / pptxgenjs 都能嵌入。

版权提示：建议用于内部或个人演示；对外发布请优先使用 CC 授权图并保留 sources.md 署名。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import time
from pathlib import Path

import requests
from PIL import Image

CACHE_ROOT = Path(__file__).resolve().parent.parent / 'Cache' / 'images'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PPT_OK_FORMATS = {'JPEG', 'PNG', 'GIF', 'BMP', 'TIFF'}  # python-pptx 可直接嵌入的格式
MIN_SIDE = 400              # 最小边长，过滤图标和缩略图
MAX_BYTES = 15 * 1024 * 1024


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': UA})
    return s


def _ppt_safe_image(raw: bytes, orient: str) -> tuple[bytes, str] | None:
    """校验并规整为 PPT 可嵌入的图片字节，返回 (数据, 扩展名)；不合格返回 None。"""
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))  # verify() 后必须重新打开才能用
        w, h = img.size
        if min(w, h) < MIN_SIDE:
            return None
        if orient == 'landscape' and w < h:
            return None
        if orient == 'portrait' and h < w:
            return None
        if img.format in PPT_OK_FORMATS:
            return raw, 'jpg' if img.format == 'JPEG' else img.format.lower()
        buf = io.BytesIO()  # WEBP/AVIF 等转成 PNG
        has_alpha = 'A' in img.mode or 'transparency' in img.info
        img.convert('RGBA' if has_alpha else 'RGB').save(buf, 'PNG')
        return buf.getvalue(), 'png'
    except Exception:
        return None


def _openverse(session: requests.Session, query: str) -> list[dict]:
    """Openverse CC 授权图。国内网络通常连不上（6 秒超时），失败走必应回退。"""
    try:
        r = session.get('https://api.openverse.org/v1/images/',
                        params={'q': query, 'page_size': 50}, timeout=6)
        r.raise_for_status()
        results = r.json().get('results', [])
    except (requests.RequestException, ValueError):
        return []
    out = []
    for it in results:
        if (it.get('width') or 0) and it['width'] < MIN_SIDE:
            continue
        out.append({
            'url': it.get('url') or '',
            'page': it.get('foreign_landing_url') or '',
            'title': it.get('title') or '',
            'creator': it.get('creator') or '未知作者',
            'license': f"{it.get('license', '')} {it.get('license_version', '')}".strip(),
        })
    return out


def _bing(session: requests.Session, query: str) -> list[dict]:
    """必应图片整页搜索（cn.bing.com 国内可直连）。

    先访问必应首页拿 cookie，再请求 /images/search 整页，从 iusc 元素的
    m 属性（&quot; 转义的 JSON）里解析图片直链 murl。非官方接口，页面结构
    变动时会自然失败返回空列表。
    """
    out, seen = [], set()
    try:
        session.get('https://cn.bing.com', timeout=10)  # cookie 预热
    except requests.RequestException:
        return out
    for first in (1, 36, 71):  # 每页约 35 个结果，最多翻 3 页
        try:
            r = session.get('https://cn.bing.com/images/search',
                            params={'q': query, 'first': first}, timeout=15)
            r.raise_for_status()
        except requests.RequestException:
            break
        found = re.findall(r'm="(\{.*?\})"', r.text)  # 先抓转义串，再还原成 JSON
        if not found:
            break
        for m in found:
            try:
                meta = json.loads(html.unescape(m))
            except (json.JSONDecodeError, ValueError):
                continue
            url = meta.get('murl')
            if url and url not in seen:
                seen.add(url)
                out.append({'url': url, 'page': '', 'title': meta.get('t', ''),
                            'creator': '未知作者', 'license': '以来源页为准'})
    return out


def fetch_images(query: str, n: int = 6, orient: str = 'any',
                 timeout: int = 120) -> Path | None:
    """抓取 n 张配图存入 Cache/images/<关键词>/，返回目录；一张没成返回 None。"""
    folder = CACHE_ROOT / (re.sub(r'[\\/:*?"<>|\s]+', '_', query).strip('_')[:40] or 'img')
    folder.mkdir(parents=True, exist_ok=True)
    session = _session()
    candidates = _openverse(session, query) + _bing(session, query)

    seen_urls, seen_hashes, credits = set(), set(), []
    deadline = time.time() + timeout
    for c in candidates:
        if len(credits) >= n or time.time() > deadline:
            break
        if c['url'] in seen_urls:
            continue
        seen_urls.add(c['url'])
        try:
            r = session.get(c['url'], stream=True, timeout=15)
            r.raise_for_status()
            raw = r.raw.read(MAX_BYTES + 1, decode_content=True)
        except requests.RequestException:
            continue
        if len(raw) > MAX_BYTES or not raw:
            continue
        digest = hashlib.sha1(raw).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        safe = _ppt_safe_image(raw, orient)
        if not safe:
            continue
        data, ext = safe
        name = f'img_{len(credits) + 1:02d}.{ext}'
        (folder / name).write_bytes(data)
        credits.append(f'- {name} | {c["title"][:40]} | {c["creator"]} '
                       f'| {c["license"]} | {c["page"] or c["url"]}')

    if not credits:
        (folder / 'sources.md').unlink(missing_ok=True)
        folder.rmdir()
        print(f'{query!r}: 一张都没抓到（检查网络或换关键词）')
        return None
    (folder / 'sources.md').write_text(
        '# 图片来源\n\n' + '\n'.join(credits) + '\n', encoding='utf-8')
    print(f'{query!r}: 已保存 {len(credits)}/{n} 张 -> {folder}')
    return folder


def main() -> None:
    ap = argparse.ArgumentParser(description='按关键词抓取 PPT 配图到 Cache/images/')
    ap.add_argument('query', help='搜索关键词')
    ap.add_argument('--n', type=int, default=6, help='目标张数，默认 6')
    ap.add_argument('--orient', choices=['any', 'landscape', 'portrait'],
                    default='any', help='图片方向偏好，默认不限')
    args = ap.parse_args()
    raise SystemExit(0 if fetch_images(args.query, args.n, args.orient) else 1)


if __name__ == '__main__':
    main()
