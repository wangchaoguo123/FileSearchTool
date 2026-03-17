"""
文件搜索工具单元测试文件
使用 pytest 框架编写，覆盖以下功能模块：
- 多类型文件搜索
- 文件类型过滤
- 实时预览
- 结果排序
- 进度显示
- 结果导出
- 系统集成
- 容错处理
"""

import os
import sys
import tempfile
import shutil
import time
import csv
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class FileSearchTool:
    """文件搜索工具核心类"""

    def __init__(self):
        pass

    def search_files(self, path, keyword, callback=None):
        """
        搜索文件
        
        参数:
            path: 搜索路径
            keyword: 搜索关键词
            callback: 进度回调函数
        
        返回:
            匹配的文件列表
        """
        results = []
        keyword = keyword.lower()
        processed_count = 0
        total_count = self._count_files(path)
        
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                processed_count += 1
                if keyword in filename.lower():
                    full_path = os.path.join(dirpath, filename)
                    stat = os.stat(full_path)
                    file_info = {
                        'path': full_path,
                        'name': filename,
                        'mtime': stat.st_mtime,
                        'size': stat.st_size
                    }
                    results.append(file_info)
                if callback and processed_count % 10 == 0:
                    callback(processed_count, total_count)
        
        if callback:
            callback(total_count, total_count)
        return results

    def _count_files(self, path):
        """统计目录下的总文件数"""
        count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            count += len(filenames)
        return count

    def filter_files_by_type(self, file_list, extensions):
        """
        按文件类型过滤
        
        参数:
            file_list: 文件列表
            extensions: 文件扩展名列表
        
        返回:
            过滤后的文件列表
        """
        if not extensions:
            return file_list
        extensions = [ext.lower() for ext in extensions]
        filtered = []
        for file_info in file_list:
            _, ext = os.path.splitext(file_info['name'].lower())
            if ext in extensions:
                filtered.append(file_info)
        return filtered

    def preview_file(self, file_path):
        """
        预览文件
        
        参数:
            file_path: 文件路径
        
        返回:
            预览内容字典
        """
        if not os.path.exists(file_path):
            return {'type': 'error', 'content': '文件不存在'}
        
        _, ext = os.path.splitext(file_path.lower())
        text_extensions = ['.txt', '.py', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        
        if ext in text_extensions:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)
                return {'type': 'text', 'content': content}
            except Exception as e:
                return {'type': 'error', 'content': f'读取失败: {str(e)}'}
        elif ext in image_extensions:
            try:
                from PIL import Image
                img = Image.open(file_path)
                return {'type': 'image', 'content': f'Image: {img.size[0]}x{img.size[1]}'}
            except ImportError:
                return {'type': 'image', 'content': 'PIL库不可用'}
            except Exception as e:
                return {'type': 'error', 'content': f'图片加载失败: {str(e)}'}
        else:
            return {'type': 'unknown', 'content': f'不支持的文件类型: {ext}'}

    def sort_results(self, results, sort_by='name', reverse=False):
        """
        排序结果
        
        参数:
            results: 搜索结果列表
            sort_by: 排序依据 (name, mtime, size)
            reverse: 是否降序
        
        返回:
            排序后的结果列表
        """
        if sort_by == 'name':
            return sorted(results, key=lambda x: x['name'], reverse=reverse)
        elif sort_by == 'mtime':
            return sorted(results, key=lambda x: x['mtime'], reverse=reverse)
        elif sort_by == 'size':
            return sorted(results, key=lambda x: x['size'], reverse=reverse)
        else:
            return results

    def export_results_to_csv(self, results, output_path):
        """
        导出结果到CSV文件
        
        参数:
            results: 搜索结果列表
            output_path: 输出文件路径
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['path', 'name', 'mtime', 'size']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)


class TestFileSearchCore:
    """测试文件搜索核心功能"""

    @pytest.fixture
    def search_tool(self):
        """创建 FileSearchTool 实例"""
        return FileSearchTool()

    @pytest.fixture
    def sample_files(self, temp_test_dir):
        """创建测试文件"""
        files = [
            ('test1.txt', 'test content 1'),
            ('sample2.py', 'print("hello")'),
            ('document3.md', '# Test Document'),
            ('image4.jpg', ''),
            ('data5.csv', 'a,b,c'),
            ('test_file6.txt', 'another test'),
            ('not_matching.txt', 'no keyword here')
        ]
        
        created_files = []
        for filename, content in files:
            file_path = os.path.join(temp_test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                if content:
                    f.write(content)
            created_files.append({
                'path': file_path,
                'name': filename,
                'mtime': os.path.getmtime(file_path),
                'size': os.path.getsize(file_path)
            })
        
        return created_files

    def test_search_files_basic(self, search_tool, temp_test_dir, sample_files):
        """测试基本文件搜索功能"""
        results = search_tool.search_files(temp_test_dir, 'test')
        assert len(results) == 2
        found_names = [r['name'] for r in results]
        assert 'test1.txt' in found_names
        assert 'test_file6.txt' in found_names
        assert 'not_matching.txt' not in found_names

    def test_search_files_case_insensitive(self, search_tool, temp_test_dir, sample_files):
        """测试搜索不区分大小写"""
        results = search_tool.search_files(temp_test_dir, 'TEST')
        assert len(results) == 2

    def test_search_files_no_match(self, search_tool, temp_test_dir, sample_files):
        """测试无匹配结果的情况"""
        results = search_tool.search_files(temp_test_dir, 'nonexistentkeyword')
        assert len(results) == 0

    def test_search_files_with_callback(self, search_tool, temp_test_dir, sample_files):
        """测试搜索进度回调"""
        progress_updates = []
        
        def callback(processed, total):
            progress_updates.append((processed, total))
        
        results = search_tool.search_files(temp_test_dir, 'test', callback=callback)
        assert len(results) == 2
        assert len(progress_updates) > 0


class TestFileFilter:
    """测试文件类型过滤功能"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    @pytest.fixture
    def sample_files(self, temp_test_dir):
        files = [
            ('test1.txt', 'content'),
            ('sample2.py', 'code'),
            ('image3.jpg', ''),
            ('data4.csv', 'data')
        ]
        
        created_files = []
        for filename, content in files:
            file_path = os.path.join(temp_test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                if content:
                    f.write(content)
            created_files.append({
                'path': file_path,
                'name': filename,
                'mtime': 0,
                'size': 0
            })
        
        return created_files

    def test_filter_files_by_type(self, search_tool, sample_files):
        """测试按单种文件类型过滤"""
        filtered = search_tool.filter_files_by_type(sample_files, ['.txt'])
        assert len(filtered) == 1
        for f in filtered:
            assert f['name'].endswith('.txt')

    def test_filter_files_by_type_multiple(self, search_tool, sample_files):
        """测试按多种文件类型过滤"""
        filtered = search_tool.filter_files_by_type(sample_files, ['.txt', '.py'])
        assert len(filtered) == 2

    def test_filter_files_by_type_no_extensions(self, search_tool, sample_files):
        """测试无扩展名过滤（返回所有文件）"""
        filtered = search_tool.filter_files_by_type(sample_files, [])
        assert len(filtered) == len(sample_files)

    def test_filter_files_by_type_case_insensitive(self, search_tool, sample_files):
        """测试扩展名不区分大小写"""
        filtered = search_tool.filter_files_by_type(sample_files, ['.TXT'])
        assert len(filtered) == 1


class TestFilePreview:
    """测试文件预览功能"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    def test_preview_text_file(self, search_tool, temp_test_dir):
        """测试文本文件预览"""
        test_file = os.path.join(temp_test_dir, 'test.txt')
        test_content = 'Hello, World!\nThis is a test file.'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        result = search_tool.preview_file(test_file)
        assert result['type'] == 'text'
        assert 'Hello, World!' in result['content']

    def test_preview_nonexistent_file(self, search_tool):
        """测试预览不存在的文件"""
        result = search_tool.preview_file('/path/to/nonexistent/file.txt')
        assert result['type'] == 'error'

    def test_preview_unknown_type(self, search_tool, temp_test_dir):
        """测试预览未知类型文件"""
        test_file = os.path.join(temp_test_dir, 'unknown.xyz')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('content')
        
        result = search_tool.preview_file(test_file)
        assert result['type'] == 'unknown'


class TestResultSorting:
    """测试结果排序功能"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    def test_sort_results_by_name(self, search_tool):
        """测试按文件名排序"""
        results = [
            {'name': 'zebra.txt', 'mtime': 0, 'size': 0, 'path': ''},
            {'name': 'apple.txt', 'mtime': 0, 'size': 0, 'path': ''},
            {'name': 'banana.txt', 'mtime': 0, 'size': 0, 'path': ''}
        ]
        
        sorted_asc = search_tool.sort_results(results, 'name', reverse=False)
        sorted_desc = search_tool.sort_results(results, 'name', reverse=True)
        
        assert sorted_asc[0]['name'] == 'apple.txt'
        assert sorted_desc[0]['name'] == 'zebra.txt'

    def test_sort_results_by_size(self, search_tool):
        """测试按文件大小排序"""
        results = [
            {'name': 'small.txt', 'size': 1, 'mtime': 0, 'path': ''},
            {'name': 'large.txt', 'size': 100, 'mtime': 0, 'path': ''}
        ]
        
        sorted_asc = search_tool.sort_results(results, 'size', reverse=False)
        sorted_desc = search_tool.sort_results(results, 'size', reverse=True)
        
        assert sorted_asc[0]['name'] == 'small.txt'
        assert sorted_desc[0]['name'] == 'large.txt'

    def test_sort_results_by_mtime(self, search_tool, temp_test_dir):
        """测试按修改时间排序"""
        file1 = os.path.join(temp_test_dir, 'old.txt')
        file2 = os.path.join(temp_test_dir, 'new.txt')
        
        with open(file1, 'w') as f:
            f.write('old')
        time.sleep(0.1)
        with open(file2, 'w') as f:
            f.write('new')
        
        results = [
            {'name': 'old.txt', 'size': 0, 'mtime': os.path.getmtime(file1), 'path': ''},
            {'name': 'new.txt', 'size': 0, 'mtime': os.path.getmtime(file2), 'path': ''}
        ]
        
        sorted_asc = search_tool.sort_results(results, 'mtime', reverse=False)
        sorted_desc = search_tool.sort_results(results, 'mtime', reverse=True)
        
        assert sorted_asc[0]['name'] == 'old.txt'
        assert sorted_desc[0]['name'] == 'new.txt'

    def test_sort_results_invalid_key(self, search_tool):
        """测试无效排序键"""
        results = [{'name': 'test.txt', 'size': 0, 'mtime': 0, 'path': ''}]
        sorted_results = search_tool.sort_results(results, 'invalid_key')
        assert len(sorted_results) == 1


class TestCSVExport:
    """测试CSV导出功能"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    def test_export_results_to_csv(self, search_tool, temp_test_dir):
        """测试导出CSV文件"""
        results = [
            {'path': '/test1.txt', 'name': 'test1.txt', 'mtime': 123456789, 'size': 100},
            {'path': '/test2.txt', 'name': 'test2.txt', 'mtime': 987654321, 'size': 200}
        ]
        
        output_csv = os.path.join(temp_test_dir, 'results.csv')
        search_tool.export_results_to_csv(results, output_csv)
        
        assert os.path.exists(output_csv)
        
        with open(output_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(results)
            assert 'path' in reader.fieldnames
            assert 'name' in reader.fieldnames


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    def test_full_workflow(self, search_tool, temp_test_dir):
        """测试完整工作流程：搜索 -> 过滤 -> 排序 -> 导出"""
        # 创建测试文件
        files = [
            ('test_report.txt', 'report content'),
            ('test_data.csv', 'data'),
            ('sample.txt', 'sample'),
            ('test_image.jpg', '')
        ]
        
        for filename, content in files:
            file_path = os.path.join(temp_test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                if content:
                    f.write(content)
        
        # 1. 搜索
        results = search_tool.search_files(temp_test_dir, 'test')
        assert len(results) == 3
        
        # 2. 过滤
        filtered = search_tool.filter_files_by_type(results, ['.txt', '.csv'])
        assert len(filtered) == 2
        
        # 3. 排序
        sorted_results = search_tool.sort_results(filtered, 'name')
        assert sorted_results[0]['name'] < sorted_results[1]['name']
        
        # 4. 导出
        output_csv = os.path.join(temp_test_dir, 'workflow_test.csv')
        search_tool.export_results_to_csv(sorted_results, output_csv)
        assert os.path.exists(output_csv)


class TestErrorHandling:
    """测试容错处理"""

    @pytest.fixture
    def search_tool(self):
        return FileSearchTool()

    def test_search_invalid_path(self, search_tool):
        """测试搜索无效路径返回空结果"""
        results = search_tool.search_files('/nonexistent/path', 'test')
        assert results == []

    def test_preview_invalid_file(self, search_tool):
        """测试预览无效文件的容错"""
        result = search_tool.preview_file('/nonexistent/file.txt')
        assert result['type'] == 'error'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
