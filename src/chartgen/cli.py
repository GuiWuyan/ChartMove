"""CLI 入口(M2 完整化,当前为占位)。

完整实现:单系列"类目=值"内联、多系列 --series JSON、kebab-case 类型名
(line-multi / bar-multi)、themes 子命令,见 docs/plan.md 第 5.2 节。
"""

from __future__ import annotations


def main() -> int:
    print("chartgen CLI 将在 M2 里程碑交付完整功能。")
    print("当前阶段请用 Python API:")
    print("    from chartgen import bar")
    print("    bar('季度产量', ['Q1', 'Q2', 'Q3'], [120, 200, 90], style='tech')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
