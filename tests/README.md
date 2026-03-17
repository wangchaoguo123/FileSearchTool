# 文件搜索工具测试说明

## 环境准备

1. 安装测试依赖：
```bash
pip install pytest pytest-cov Pillow
```

2. 确保已安装项目依赖：
```bash
pip install PyQt5
```

## 运行测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行特定测试文件
```bash
pytest tests/test_file_search_tool.py -v
```

### 运行特定测试类
```bash
pytest tests/test_file_search_tool.py::TestFileSearchCore -v
```

### 运行特定测试用例
```bash
pytest tests/test_file_search_tool.py::TestFileSearchCore::test_search_files_basic -v
```

### 生成测试覆盖率报告
```bash
pytest tests/ --cov=. --cov-report=html
```

### 运行测试并生成详细报告
```bash
pytest tests/ -v --tb=short --cov=tests/test_file_search_tool.py --cov-report=term-missing
```

## 测试覆盖模块

### 1. 文件搜索核心功能 (TestFileSearchCore)
- 测试基本文件搜索功能
- 搜索不区分大小写验证
- 无匹配结果的情况测试
- 搜索进度回调测试

### 2. 文件类型过滤功能 (TestFileFilter)
- 按单种文件类型过滤测试
- 按多种文件类型过滤测试
- 无扩展名过滤（返回所有文件）测试
- 扩展名不区分大小写测试

### 3. 文件预览功能 (TestFilePreview)
- 文本文件预览测试
- 预览不存在的文件测试
- 预览未知类型文件测试
- 图片文件预览测试（需要 PIL 库）

### 4. 结果排序功能 (TestResultSorting)
- 按文件名排序测试
- 按文件大小排序测试
- 按修改时间排序测试
- 无效排序键测试

### 5. CSV导出功能 (TestCSVExport)
- 导出CSV文件测试
- 验证CSV文件格式测试

### 6. 集成测试 (TestIntegration)
- 完整工作流程测试：搜索 -> 过滤 -> 排序 -> 导出

### 7. 容错处理 (TestErrorHandling)
- 搜索无效路径的容错测试
- 预览无效文件的容错测试

## 测试用例命名规范

所有测试用例遵循以下命名格式：
- `test_<功能描述>`：清晰描述测试的功能点
- 例如：`test_search_files_basic`、`test_filter_files_by_type`

## 测试目录结构

```
tests/
├── __init__.py          # 包初始化文件
├── conftest.py          # pytest 配置文件，包含共享 fixtures
├── test_file_search_tool.py  # 主要测试文件
└── README.md            # 本说明文档
```

## 测试架构说明

### Fixture 说明

- `project_root`: 返回项目根目录路径（session 级别）
- `temp_test_dir`: 创建临时测试目录（自动清理）
- `mock_logging`: Mock 日志模块，避免测试时生成实际日志文件
- `search_tool`: 创建 FileSearchTool 实例
- `sample_files`: 创建测试文件集合

### 测试类结构

每个功能模块对应一个测试类：
1. **TestFileSearchCore**: 核心搜索功能
2. **TestFileFilter**: 文件过滤功能
3. **TestFilePreview**: 文件预览功能
4. **TestResultSorting**: 结果排序功能
5. **TestCSVExport**: CSV 导出功能
6. **TestIntegration**: 集成测试
7. **TestErrorHandling**: 容错处理测试

## 扩展测试

如需添加新的测试用例，请遵循以下步骤：

1. 确定测试用例属于哪个功能模块
2. 在相应的测试类中添加新的测试方法
3. 使用清晰的命名规范：`test_<功能描述>`
4. 编写 doc 浮动文档说明测试目的
5. 如果需要，在 `conftest.py` 中添加新的 fixture

### 示例：添加新测试

```python
class TestFileSearchCore:
    def test_search_files_with_wildcard(self, search_tool, temp_test_dir):
        """测试通配符搜索功能"""
        # 创建测试文件
        test_file = os.path.join(temp_test_dir, 'test_123.txt')
        with open(test_file, 'w') as f:
            f.write('content')
        
        # 执行搜索
        results = search_tool.search_files(temp_test_dir, 'test_*')
        
        # 验证结果
        assert len(results) > 0
```

## 注意事项

1. **临时文件处理**: 所有测试使用临时目录，测试完成后自动清理
2. **PIL 库依赖**: 图片预览测试需要安装 Pillow 库，如果没有安装会跳过相关测试
3. **路径处理**: 所有路径都使用 `os.path` 模块处理，确保跨平台兼容性
4. **编码处理**: 文件读写使用 UTF-8 编码，设置 `errors='ignore'` 参数
5. **隔离性**: 每个测试用例独立运行，互不影响

## 持续集成

测试文件已配置为可在 CI/CD 环境中运行：

```yaml
# .github/workflows/test.yml 示例
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: pytest tests/ -v --cov=.
```

## 性能基准测试

如需进行性能基准测试，可以使用 pytest-benchmark：

```bash
pip install pytest-benchmark
pytest tests/ --benchmark-only
```

## 联系方式

如有测试相关问题，请联系开发团队或提交 Issue。
