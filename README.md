# 车辆数据文档处理器

这是一个用于处理和验证车辆数据文档的Python工具包。该工具可以从Word文档中提取车辆信息，进行数据验证和统计分析。

## 功能特点

- 从Word文档中提取结构化车辆数据
- 提取车辆批次信息并进行验证
- 统计分析车辆能源类型和批次分布
- 生成数据统计报告
- 命令行界面支持批量处理

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/doc-procesor.git
cd doc-procesor

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

## 使用方法

### 命令行使用

处理单个文件:

```bash
python -m src.cli.main process 文档路径.docx -o 输出目录
```

处理整个目录下的文件:

```bash
python -m src.cli.main process 文档目录 -o 输出目录 --pattern "*.docx"
```

### 命令行选项

```
选项:
  -o, --output TEXT           输出文件路径或目录
  -v, --verbose               显示详细处理信息
  --pattern TEXT              文件匹配模式（用于目录输入）
  --config PATH               配置文件路径
  --log-config PATH           日志配置文件路径
  --chunk-size INTEGER        数据处理块大小
  --skip-verification         跳过批次验证
  --help                      显示帮助信息
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

## 许可证

MIT 
