# 测试说明文档

本文档介绍了车辆数据文档处理器的测试框架、结构和运行方法。

## 测试结构

测试已重新组织为模块化目录结构，分为单元测试和集成测试：

```
tests/
├── __init__.py       # 测试包初始化
├── conftest.py       # 测试配置和共享fixtures
├── data/             # 测试数据
│   ├── sample_docs/  # 样例文档文件
│   └── fixtures/     # 测试数据fixtures
├── unit/             # 单元测试
│   ├── batch/        # 批次验证测试
│   ├── cli/          # CLI测试
│   ├── config/       # 配置测试
│   ├── document/     # 文档解析测试
│   ├── models/       # 数据模型测试
│   ├── processor/    # 文档处理器测试
│   ├── table/        # 表格处理测试
│   └── utils/        # 工具函数测试
├── integration/      # 集成测试
│   ├── cli/          # CLI集成测试
│   └── processing/   # 处理流程集成测试
└── utils/            # 测试辅助函数
```

### 测试类型

测试代码分为两种主要类型：

1. **单元测试** (`tests/unit/`)：测试各个组件的基本功能，通常使用模拟（mock）来隔离依赖
   - 每个源代码模块有专门的测试目录
   - 使用pytest fixtures提供测试数据
   - 测试覆盖各种边界条件和错误情况

2. **集成测试** (`tests/integration/`)：测试组件之间的交互和整个系统的功能
   - `cli/`: 命令行接口集成测试，验证命令行功能
   - `processing/`: 文档处理流程集成测试，验证文档处理端到端流程

## 测试辅助工具

为了便于测试，我们提供了以下辅助函数：

- `tests/utils/file_helpers.py`: 文件操作辅助函数
- `tests/utils/test_data.py`: 测试数据生成函数
- `tests/utils/fixtures.py`: 共享的pytest fixtures

常用辅助函数包括：

```python
# 创建测试文档
def create_sample_document(content=None, tables=None):
    """创建一个包含指定内容和表格的测试文档"""
    # ...

# 随机字符串生成
def generate_random_string(length=10):
    """生成指定长度的随机字符串"""
    # ...

# 创建临时目录
@pytest.fixture
def temp_dir():
    """创建临时目录并在测试后清理"""
    # ...
```

## 运行测试

### 使用测试运行脚本

我们提供了一个专用的测试运行脚本 `run_tests.py`，支持各种命令行参数：

```bash
# 运行所有测试
python run_tests.py

# 运行单元测试
python run_tests.py -t unit

# 运行集成测试
python run_tests.py -t integration

# 运行特定模块的测试
python run_tests.py -m processor

# 生成HTML覆盖率报告
python run_tests.py --html-report

# 运行标记的测试（例如：smoke测试）
python run_tests.py -k smoke

# 显示帮助
python run_tests.py --help
```

### 使用pytest直接运行

您也可以使用pytest直接运行测试：

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行特定模块的测试
pytest tests/unit/processor/

# 生成测试覆盖率报告
pytest --cov=src

# 生成HTML测试覆盖率报告
pytest --cov=src --cov-report=html

# 运行标记的测试
pytest -m "smoke"

# 详细模式
pytest -v
```

## 测试标记

测试使用pytest标记系统进行分类，主要标记包括：

- `unit`: 标记单元测试
- `integration`: 标记集成测试
- `smoke`: 标记基本冒烟测试
- `slow`: 标记耗时较长的测试
- `doc`: 标记文档处理相关测试
- `cli`: 标记命令行接口测试
- `fast`: 标记快速执行的测试

示例用法：

```bash
# 运行所有smoke测试
pytest -m "smoke"

# 运行所有非耗时测试
pytest -m "not slow"

