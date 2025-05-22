"""
车辆信息模型 - 定义车辆数据的结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class CarInfo:
    """
    车辆信息类，表示一辆车的所有相关信息

    Attributes:
        vmodel: 车辆型号
        category: 车辆类别（节能型或新能源）
        sub_type: 车辆子类型
        batch: 批次号
        energytype: 能源类型（1：新能源，2：节能型）
        company: 企业名称
        brand: 品牌
        raw_text: 原始文本
        table_id: 表格ID
        extra_fields: 其他额外字段
    """

    # 必填字段
    vmodel: str
    category: str
    sub_type: str
    energytype: int  # 1: 新能源, 2: 节能型

    # 可选字段
    batch: Optional[str] = None
    company: Optional[str] = None
    brand: Optional[str] = None
    raw_text: Optional[str] = None
    table_id: Optional[int] = None

    # 额外字段
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        将车辆信息转换为字典格式

        Returns:
            包含所有车辆信息的字典
        """
        result = {
            "vmodel": self.vmodel,
            "category": self.category,
            "sub_type": self.sub_type,
            "energytype": self.energytype,
        }

        # 添加可选字段（如果有值）
        if self.batch:
            result["batch"] = self.batch
        if self.company:
            result["企业名称"] = self.company
        if self.brand:
            result["品牌"] = self.brand
        if self.raw_text:
            result["raw_text"] = self.raw_text
        if self.table_id is not None:
            result["table_id"] = self.table_id

        # 添加额外字段
        result.update(self.extra_fields)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CarInfo":
        """
        从字典创建车辆信息对象

        Args:
            data: 包含车辆信息的字典

        Returns:
            CarInfo对象
        """
        # 提取必填字段
        vmodel = data.pop("vmodel", "")
        category = data.pop("category", "")
        sub_type = data.pop("sub_type", "")
        energytype = data.pop("energytype", 0)

        # 提取可选字段
        batch = data.pop("batch", None)
        company = data.pop("企业名称", None)
        brand = data.pop("品牌", None)
        raw_text = data.pop("raw_text", None)
        table_id = data.pop("table_id", None)

        # 剩余的字段作为额外字段
        extra_fields = data

        return cls(
            vmodel=vmodel,
            category=category,
            sub_type=sub_type,
            energytype=energytype,
            batch=batch,
            company=company,
            brand=brand,
            raw_text=raw_text,
            table_id=table_id,
            extra_fields=extra_fields,
        )


@dataclass
class BatchInfo:
    """
    批次信息类，表示一个批次的数据

    Attributes:
        batch_number: 批次号
        total_count: 总记录数
        declared_count: 声明的总记录数
        energy_saving_count: 节能型汽车数量
        new_energy_count: 新能源汽车数量
        car_list: 车辆列表
        table_counts: 各表格的记录数
    """

    batch_number: str
    total_count: int = 0
    declared_count: Optional[int] = None
    energy_saving_count: int = 0
    new_energy_count: int = 0
    car_list: List[CarInfo] = field(default_factory=list)
    table_counts: Dict[int, int] = field(default_factory=dict)

    def add_car(self, car: CarInfo) -> None:
        """
        添加车辆信息到批次

        Args:
            car: 车辆信息对象
        """
        self.car_list.append(car)
        self.total_count += 1

        # 更新分类计数
        if car.energytype == 1:
            self.new_energy_count += 1
        elif car.energytype == 2:
            self.energy_saving_count += 1

        # 更新表格计数
        if car.table_id is not None:
            if car.table_id not in self.table_counts:
                self.table_counts[car.table_id] = 0
            self.table_counts[car.table_id] += 1

    def to_dict(self) -> Dict[str, Any]:
        """
        将批次信息转换为字典格式

        Returns:
            包含批次信息的字典
        """
        return {
            "batch_number": self.batch_number,
            "total_count": self.total_count,
            "declared_count": self.declared_count,
            "energy_saving_count": self.energy_saving_count,
            "new_energy_count": self.new_energy_count,
            "table_counts": self.table_counts,
            "cars": [car.to_dict() for car in self.car_list],
        }
