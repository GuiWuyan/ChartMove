# 更新日志

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),版本号遵循语义化版本。

## Unreleased

### 修正

- **瀑布图**:`total=False`(CLI `--no-total`、MCP `total`)此前是空参数,合计柱从不缺席,传与不传产物逐字节相同;现按参数生效。这是行为变更:之前传 `total=False` 拿到的是带「合计」柱的图,现在不会追加。
- **主题名**:库调用 / MCP 传未知 `style` 此前静默回退 `business` 出图,且 MCP 返回 JSON 会把未生效的值回显成已生效;现在报错(报错信息列出可选主题)。`style=None / ''` 回退 `business` 的行为保留;CLI 本就通过 `choices` 拒绝,不变。
- **饼图 / 环形图**:数值此前在外标签与扇区内重复出现两遍(图例另列一遍类目);现在数值只保留在外标签,占比 <6% 的小扇区也能显示数值。这是视觉变更:既有饼图 / 环形图观感会变(扇区内的白色数字消失)。
- **环形图**:`show_values=False` 此前直接崩溃(`ValueError: not enough values to unpack`),现正常出图(外部只标类目名)。
