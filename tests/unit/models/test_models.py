"""
测试模型类
"""

import pytest
from src.models.car_info import CarInfo, BatchInfo
from src.models.document_node import DocumentNode, DocumentStructure


class TestCarInfo:
    """测试CarInfo类"""

    def test_car_info_creation(self):
        """测试创建CarInfo对象"""
        car = CarInfo(
            vmodel="Model X",
            category="轿车",
            sub_type="小型车",
            energytype=1,
            batch="B001",
            company="Company A",
            brand="Brand A",
            raw_text="Sample text",
            table_id=1,
        )

        assert car.vmodel == "Model X"
        assert car.category == "轿车"
        assert car.sub_type == "小型车"
        assert car.energytype == 1
        assert car.batch == "B001"
        assert car.company == "Company A"
        assert car.brand == "Brand A"
        assert car.raw_text == "Sample text"
        assert car.table_id == 1

    def test_car_info_to_dict(self):
        """测试CarInfo转换为字典"""
        car = CarInfo(
            vmodel="Model X",
            category="轿车",
            sub_type="小型车",
            energytype=1,
            batch="B001",
            company="Company A",
            brand="Brand A",
            table_id=1,
            extra_fields={"颜色": "红色", "年份": 2023},
        )

        car_dict = car.to_dict()

        assert car_dict["vmodel"] == "Model X"
        assert car_dict["category"] == "轿车"
        assert car_dict["sub_type"] == "小型车"
        assert car_dict["energytype"] == 1
        assert car_dict["batch"] == "B001"
        assert car_dict["企业名称"] == "Company A"
        assert car_dict["品牌"] == "Brand A"
        assert car_dict["table_id"] == 1
        assert car_dict["颜色"] == "红色"
        assert car_dict["年份"] == 2023

    def test_car_info_from_dict(self):
        """测试从字典创建CarInfo对象"""
        car_dict = {
            "vmodel": "Model Y",
            "category": "SUV",
            "sub_type": "中型车",
            "energytype": 2,
            "batch": "B002",
            "企业名称": "Company B",
            "品牌": "Brand B",
            "table_id": 2,
            "raw_text": "Sample text",
            "颜色": "蓝色",
            "年份": 2024,
        }

        car = CarInfo.from_dict(car_dict)

        assert car.vmodel == "Model Y"
        assert car.category == "SUV"
        assert car.sub_type == "中型车"
        assert car.energytype == 2
        assert car.batch == "B002"
        assert car.company == "Company B"
        assert car.brand == "Brand B"
        assert car.table_id == 2
        assert car.raw_text == "Sample text"
        assert car.extra_fields["颜色"] == "蓝色"
        assert car.extra_fields["年份"] == 2024


class TestBatchInfo:
    """测试BatchInfo类"""

    def test_batch_info_creation(self):
        """测试创建BatchInfo对象"""
        batch = BatchInfo(
            batch_number="B001",
            total_count=0,
            declared_count=10,
            energy_saving_count=0,
            new_energy_count=0,
        )

        assert batch.batch_number == "B001"
        assert batch.total_count == 0
        assert batch.declared_count == 10
        assert batch.energy_saving_count == 0
        assert batch.new_energy_count == 0
        assert len(batch.car_list) == 0
        assert len(batch.table_counts) == 0

    def test_add_car(self):
        """测试添加车辆到批次"""
        batch = BatchInfo(batch_number="B001")

        # 添加新能源汽车
        car1 = CarInfo(
            vmodel="Model X",
            category="轿车",
            sub_type="小型车",
            energytype=1,  # 新能源
            table_id=1,
        )
        batch.add_car(car1)

        # 添加节能型汽车
        car2 = CarInfo(
            vmodel="Model Y",
            category="SUV",
            sub_type="中型车",
            energytype=2,  # 节能型
            table_id=1,
        )
        batch.add_car(car2)

        # 添加另一个新能源汽车，不同表格
        car3 = CarInfo(
            vmodel="Model Z",
            category="轿车",
            sub_type="大型车",
            energytype=1,  # 新能源
            table_id=2,
        )
        batch.add_car(car3)

        assert batch.total_count == 3
        assert batch.energy_saving_count == 1
        assert batch.new_energy_count == 2
        assert len(batch.car_list) == 3
        assert batch.table_counts[1] == 2
        assert batch.table_counts[2] == 1

    def test_to_dict(self):
        """测试BatchInfo转换为字典"""
        batch = BatchInfo(batch_number="B001", declared_count=3)

        car1 = CarInfo(
            vmodel="Model X",
            category="轿车",
            sub_type="小型车",
            energytype=1,
            table_id=1,
        )
        batch.add_car(car1)

        car2 = CarInfo(
            vmodel="Model Y",
            category="SUV",
            sub_type="中型车",
            energytype=2,
            table_id=2,
        )
        batch.add_car(car2)

        batch_dict = batch.to_dict()

        assert batch_dict["batch_number"] == "B001"
        assert batch_dict["total_count"] == 2
        assert batch_dict["declared_count"] == 3
        assert batch_dict["energy_saving_count"] == 1
        assert batch_dict["new_energy_count"] == 1
        assert batch_dict["table_counts"][1] == 1
        assert batch_dict["table_counts"][2] == 1
        assert len(batch_dict["cars"]) == 2


