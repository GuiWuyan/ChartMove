# 更新日志

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),版本号遵循语义化版本。

## Unreleased

### 修正

- **瀑布图**:`total=False`(CLI `--no-total`、MCP `total`)此前是空参数,合计柱从不缺席,传与不传产物逐字节相同;现按参数生效。这是行为变更:之前传 `total=False` 拿到的是带「合计」柱的图,现在不会追加。
