# 文档处理器 (Document Processor)

一个强大的文档处理工具，专门用于处理和分析车辆数据文档。本工具支持智能解析、数据提取、多进程处理和丰富的数据分析功能。

## ✨ 主要特性

### 🔄 智能文档解析
- 支持 Word 文档（.docx）的智能解析
- 自动识别文档结构和层级关系
- 智能提取批次号和分类信息
- 支持中文数字自动转换

### 📊 数据处理能力
- 智能表格识别和数据提取
- 自动字段映射和标准化
- 数据清洗和验证
- 支持多种数据格式转换

### ⚡ 性能优化
- 多进程并行处理
- 内存使用优化
- 大文件分块处理
- 智能缓存管理

### 📝 日志和监控
- 详细的处理日志
- 实时进度显示
- 性能统计报告
- 错误追踪和处理

### 🛠 配置灵活
- YAML 配置文件支持
- 可自定义处理参数
- 灵活的输出选项
- 丰富的调试选项

## 🚀 快速开始

### 安装
```bash
# 克隆仓库
git clone https://github.com/iyuangang/doc-processor.git
cd doc-processor

# 安装依赖
pip install -r requirements.txt
```

### 基本使用
```bash
# 处理单个文件
python main.py process input.docx -o output.csv

# 使用详细模式
python main.py process input.docx -v

# 使用自定义配置
python main.py process input.docx --config custom_config.yaml
```

## 📖 详细功能

### 文档结构解析
- 支持多级标题识别
- 智能段落分析
- 表格结构识别
- 批注和说明提取

### 数据提取能力
- 自动识别表格类型
- 智能字段映射
- 数据类型转换
- 空值智能处理

### 数据验证
- 字段完整性检查
- 数据类型验证
- 业务规则验证
- 错误数据标记

### 输出格式
- CSV 输出支持
- 统计报告生成
- 错误日志输出
- 处理报告生成

## ⚙️ 配置选项

### 性能配置
```yaml
performance:
  chunk_size: 1000
  cache_size_limit: 52428800  # 50MB
  cleanup_interval: 300
  large_file_threshold: 104857600  # 100MB
```

### 日志配置
```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file:
    enabled: true
    path: "logs/doc_processor.log"
```

### 处理配置
```yaml
processing:
  skip_empty_rows: true
  clean_text: true
  validate_data: true
  output_encoding: "utf-8-sig"
```

## 📊 性能优化

### 内存管理
- 大文件分块处理
- 定期缓存清理
- 内存使用监控
- 资源自动释放

### 并行处理
- 多进程支持
- 动态进程池
- 任务分配优化
- 进度同步处理

## 🔍 错误处理

### 异常捕获
- 详细错误日志
- 异常堆栈跟踪
- 错误恢复机制
- 用户友好提示

### 数据验证
- 输入数据验证
- 格式完整性检查
- 业务规则验证
- 错误数据标记

## 📋 系统要求

- Python 3.8+
- 依赖包：
  - pandas >= 1.5.0
  - python-docx >= 0.8.11
  - click >= 8.0.0
  - rich >= 13.0.0
  - PyYAML >= 6.0.0
  - 其他依赖见 requirements.txt

## 🤝 贡献指南

欢迎贡献代码和提出建议！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📝 开发计划

- [ ] 支持更多文档格式
- [ ] 添加 Web 界面
- [ ] 优化数据处理算法
- [ ] 增加数据分析功能
- [ ] 支持导出更多格式

## 📄 许可证

MIT License - 详见 LICENSE 文件

