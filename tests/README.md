# 测试说明

测试分为 `tests/unit/` 单元测试和 `tests/integration/` 端到端测试；共享 fixture 位于 `tests/conftest.py`，辅助函数位于 `tests/utils/`，静态样例数据位于 `tests/test_data/`。

## 运行

```bash
# 完整测试与终端覆盖率
python -m pytest

# 仅单元或集成测试
python run_tests.py -t unit
python run_tests.py -t integration

# 按模块或标记筛选
python run_tests.py -m processor
python run_tests.py -k "not slow"

# 额外生成 HTML/XML 覆盖率报告
python run_tests.py --html-report --xml-report
```

pytest 的唯一配置源是根目录 `pyproject.toml`。测试运行器以参数列表启动 pytest，不依赖 shell，因此含空格的路径和标记表达式也能安全工作。

## 约定

- 测试文件和函数分别以 `test_` 开头；测试类以 `Test` 开头。
- 单元测试隔离单个组件；集成测试使用临时目录创建真实 DOCX/CSV，不能写入仓库样例或 `output/`。
- 修复缺陷时添加能够复现原问题的测试；解析优化必须同时验证标准模式与流式模式输出一致。
- `slow` 标记仅用于需要大型外部样例的性能测试，不应成为 CI 正确性检查的依赖。
