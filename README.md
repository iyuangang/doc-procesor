# 车辆数据文档处理器

这是一个用于处理和验证车辆数据文档的Python工具包。该工具可以从Word文档中提取车辆信息，进行数据验证和统计分析。

## 功能特点

- 从Word文档中提取结构化车辆数据
- 提取车辆批次信息并进行验证
- 统计分析车辆能源类型和批次分布
- 生成数据统计报告
- 命令行界面支持批量处理
- CSV 原子写入，保留所有动态字段
- 损坏文档、部分批处理失败返回非零状态

## 最新更新

- **入口统一**：安装命令、脚本和 `python -m src` 共用同一套 Click CLI
- **验证修复**：独立比较候选行、有效记录与声明数量
- **错误处理**：API 不再将异常静默转换为空列表
- **输出安全**：CSV 使用 UTF-8 BOM、完整字段集和原子替换
- **大文档优化**：超过阈值后逐行解析 OOXML，避免构建完整 Word DOM

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

# 安装项目和测试/静态检查工具
pip install -e ".[dev]"
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

也可以使用包入口，参数和行为完全相同：

```bash
# 处理单个文件
python -m src process 文档路径.docx -o 输出目录

# 处理整个目录下的文件
python -m src process 文档目录 -o 输出目录 --pattern "*.docx"
```

### 命令行选项

```bash
选项:
  -o, --output PATH     输出目录
  -v, --verbose         显示详细处理信息
  --pattern TEXT        文件匹配模式（用于目录输入）
  --config FILE         配置文件路径
  --log-config FILE     日志配置文件路径
  --chunk-size INTEGER  数据处理块大小
  --skip-verification   跳过批次验证
  --classic-display     使用传统结果显示
  --help                显示帮助信息
```

### Python API调用

```python
from src.processor.doc_processor import process_doc, DocProcessor

# 方法1: 使用便捷函数处理并保存结果
cars = process_doc("path/to/document.docx", "output.csv", verbose=True)

# 方法2: 仅获取处理结果
cars = process_doc("path/to/document.docx")

# 方法3: 更细粒度控制
# 创建处理器实例
processor = DocProcessor("path/to/document.docx", verbose=True)
# 处理文档
cars = processor.process()
# 保存结果
processor.save_to_csv("output.csv")

# 处理多个文件并合并结果
all_cars = []
for file_path in file_list:
    try:
        result = process_doc(file_path)
        all_cars.extend(result)
    except Exception as e:
        print(f"处理文件 {file_path} 失败: {str(e)}")
```

### 处理结果示例

```python
# 处理后的结果示例
[
    {
        "vmodel": "测试型号1",
        "企业名称": "测试企业A",
        "品牌": "测试品牌X",
        "batch": "1",
        "energytype": 2,
        "category": "节能型",
        "sub_type": "轿车",
        "排量": "1.5L",
        "变速器类型": "AT",
        "档位数": "6",
        "table_id": 1
    },
    # ... 更多车辆记录
]
```

## 项目结构

```
doc-processor/
├── src/                  # 源代码
│   ├── __init__.py       # 包初始化
│   ├── __main__.py       # 入口点
│   ├── batch/            # 批次处理和验证
│   ├── cli/              # 命令行接口
│   ├── config/           # 配置管理
│   ├── document/         # 文档解析
│   ├── models/           # 数据模型
│   ├── processor/        # 文档处理器
│   ├── table/            # 表格提取
│   ├── ui/               # 用户界面
│   └── utils/            # 工具函数
├── tests/                # 测试代码
│   ├── __init__.py       # 测试包初始化
│   ├── conftest.py       # 测试配置
│   ├── data/             # 测试数据
│   ├── unit/             # 单元测试
│   │   ├── batch/        # 批次验证测试
│   │   ├── cli/          # CLI测试
│   │   ├── config/       # 配置测试
│   │   ├── document/     # 文档解析测试
│   │   ├── models/       # 数据模型测试
│   │   ├── processor/    # 文档处理器测试
│   │   ├── table/        # 表格处理测试
│   │   └── utils/        # 工具函数测试
│   └── integration/      # 集成测试
│       ├── cli/          # CLI集成测试
│       └── processing/   # 处理流程集成测试
├── pyproject.toml        # 构建、依赖、类型和 pytest 配置
├── run_tests.py          # 测试运行脚本
├── requirements.txt      # 依赖列表
└── README.md             # 项目说明
```

## 配置

可以通过 YAML（JSON 也是合法的 YAML 子集）配置程序行为。当前文件输出仅支持 CSV：

```yaml
document:
  skip_verification: false
  skip_count_check: false
  large_file_threshold: 100
  max_paragraphs_to_search: 30
  max_tables_to_search: 5

performance:
  chunk_size: 1000
  # auto 会在文件达到阈值后启用低内存 OOXML 流式解析
  streaming_xml: auto
  streaming_threshold_mb: 1

output:
  use_dashboard: true
```

`streaming_xml` 也可设为 `true` 或 `false` 强制选择解析器。在仓库真实样本的逐记录哈希校验中，流式与标准模式输出完全一致；两份大型样本的峰值内存分别由约 2.07 GB、1.24 GB 降至约 47 MB、52 MB。具体耗时和内存会随运行环境变化。

## 测试

本项目包含单元测试和集成测试，确保代码质量和功能正确性。

### 运行测试

使用测试运行脚本运行所有测试:

```bash
python run_tests.py
```

运行特定类型的测试:

```bash
# 运行单元测试
python run_tests.py -t unit

# 运行集成测试
python run_tests.py -t integration

# 运行特定模块的测试
python run_tests.py -m processor
```

或者使用 pytest 直接运行:

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行特定模块的测试
pytest tests/unit/processor/
```

### 测试结构

测试结构已重新组织为模块化目录：

- `tests/unit/`: 单元测试
  - 每个模块有专门的测试目录（batch、cli、config等）
- `tests/integration/`: 集成测试
  - `cli/`: 命令行接口集成测试
  - `processing/`: 文档处理流程集成测试
- `tests/test_data/`: 测试数据目录
- `tests/utils/`: 测试辅助工具

### 测试覆盖率

生成测试覆盖率报告:

```bash
python run_tests.py --html-report
```

覆盖率报告会生成在 `htmlcov/`，XML 摘要写入 `coverage.xml`。CI 以当前测试运行结果为准，不在文档中维护容易过期的固定百分比。

## 文档和资源

- [测试说明文档](tests/README.md): 测试结构和运行方法

## 贡献指南

欢迎为本项目做出贡献，无论是提交问题、改进建议还是代码贡献。

### 开发流程

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交Pull Request

### 代码规范

- 遵循PEP 8编码规范
- 添加文档字符串
- 确保通过所有测试
- 添加适当的测试用例

## 许可证

MIT License 
