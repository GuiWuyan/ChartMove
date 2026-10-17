"""入口层异常翻译:异常分类(用户数据错误 vs 内部错误)与中文文案的单一出处。
CLI 与 MCP 的传输形态不同(stderr + 退出码 / ToolError),但"哪些异常算数据错、
消息怎么写"必须只有一份——新增用户可见异常类型只需扩展 USER_ERRORS。
本模块保持纯逻辑:不 import mcp/CLI,也不直接打印或抛 ToolError(那是入口的事)。"""
from __future__ import annotations

USER_ERRORS: tuple[type[Exception], ...] = (ValueError, RuntimeError, OSError)


def message(e: Exception) -> str:
    """任意异常 → 面向用户的中文消息:数据校验错误原样返回(校验层已写中文),
    其余标注「内部错误(类型名)」——保留类型名便于区分是 bug 还是数据问题。"""
    if isinstance(e, USER_ERRORS):
        return str(e)
    return f'内部错误({type(e).__name__}): {e}'
