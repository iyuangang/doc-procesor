# 车辆数据文档处理工具测试说明

本目录包含车辆数据文档处理工具的测试代码。测试基于pytest框架，包含单元测试和集成测试。

## 目录结构

```
tests/
├── __init__.py        # 测试包
├── conftest.py        # pytest配置文件
├── README.md          # 本文件
├── data/              # 测试数据目录
├── unit/              # 单元测试
│   ├── __init__.py    # 单元测试包
│   ├── batch/         # 批次验证测试
│   ├── cli/           # CLI测试
│   ├── config/        # 配置测试
│   ├── document/      # 文档解析测试
│   ├── models/        # 数据模型测试
│   ├── processor/     # 文档处理器测试
│   ├── table/         # 表格处理测试
│   └── utils/         # 工具函数测试
└── integration/       # 集成测试
    ├── __init__.py    # 集成测试包
    └── cli/           # CLI集成测试
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行单元测试

```bash
pytest tests/unit/
```

### 运行集成测试

```bash
pytest tests/integration/
```

### 运行特定模块的测试

```bash
# 运行表格处理测试
pytest tests/unit/table/

# 运行文档处理器测试
pytest tests/unit/processor/
```

### 生成覆盖率报告

```bash
pytest --cov=src --cov-report=term --cov-report=html
```

覆盖率报告将输出到终端，并生成HTML报告保存在`htmlcov/`目录下。

## 测试工具

测试工具函数位于`tests/utils/test_helpers.py`，提供了常用的测试辅助功能：

- `create_sample_document`: 创建用于测试的示例Word文档
- `generate_random_string`: 生成随机字符串
- `create_temp_file`: 创建临时文件
- `simulate_docx_file_content`: 模拟docx文件内容

## 测试配置

测试配置位于`tests/conftest.py`，提供了以下固定装置(fixtures)：

- `test_data_dir`: 测试数据目录路径
- `sample_docx_path`: 样本docx文件路径
- `sample_car_dict`: 样本车辆信息字典
- `sample_car_list`: 样本车辆信息列表
- `temp_dir`: 临时目录
- `mock_empty_config`: 空配置
- `runner`: Click命令测试运行器
- `sample_docx`: 创建示例docx文件
- `sample_config`: 创建示例配置文件
- `sample_log_config`: 创建示例日志配置文件 
