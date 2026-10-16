# AGENTS.md — chartmove 调用须知(面向使用本工具出图的 agent)

chartmove 是中文数据图表生成器:30 种图表(含 math 科学绘图域:函数图像 / 极坐标曲线 / 参数曲线·相轨线 / 矢量场·流线·方向场 / 等高线 / 3D 曲面),15 套主题分属 4 个风格包,输出 PNG / PDF / TIF / GIF / MP4。入口只有两个:CLI 与 MCP Server(stdio)。

## 调用方式

- **CLI**:`chartmove <类型> "标题" [数据] [参数]`,如 `chartmove bar "季度产量" Q1=120 Q2=200`;多份 CSV/Excel 各出一张用 `chartmove batch <类型> "通配符或文件..."`(标题模板 `{name}`/`{i}`,默认取文件名);全部参数看 `chartmove --help` 与 `chartmove bar --help`,数据写法与参数表见 README.md
- **MCP**:工具 `make_chart`(出图)与 `list_themes`(列主题),参数以工具描述为准(英文);数据校验错误以中文 ToolError 返回,按提示改参重试
- agent 手头有 CSV / Excel 时,`make_chart` 传 `file` 路径直读(优先于内联数据),列约定同 CLI `--file`,不必把整表内联进参数
- math 域(funcplot/polar/param/vector/contour/surface)的表格**全为数值列**、按行对齐:funcplot 第 1 列 x 其余列 = 各曲线 y,polar 2 列(theta 弧度, r),param 2 列(x, y)或 3 列(t, x, y),vector 4 列(x, y, u, v),contour / surface 默认矩阵布局(首行首列 = 数值坐标)或 `long=true` / `--long` 切 3 列长表(x, y, z);矢量场 stream 模式需要等间距完整网格
- 出图结果 JSON 里的 `path`(绝对路径)即交付物,直接把它交给用户
- 主题 / 参数拿不准就先跑 `chartmove themes` 或 MCP `list_themes`,不要凭空造参数

## 硬性规则

- 图表产物是持久交付物:默认写 `./Results/`,可用 `--out-dir` / `out_dir=` 参数或 `CHARTMOVE_OUT_DIR` 环境变量覆盖;不做 TTL 清理,同名文件自动加序号(`_2`/`_3`)不覆盖旧产物,也不要手动删除或覆盖用户已有的产物
- MP4 需要系统装有 ffmpeg,没有就改用 GIF;GIF 无额外依赖
- 出现"未找到中文字体"警告说明中文会渲染成方框:Linux 安装 Noto Sans CJK(如 `fonts-noto-cjk` 包),Windows 需微软雅黑,装好后重新出图
