"""冒烟测试:包可导入、版本元数据完整。

图表级 smoke test(9 类型 × 3 输出格式)随 M1 内核迁移补充,
届时每种用到的图表类型都必须出图不抛异常且文件存在。
"""

import chartgen


def test_package_importable():
    assert chartgen.__version__


def test_version_format():
    parts = chartgen.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
