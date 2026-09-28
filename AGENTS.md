# AGENTS.md — chartgen 调用须知(面向使用本工具出图的 agent)

chartgen 是中文数据图表生成器:16 种图表 × 13 主题(4 风格包),输出 PNG / PDF / TIF / GIF / MP4。入口只有两个:CLI 与 MCP Server(stdio)。

## 调用方式

- **CLI**:`chartgen <类型> "标题" [数据] [参数]`,如 `chartgen bar "季度产量" Q1=120 Q2=200`;全部参数看 `chartgen --help` 与 `chartgen bar --help`,数据写法与参数表见 README.md
- **MCP**:工具 `make_chart`(出图)与 `list_themes`(列主题),参数以工具描述为准(英文);数据校验错误以中文 ToolError 返回,按提示改参重试
- 出图结果 JSON 里的 `path`(绝对路径)即交付物,直接把它交给用户
- 主题 / 参数拿不准就先跑 `chartgen themes` 或 MCP `list_themes`,不要凭空造参数

## 硬性规则

- 图表产物是持久交付物:默认写 `./Results/`,可用 `--out-dir` / `out_dir=` 参数或 `CHARTGEN_OUT_DIR` 环境变量覆盖;不做 TTL 清理,也不要删除或覆盖用户已有的产物
- MP4 需要系统装有 ffmpeg,没有就改用 GIF;GIF 无额外依赖
- 出现"未找到中文字体"警告说明中文会渲染成方框:Linux 安装 Noto Sans CJK(如 `fonts-noto-cjk` 包),Windows 需微软雅黑,装好后重新出图