class TestDocumentNode:
    """测试DocumentNode类"""

    def test_document_node_creation(self):
        """测试创建DocumentNode对象"""
        node = DocumentNode(
            title="测试节点",
            level=1,
            node_type="section",
            content="测试内容",
            batch_number="B001",
            metadata={"key": "value"},
        )

        assert node.title == "测试节点"
        assert node.level == 1
        assert node.node_type == "section"
        assert node.content == "测试内容"
        assert node.batch_number == "B001"
        assert node.metadata["key"] == "value"
        assert len(node.children) == 0


class TestDocumentStructure:
    """测试DocumentStructure类"""

    def test_document_structure_creation(self):
        """测试创建DocumentStructure对象"""
        doc = DocumentStructure()

        assert doc.root.title == "文档结构"
        assert doc.root.level == 0
        assert doc.root.node_type == "root"
        assert doc.current_section is None
        assert doc.current_subsection is None
        assert doc.batch_number is None

    def test_add_node(self):
        """测试添加节点"""
        doc = DocumentStructure()
        doc.set_batch_number("B001")

        # 添加一级节点
        section = doc.add_node("第一章", "section", "章节内容")
        assert section.title == "第一章"
        assert section.level == 1
        assert section.node_type == "section"
        assert section.content == "章节内容"
        assert section.batch_number == "B001"
        assert len(doc.root.children) == 1

        # 添加二级节点
        subsection = doc.add_node("1.1 小节", "subsection", "小节内容")
        assert subsection.title == "1.1 小节"
        assert subsection.level == 2
        assert subsection.node_type == "subsection"
        assert subsection.content == "小节内容"

        # 添加表格节点
        table = doc.add_node(
            "表格1", "table", "表格内容", metadata={"rows": 5, "cols": 3}
        )
        assert table.title == "表格1"
        assert table.node_type == "table"
        assert table.content == "表格内容"
        assert table.metadata["rows"] == 5
        assert table.metadata["cols"] == 3

    def test_to_dict(self):
        """测试DocumentStructure转换为字典"""
        doc = DocumentStructure()
        doc.set_batch_number("B001")

        # 添加节点
        section = doc.add_node("第一章", "section", "章节内容")
        subsection = doc.add_node(
            "1.1 小节", "subsection", "小节内容", parent_node=section
        )
        table = doc.add_node("表格1", "table", "表格内容", parent_node=subsection)

        # 转换为字典
        doc_dict = doc.to_dict()

        assert doc_dict["title"] == "文档结构"
        assert doc_dict["type"] == "root"
        assert len(doc_dict["children"]) == 1

        section_dict = doc_dict["children"][0]
        assert section_dict["title"] == "第一章"
        assert section_dict["type"] == "section"
        assert len(section_dict["children"]) == 1

        subsection_dict = section_dict["children"][0]
        assert subsection_dict["title"] == "1.1 小节"
        assert subsection_dict["type"] == "subsection"
        assert len(subsection_dict["children"]) == 1

        table_dict = subsection_dict["children"][0]
        assert table_dict["title"] == "表格1"
        assert table_dict["type"] == "table"
