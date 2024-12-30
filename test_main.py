import pytest
from main import extract_batch_number, cn_to_arabic


def test_cn_to_arabic():
    """测试中文数字转阿拉伯数字"""
    test_cases = [
        ("六十五", "65"),
        ("十五", "15"),
        ("六十", "60"),
        ("六", "6"),
        ("65", "65"),
        ("二十六", "26"),
        ("一百二十六", "126"),
        ("九百九十六", "996"),
    ]
    for cn_num, expected in test_cases:
        assert cn_to_arabic(cn_num) == expected


def test_extract_batch_number():
    """测试批次号提取"""
    test_cases = [
        ("第六十五批", "65"),
        ("第六十五批节能型汽车", "65"),
        ("关于发布第六十五批节能与新能源汽车示范推广应用工程推荐车型目录的通知", "65"),
        ("第十五批", "15"),
        ("第六十批", "60"),
        ("第九百九十六批", "996"),
        ("第六批", "6"),
        ("第65批", "65"),
    ]
    for text, expected in test_cases:
        result = extract_batch_number(text)
        assert (
            result == expected
        ), f"测试失败: 输入 '{text}', 期望 '{expected}', 实际得到 '{result}'"


def test_extract_batch_number_edge_cases():
    """测试批次号提取的边界情况"""
    test_cases = [
        ("", None),
        ("没有批次号的文本", None),
        ("第批", None),
        ("第一百批", "100"),
        ("九百九十六", "996"),
        ("第十批节能型汽车", "10"),
    ]
    for text, expected in test_cases:
        result = extract_batch_number(text)
        assert (
            result == expected
        ), f"测试失败: 输入 '{text}', 期望 '{expected}', 实际得到 '{result}'"
