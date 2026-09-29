"""THEMES 主题库:13 主题 分为 4 风格包。

可选扩展键:spines('box' 四边框 / 'none' 无脊线)、grid_axis('both' 双向网格)、
fig_face(图面底色,区别于绘图区 face)、sketch(手绘抖动)。

打包元数据(THEME_PACKS / THEME_LABELS / THEME_DESCS)供 CLI `themes` 子命令
与 MCP `list_themes` 工具直接使用。
"""

# 每包内的顺序即展示顺序
THEME_PACKS: dict[str, list[str]] = {
    '学术包': ['academic', 'grayscale', 'ggplot', 'colorblind'],
    '商务包': ['business', 'mckinsey', 'dashboard'],
    '简约演示包': ['whitegrid', 'minimal', 'morandi'],
    '其他风格包': ['sketch', 'terminal', 'cyberpunk'],
}

THEME_LABELS: dict[str, str] = {
    'academic': '学术Ticks标准风',
    'grayscale': '灰度单色学术风',
    'ggplot': 'ggplot复古统计风',
    'colorblind': '色盲无障碍风',
    'business': '商务极简风',
    'mckinsey': '麦肯锡风',
    'dashboard': '深色看板商务风',
    'whitegrid': '白底网格风',
    'minimal': '纯极简无脊线风',
    'morandi': '莫兰迪低饱和风',
    'sketch': '手绘草图风',
    'terminal': '暗黑程序员风',
    'cyberpunk': '赛博朋克霓虹风',
}

THEME_DESCS: dict[str, str] = {
    'academic': '出版级四边框刻度、无网格、克制配色(SciencePlots 风格)',
    'grayscale': '纯灰度明度分级,黑白打印不丢信息',
    'ggplot': '灰面板白网格、无脊线,R 语言经典质感',
    'colorblind': 'Okabe-Ito 色盲安全色板,期刊投稿可用',
    'business': '白底浅网格、藏蓝主色,通用商务默认',
    'mckinsey': '无网格多留白、深蓝+灰、红色强调,咨询报告感',
    'dashboard': '深藏青底亮色系,大屏看板高对比',
    'whitegrid': '双向浅网格,seaborn 式清爽通用',
    'minimal': '去边框去网格,黑白灰+红色点睛',
    'morandi': '灰调柔和色系、暖白纸面,优雅耐看',
    'sketch': 'xkcd 式手绘抖动线条,西文手写体(中文仍用中文字体)',
    'terminal': 'GitHub Dark 底色,代码/技术场景',
    'cyberpunk': '深紫夜底霓虹高饱和,发布会大屏',
}

