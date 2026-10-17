"""errors.message:用户数据错误原样透传,内部错误标注类型名(单一出处契约)。"""
from chartmove.errors import USER_ERRORS, message


def test_user_errors_passthrough():
    assert message(ValueError('x 与 y 必须是非空且等长的一维数值序列')) == \
        'x 与 y 必须是非空且等长的一维数值序列'
    assert message(RuntimeError('未找到 ffmpeg(MP4 需要)')) == '未找到 ffmpeg(MP4 需要)'
    assert all(issubclass(t, Exception) for t in USER_ERRORS)


def test_internal_error_labelled():
    msg = message(TypeError("'NoneType' object is not subscriptable"))
    assert msg.startswith('内部错误(TypeError):')
    assert 'not subscriptable' in msg
