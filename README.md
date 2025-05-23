# 车辆数据文档处理器

这是一个用于处理和验证车辆数据文档的Python工具包。该工具可以从Word文档中提取车辆信息，进行数据验证和统计分析。

## 功能特点

- 从Word文档中提取结构化车辆数据
- 提取车辆批次信息并进行验证
- 统计分析车辆能源类型和批次分布
- 生成数据统计报告
- 命令行界面支持批量处理

## 安装

### 从PyPI安装（适用于最终用户）

```bash
# 通过pip安装
pip install doc-processor
```

安装后可以直接使用命令行工具:

```bash
doc-processor process 文档路径.docx -o 输出目录
```

### 从源码安装（适用于开发者）

```bash
# 克隆仓库
git clone https://github.com/iyuangang/doc-processor.git
cd doc-processor

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

## 使用方法

### 命令行使用

推荐使用方式（无警告信息）:

```bash
# 处理单个文件
python doc_processor.py process 文档路径.docx -o 输出目录
# 或者使用安装后的命令
doc-processor process 文档路径.docx -o 输出目录

# 处理整个目录下的文件
python doc_processor.py process 文档目录 -o 输出目录 --pattern "*.docx"
# 或者使用安装后的命令
doc-processor process 文档目录 -o 输出目录 --pattern "*.docx"
```

或者，您还可以使用以下方式（可能会显示导入警告）:

```bash
# 处理单个文件
python -m src.cli.main process 文档路径.docx -o 输出目录

# 处理整个目录下的文件
python -m src.cli.main process 文档目录 -o 输出目录 --pattern "*.docx"
```

### 命令行选项

```bash
选项:
  -o, --output PATH     输出文件路径或目录
  -v, --verbose         显示详细处理信息
  --pattern TEXT        文件匹配模式（用于目录输入）
  --config FILE         配置文件路径
  --log-config FILE     日志配置文件路径
  --chunk-size INTEGER  数据处理块大小
  --skip-verification   跳过批次验证
  --help                显示帮助信息
```

## 配置

可以通过YAML配置文件自定义程序行为:

```yaml
document:
  skip_verification: false
  
performance:
  chunk_size: 1000
  
logging:
  level: INFO
  file: logs/app.log
```

## 打包与分发

### 构建分发包

```bash
# 安装构建工具
pip install build wheel

# 构建包
python -m build

# 这将在dist/目录下生成两个文件:
# - doc_processor-1.0.0-py3-none-any.whl (wheel格式)
# - doc_processor-1.0.0.tar.gz (源码发布格式)
```

### 安装分发包

```bash
# 从wheel文件安装
pip install dist/doc_processor-1.0.0-py3-none-any.whl
```

### 上传到PyPI (仅维护者)

```bash
# 安装上传工具
pip install twine

# 上传到PyPI
twine upload dist/*
```

## 测试

本项目包含多层次的测试，确保代码质量和功能正确性。

### 运行测试

使用pytest运行所有测试:

```bash
python -m pytest
```

运行特定类型的测试:

```bash
# 运行单元测试
python -m pytest tests/test_cli/test_main.py

# 运行集成测试
python -m pytest tests/test_cli/test_integration*.py
```

### 测试结构

- **单元测试**: 测试各个组件的基本功能
- **集成测试**: 测试整个系统的交互，包括:
  - `test_integration.py`: 命令行基本功能测试
  - `test_integration_processing.py`: 文档处理流程测试
  - `test_config_integration.py`: 配置和日志系统测试

### 测试覆盖率

生成测试覆盖率报告:

```bash
python -m pytest --cov=src
```

查看HTML格式的详细覆盖率报告:

```bash
python -m pytest --cov=src --cov-report=html
```

## 许可证

MIT 
