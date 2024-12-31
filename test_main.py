import pytest
from main import extract_doc_content, cn_to_arabic, extract_batch_number


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


def test_extract_extra_info_batch65():
    """测试从第65批文档中提取额外信息"""
    doc_path = "65.docx"
    paragraphs, extra_info = extract_doc_content(doc_path)

    # 打印所有提取到的额外信息，用于调试
    print("\n提取到的额外信息:")
    for info in extra_info:
        print(f"\n类型: {info['type']}")
        print(f"章节: {info['section']}")
        print(f"内容: {info['content']}")

    # 检查第一条额外信息（应该是关于第二部分的说明）
    expected_content = (
        "第二部分 第四批至第六十四批《享受车船税减免优惠的节约能源 使用新能源汽车车型目录》中符合 "
        "《关于调整享受车船税优惠的节能 新能源汽车产品技术要求的公告》(2024年第10号）技术要求 "
        "自动转入车型"
    )

    # 确保至少有一条额外信息
    assert extra_info, "没有提取到任何额外信息"

    # 查找包含预期内容片段的信息
    found = False
    for info in extra_info:
        if "第二部分" in info["content"]:
            found = True
            # 检查内容是否完整
            assert "技术要求" in info["content"], "内容不完整：缺少技术要求部分"
            assert "自动转入车型" in info["content"], "内容不完整：缺少自动转入车型部分"
            print(f"\n实际内容: {info['content']}")
            print(f"预期内容: {expected_content}")
            break

    assert found, "未找到包含'第二部分'的额外信息"