# 组合使用标记
pytest -m "unit and not slow"
```

## 添加新测试

### 单元测试

添加新的单元测试时，请遵循以下原则：

1. 将测试文件放在相应的模块目录下
2. 文件名以 `test_` 开头
3. 测试函数以 `test_` 开头
4. 测试类以 `Test` 开头
5. 使用断言验证结果
6. 使用mock隔离外部依赖

示例：

```python
# tests/unit/processor/test_new_feature.py
import pytest
from unittest.mock import patch, MagicMock
from src.processor.new_feature import NewFeature

class TestNewFeature:
    def test_feature_basic_functionality(self):
        # 准备测试数据
        test_input = {"key": "value"}
        
        # 创建被测对象
        feature = NewFeature()
        
        # 调用被测方法
        result = feature.process(test_input)
        
        # 验证结果
        assert result["processed"] == True
        assert "timestamp" in result
    
    @patch('src.processor.new_feature.external_dependency')
    def test_feature_with_external_dependency(self, mock_dependency):
        # 设置mock行为
        mock_dependency.get_data.return_value = {"mock": "data"}
        
        # 创建被测对象
        feature = NewFeature()
        
        # 调用被测方法
        result = feature.process_with_external({"input": "value"})
        
        # 验证结果
        assert result["success"] == True
        # 验证mock被正确调用
        mock_dependency.get_data.assert_called_once()
```

### 集成测试

添加集成测试时，请注意：

1. 集成测试应该验证多个组件的交互
2. 尽量使用真实的依赖项（少用mock）
3. 创建真实的输入数据和预期结果
4. 清理测试产生的任何临时数据

示例：

```python
# tests/integration/processing/test_end_to_end.py
import os
import pytest
from src.processor.doc_processor import process_doc
from tests.utils.file_helpers import create_temp_file, compare_csv_files

class TestEndToEndProcessing:
    @pytest.fixture
    def setup_test_environment(self, temp_dir):
        # 创建测试文档
        doc_path = create_temp_file(temp_dir, "test.docx", create_test_doc())
        output_path = os.path.join(temp_dir, "output.csv")
        expected_output = create_expected_csv()
        expected_path = create_temp_file(temp_dir, "expected.csv", expected_output)
        
        return {
            "doc_path": doc_path,
            "output_path": output_path,
            "expected_path": expected_path
        }
    
    def test_process_and_save(self, setup_test_environment):
        env = setup_test_environment
        
        # 执行被测流程
        cars = process_doc(env["doc_path"], env["output_path"], verbose=True)
        
        # 验证结果
        assert len(cars) > 0
        assert os.path.exists(env["output_path"])
        
        # 比较输出与预期
        assert compare_csv_files(env["output_path"], env["expected_path"])
```

## 最佳实践

遵循以下最佳实践来编写有效的测试：

1. **测试独立性**：测试不应相互依赖，也不应依赖执行顺序
2. **使用fixtures**：尽可能使用pytest fixtures来设置和清理测试环境
3. **测试边界条件**：验证极端情况和边界条件
4. **预期异常测试**：测试错误处理和异常情况
5. **避免测试内部实现**：测试公共接口，而非内部实现细节
6. **描述性命名**：使用描述性的测试名称，清晰表达测试的意图
7. **保持测试简单**：每个测试只验证一个概念
8. **使用参数化测试**：使用`@pytest.mark.parametrize`测试多个输入场景
9. **维护测试数据**：将大型测试数据分离到单独的文件中

## 故障排除

如果测试失败，可采取以下步骤：

1. 以详细模式运行失败的测试：`pytest path/to/test.py -v`
2. 使用日志记录：`pytest path/to/test.py --log-cli-level=DEBUG`
3. 使用调试器：`pytest path/to/test.py --pdb`
4. 检查测试环境变量和依赖

## 代码覆盖率

我们的目标是保持至少70%的代码覆盖率。每次提交前，请运行覆盖率报告：

```bash
python run_tests.py --html-report
```

查看 `htmlcov/index.html` 了解详细的覆盖率信息。 
 