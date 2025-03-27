# 车辆数据文档处理工具 (Document Processor)

一个用于从Word文档中提取车辆信息的工具，支持多进程处理和数据验证。

## 功能特点

- 从Word文档(.docx)中提取车辆数据
- 处理中文批次号和数字转换
- 支持多进程并行处理多个文档
- 数据一致性验证和批次验证
- 美观的命令行界面和处理进度显示
- 导出数据为CSV格式
- 支持对比不同版本的数据变化

## 安装方法

### 从源码安装

```bash
git clone https://github.com/yourusername/doc-processor.git
cd doc-processor
pip install -e .
```

### 使用pip安装

```bash
pip install doc-processor
```

## 使用方法

```bash
# 处理单个文档
doc-processor process input.docx -o output.csv

# 处理整个目录
doc-processor process docs_directory/ -o output.csv

# 详细模式
doc-processor process input.docx -o output.csv -v

# 预览文档结构
doc-processor process input.docx --preview

# 对比数据变化
doc-processor process input.docx -o output.csv --compare old_data.csv
```

## 开发说明

### 项目结构

```
doc_processor/
├── cli/                # 命令行接口
├── config/             # 配置管理
├── core/               # 核心处理逻辑
├── extractors/         # 信息提取器
├── models/             # 数据模型
├── parsers/            # 文档解析器
├── utils/              # 工具函数
└── exceptions/         # 自定义异常
```

### 开发环境设置

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black doc_processor tests
isort doc_processor tests
```

## 许可证

MIT 
