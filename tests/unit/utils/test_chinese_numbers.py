"""
测试中文数字处理模块
"""

import pytest

from src.utils.chinese_numbers import cn_to_arabic, extract_batch_number


class TestChineseNumbers:
    """测试中文数字处理功能"""

    def test_cn_to_arabic_single_digit(self) -> None:
        """测试单个中文数字转换"""
        assert cn_to_arabic("一") == "1"
        assert cn_to_arabic("二") == "2"
        assert cn_to_arabic("三") == "3"
        assert cn_to_arabic("四") == "4"
        assert cn_to_arabic("五") == "5"
        assert cn_to_arabic("六") == "6"
        assert cn_to_arabic("七") == "7"
        assert cn_to_arabic("八") == "8"
        assert cn_to_arabic("九") == "9"
        assert cn_to_arabic("零") == "0"

    def test_cn_to_arabic_tens(self) -> None:
        """测试十位数中文数字转换"""
        assert cn_to_arabic("十") == "10"
        assert cn_to_arabic("十一") == "11"
        assert cn_to_arabic("十二") == "12"
        assert cn_to_arabic("二十") == "20"
        assert cn_to_arabic("二十一") == "21"
        assert cn_to_arabic("三十五") == "35"
        assert cn_to_arabic("九十九") == "99"

    def test_cn_to_arabic_hundreds(self) -> None:
        """测试百位数中文数字转换"""
        assert cn_to_arabic("一百") == "100"
        assert cn_to_arabic("二百") == "200"
        assert cn_to_arabic("一百零一") == "101"
        assert cn_to_arabic("一百一") == "101"  # 不带零的情况
        assert cn_to_arabic("一百一十") == "110"
        assert cn_to_arabic("一百二十三") == "123"
        assert cn_to_arabic("九百九十九") == "999"

    def test_cn_to_arabic_mixed(self) -> None:
        """测试混合情况的中文数字转换"""
        # 直接是阿拉伯数字的情况
        assert cn_to_arabic("123") == "123"

        # 其他情况
        assert cn_to_arabic("十") == "10"
        assert cn_to_arabic("百") == "100"

    def test_cn_to_arabic_edge_cases(self) -> None:
        """测试边缘情况"""
        # 空字符串
        assert cn_to_arabic("") == ""

        # 非数字字符
        assert cn_to_arabic("abc") == "abc"

        # 混合字符
        assert cn_to_arabic("第一") == "第一"

    def test_extract_batch_number(self) -> None:
        """测试从文本中提取批次号"""
        # 标准格式 - 中文数字
        assert extract_batch_number("第一批车型目录") == "1"
        assert extract_batch_number("第二批新能源汽车推广目录") == "2"
        assert (
            extract_batch_number("第十批节能与新能源汽车示范推广应用工程推荐车型目录")
            == "10"
        )
        assert extract_batch_number("第二十一批新能源汽车推广应用推荐车型目录") == "21"

        # 标准格式 - 阿拉伯数字
        assert extract_batch_number("第1批车型目录") == "1"
        assert extract_batch_number("第123批新能源汽车推广目录") == "123"

        # 百位数
        assert extract_batch_number("第一百零一批") == "101"
        assert extract_batch_number("第二百批") == "200"

        # 无批次号
        assert extract_batch_number("车型目录") is None
        assert extract_batch_number("") is None

        # 异常情况
        assert extract_batch_number("第批") is None
        assert extract_batch_number("第abc批") is None

    def test_extract_batch_number_direct_chinese(self) -> None:
        """测试直接从中文数字提取批次号"""
        # 文本中包含中文数字，但不是标准批次号格式
        # 对于连续的中文数字，函数会直接返回
        assert extract_batch_number("一二三四五") == "一二三四五"

        # 对于带有"二十一"这样的组合中文数字，函数会转换为阿拉伯数字
        assert extract_batch_number("批次号为二十一") == "21"

        # 无法识别的中文数字
        assert extract_batch_number("非数字文本") is None
