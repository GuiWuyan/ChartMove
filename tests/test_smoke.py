"""冒烟测试:包可导入、版本元数据完整。"""

import chartmove


def test_package_importable():
    assert chartmove.__version__


def test_version_format():
    parts = chartmove.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