THEMES: dict[str, dict] = {
    # ---------- 学术包 ----------
    'academic': dict(  # 学术Ticks标准风:四边框+刻度、无网格,SciencePlots 同款配色
        palette=('#0C5DA5', '#00B945', '#FF9500', '#C20078', '#5B8CFF', '#7F7F7F'),
        hi_max='#C20078', hi_min='#7F7F7F',
        face='white', text='#000000', axis='#000000',
        grid_color='#E0E0E0', grid_ls='', grid_lw=0.6,
        spines='box',
    ),
    'grayscale': dict(  # 灰度单色学术风:明度分级,黑白打印安全
        palette=('#595959', '#2B2B2B', '#8C8C8C', '#B3B3B3', '#404040', '#D0D0D0'),
        hi_max='#000000', hi_min='#C9C9C9',
        face='white', text='#000000', axis='#000000',
        grid_color='#E0E0E0', grid_ls='-', grid_lw=0.6,
        spines='box',
    ),
    'ggplot': dict(  # ggplot复古统计风:灰面板白网格、无脊线
        palette=('#F8766D', '#00BFC4', '#7CAE00', '#C77CFF', '#FFB000', '#619CFF'),
        hi_max='#CB181D', hi_min='#7F7F7F',
        face='#E5E5E5', fig_face='white', text='#333333', axis='#7F7F7F',
        grid_color='white', grid_ls='-', grid_lw=1.4,
        grid_axis='both', spines='none',
    ),
    'colorblind': dict(  # 色盲无障碍风:Okabe-Ito 安全色板
        palette=('#0072B2', '#E69F00', '#009E73', '#D55E00', '#56B4E9', '#CC79A7'),
        hi_max='#E69F00', hi_min='#999999',
        face='white', text='#000000', axis='#000000',
        grid_color='#E5E5E5', grid_ls='-', grid_lw=0.6,
        spines='box',
    ),
    # ---------- 商务包 ----------
    'business': dict(  # 商务极简风(默认):白底浅网格、藏蓝主色
        palette=('#1F4E79', '#2E75B6', '#8FAADC', '#C55A11', '#767171', '#BFBFBF'),
        hi_max='#C55A11', hi_min='#A6A6A6',
        face='white', text='#262626', axis='#C9C9C9',
        grid_color='#E7EBF0', grid_ls='-', grid_lw=0.9,
    ),
    'mckinsey': dict(  # 麦肯锡风:无网格多留白,深蓝+灰,红色强调
        palette=('#1F3864', '#8EAADB', '#2E5FA3', '#A6A6A6', '#44546A', '#D6D6D6'),
        hi_max='#C00000', hi_min='#BFBFBF',
        face='white', text='#2B2B2B', axis='#BFBFBF',
        grid_color='#E0E0E0', grid_ls='', grid_lw=0.8,
    ),
    'dashboard': dict(  # 深色看板商务风:深藏青底亮色系,大屏高对比
        palette=('#4CC9F0', '#FFB454', '#90BE6D', '#F28482', '#C3A6FF', '#FFD166'),
        hi_max='#FFB454', hi_min='#5A6B8C',
        face='#101C30', fig_face='#0B1424', text='#E8EEF7', axis='#33415C',
        grid_color='#22314B', grid_ls='-', grid_lw=0.8,
    ),
    # ---------- 简约演示包 ----------
    'whitegrid': dict(  # 白底网格风:双向浅网格,seaborn 式
        palette=('#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3', '#937860'),
        hi_max='#C44E52', hi_min='#B0B0B0',
        face='white', text='#333333', axis='#CCCCCC',
        grid_color='#DCDCDC', grid_ls='-', grid_lw=1.0,
        grid_axis='both',
    ),
    'minimal': dict(  # 纯极简无脊线风:去边框去网格,黑白灰+红点睛
        palette=('#1A1A1A', '#737373', '#B0B0B0', '#4A4A4A', '#D0D0D0', '#8C8C8C'),
        hi_max='#D64541', hi_min='#D9D9D9',
        face='white', text='#1A1A1A', axis='#D9D9D9',
        grid_color='#EEEEEE', grid_ls='', grid_lw=0.7,
        spines='none',
    ),
    'morandi': dict(  # 莫兰迪低饱和风:灰调柔和色系、暖白纸面
        palette=('#A9B7C6', '#C9A9A6', '#B5C0B8', '#D4C5B0', '#9FA8A3', '#C4BFC5'),
        hi_max='#7D6B5D', hi_min='#D8D5D0',
        face='#FAF9F6', text='#5C5C5C', axis='#DDD9D3',
        grid_color='#EBE8E3', grid_ls='-', grid_lw=0.9,
    ),
    # ---------- 其他风格包 ----------
    'sketch': dict(  # 手绘草图风:xkcd 式抖动线条,白纸面虚线网格
        palette=('#2B6CB0', '#E0563A', '#3E9B4F', '#7B4FA6', '#D69E2E', '#319795'),
        hi_max='#E0563A', hi_min='#B0B0B0',
        face='white', text='#2B2B2B', axis='#AAAAAA',
        grid_color='#DDDDDD', grid_ls='--', grid_lw=0.9,
        sketch=True,
    ),
    'terminal': dict(  # 暗黑程序员风:GitHub Dark 底色
        palette=('#58A6FF', '#3FB950', '#F778BA', '#FFA657', '#BC8CFF', '#39C5CF'),
        hi_max='#FFA657', hi_min='#484F58',
        face='#161B22', fig_face='#0D1117', text='#E6EDF3', axis='#30363D',
        grid_color='#21262D', grid_ls='-', grid_lw=0.8,
    ),
    'cyberpunk': dict(  # 赛博朋克霓虹风:深紫夜底霓虹高饱和
        palette=('#00F0FF', '#FF2E97', '#B026FF', '#39FF14', '#FFE700', '#00B3FF'),
        hi_max='#FF2E97', hi_min='#4A3B7C',
        face='#0D0221', fig_face='#05010D', text='#E4D9FF', axis='#3D2B6B',
        grid_color='#2A1650', grid_ls='-', grid_lw=0.8,
    ),
}
