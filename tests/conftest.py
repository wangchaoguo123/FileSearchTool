"""
pytest 配置文件
包含测试共享 fixtures 和配置
"""

import pytest
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def project_root():
    """返回项目根目录路径"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def temp_test_dir(tmp_path):
    """创建临时测试目录，测试完成后自动清理"""
    test_dir = tmp_path / "file_search_test"
    test_dir.mkdir()
    return test_dir


@pytest.fixture(scope="function")
def mock_logging():
    """Mock 日志模块，避免测试时生成实际日志文件"""
    from unittest.mock import patch
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = mock_get_logger.return_value
        mock_logger.debug = lambda *args, **kwargs: None
        mock_logger.info = lambda *args, **kwargs: None
        mock_logger.warning = lambda *args, **kwargs: None
        mock_logger.error = lambda *args, **kwargs: None
        yield mock_logger
