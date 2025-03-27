"""
车辆信息模型模块，定义车辆数据结构
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CarInfo:
    """
    车辆信息类

    Attributes:
        car_type: 车辆类型（1表示新能源，2表示节能型）
        category: 车辆分类（如"节能型"或"新能源"）
        sub_type: 子类型（如"乘用车"）
        batch: 批次号
        table_id: 表格ID

        企业名称: 企业名称
        品牌: 品牌
        型号: 型号
        序号: 序号

        raw_text: 原始文本
        other_fields: 其他字段
    """

    car_type: int  # 1-新能源, 2-节能型
    category: str
    sub_type: str
    batch: Optional[str] = None
    table_id: Optional[int] = None

    企业名称: str = ""
    品牌: str = ""
    型号: str = ""
    序号: str = ""

    raw_text: str = ""
    other_fields: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理"""
        # 将企业名称字段标准化
        if not self.企业名称 and (
            "企业" in self.other_fields or "生产企业" in self.other_fields
        ):
            self.企业名称 = self.other_fields.pop("企业", "") or self.other_fields.pop(
                "生产企业", ""
            )

        # 将品牌字段标准化
        if not self.品牌 and (
            "通用名称" in self.other_fields or "商标" in self.other_fields
        ):
            self.品牌 = self.other_fields.pop("通用名称", "") or self.other_fields.pop(
                "商标", ""
            )

        # 将型号字段标准化
        if not self.型号 and (
            "产品型号" in self.other_fields or "车辆型号" in self.other_fields
        ):
            self.型号 = self.other_fields.pop("产品型号", "") or self.other_fields.pop(
                "车辆型号", ""
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CarInfo":
        """
        从字典创建车辆信息

        Args:
            data: 数据字典

        Returns:
            车辆信息对象
        """
        # 提取基本字段
        car_type = data.pop("car_type", 0)
        category = data.pop("category", "")
        sub_type = data.pop("sub_type", "")
        batch = data.pop("batch", None)
        table_id = data.pop("table_id", None)

        企业名称 = data.pop("企业名称", "")
        品牌 = data.pop("品牌", "")
        型号 = data.pop("型号", "")
        序号 = data.pop("序号", "")

        raw_text = data.pop("raw_text", "")

        # 其余字段作为其他字段
        return cls(
            car_type=car_type,
            category=category,
            sub_type=sub_type,
            batch=batch,
            table_id=table_id,
            企业名称=企业名称,
            品牌=品牌,
            型号=型号,
            序号=序号,
            raw_text=raw_text,
            other_fields=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            字典表示
        """
        result = {
            "car_type": self.car_type,
            "category": self.category,
            "sub_type": self.sub_type,
            "batch": self.batch,
            "table_id": self.table_id,
            "企业名称": self.企业名称,
            "品牌": self.品牌,
            "型号": self.型号,
            "序号": self.序号,
            "raw_text": self.raw_text,
        }

        # 添加其他字段
        result.update(self.other_fields)

        return result

    def __str__(self) -> str:
        """
        字符串表示

        Returns:
            字符串表示
        """
        return f"车型({self.category}): {self.品牌} {self.型号} - {self.企业名称}"


class CarInfoCollection:
    """
    车辆信息集合类

    Attributes:
        cars: 车辆信息列表
    """

    def __init__(self) -> None:
        """初始化车辆信息集合"""
        self.cars: List[CarInfo] = []

    def add(self, car: CarInfo) -> None:
        """
        添加车辆信息

        Args:
            car: 车辆信息
        """
        self.cars.append(car)

    def add_from_dict(self, data: Dict[str, Any]) -> None:
        """
        从字典添加车辆信息

        Args:
            data: 数据字典
        """
        self.cars.append(CarInfo.from_dict(data))

    def to_list_of_dicts(self) -> List[Dict[str, Any]]:
        """
        转换为字典列表

        Returns:
            字典列表
        """
        return [car.to_dict() for car in self.cars]

    def __len__(self) -> int:
        """
        获取车辆数量

        Returns:
            车辆数量
        """
        return len(self.cars)

    def count_by_category(self) -> Dict[str, int]:
        """
        按类别统计车辆数量

        Returns:
            类别统计字典
        """
        result: Dict[str, int] = {}
        for car in self.cars:
            category = car.category
            if category not in result:
                result[category] = 0
            result[category] += 1
        return result

    def count_by_type(self) -> Dict[int, int]:
        """
        按类型统计车辆数量

        Returns:
            类型统计字典
        """
        result: Dict[int, int] = {1: 0, 2: 0}  # 1-新能源, 2-节能型
        for car in self.cars:
            if car.car_type in result:
                result[car.car_type] += 1
        return result

    def get_models(self) -> List[str]:
        """
        获取所有型号列表

        Returns:
            型号列表
        """
        return [car.型号 for car in self.cars if car.型号]
