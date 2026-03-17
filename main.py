import sys
import os
import csv
import datetime
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 导入配置模块
from config import (
    Config,
    init_config,
    validate_config,
    parse_log_level
)

# 尝试导入PIL库用于图片预览
PIL_AVAILABLE = False
Image = None
ImageQt = None

# 全局日志记录器
logger = None


def get_app_root_path():
    """
    获取应用程序根目录路径，兼容开发环境和打包后的环境
    
    返回值:
        str: 应用程序根目录的绝对路径
    """
    if hasattr(sys, 'frozen'):
        # 打包环境：使用可执行文件所在目录
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境：使用当前脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))


def setup_logging():
    """
    配置日志系统 - 使用Config模块中的配置
    
    功能说明：
    1. 从Config模块读取日志配置
    2. 设置日志级别为Config.LOG_LEVEL
    3. 创建日志文件：Config.LOG_DIR/Config.LOG_FILE_PREFIX_YYMMDD.log
    4. 文件最大大小：Config.LOG_MAX_SIZE
    5. 保留备份数量：Config.LOG_BACKUP_COUNT
    6. 控制台输出INFO及以上级别的日志
    7. 文件日志包含：时间、日志级别、消息、文件名、行号
    8. 控制台日志包含：时间、日志级别、消息
    """
    global logger
    
    # 创建日志目录（如果不存在）
    log_dir = os.path.join(get_app_root_path(), Config.LOG_DIR)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名：Config.LOG_FILE_PREFIX_YYMMDD.log
    today = datetime.datetime.now().strftime("%y%m%d")
    log_filename = os.path.join(log_dir, f"{Config.LOG_FILE_PREFIX}_{today}.log")
    
    # 获取日志记录器
    logger = logging.getLogger("FileSearchTool")
    
    # 从Config读取日志级别
    log_level = parse_log_level(Config.LOG_LEVEL)
    logger.setLevel(log_level)
    logger.propagate = False  # 防止日志传播到父记录器
    
    # 清除已有的处理器（防止重复添加）
    if logger.handlers:
        logger.handlers.clear()
    
    # ============================================
    # 文件日志处理器 - 记录所有级别日志
    # ============================================
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 使用RotatingFileHandler实现日志文件轮转
    # 从Config读取配置
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # ============================================
    # 控制台日志处理器 - 只输出INFO及以上级别
    # ============================================
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info("=" * 50)
    logger.info("日志系统初始化完成")
    logger.info(f"应用名称: {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"日志文件: {log_filename}")
    logger.info(f"调试模式: {'开启' if Config.DEBUG_MODE else '关闭'}")
    logger.info("=" * 50)

try:
    import PIL
    from PIL import Image
    try:
        from PIL.ImageQt import ImageQt
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
except ImportError:
    PIL_AVAILABLE = False

# 设置Qt插件路径
def fix_qt_plugin_path():
    """
    修复Qt插件路径，确保应用程序能够正确加载Qt插件
    
    该函数处理两种情况：
    1. 当应用程序被冻结打包（如使用PyInstaller）时，使用sys._MEIPASS获取基础路径
    2. 当应用程序在开发环境中运行时，从PyQt5安装目录获取基础路径
    
    然后构建插件路径并检查其是否存在，如果存在则：
    - 将插件路径添加到QCoreApplication的库路径中
    - 设置QT_PLUGIN_PATH环境变量
    
    这样可以确保Qt相关功能（如文件对话框、图标等）在不同运行环境中都能正常工作
    """
    if hasattr(sys, 'frozen'):
        base_path = sys._MEIPASS
    else:
        import PyQt5
        base_path = os.path.dirname(PyQt5.__file__)
    
    plugin_path = os.path.join(base_path, 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        QCoreApplication.addLibraryPath(plugin_path)
        os.environ['QT_PLUGIN_PATH'] = plugin_path

# 搜索线程（防止界面卡死）
class SearchThread(QThread):
    file_found = pyqtSignal(str)
    search_finished = pyqtSignal()
    progress_updated = pyqtSignal(int, int)
    total_counted = pyqtSignal(int)

    def __init__(self, root_path, keyword, file_types=None):
        """
        初始化搜索线程
        
        参数:
            root_path (str): 要搜索的根目录路径
            keyword (str): 搜索关键词，会自动转换为小写进行不区分大小写的匹配
            file_types (list, optional): 要搜索的文件类型列表，如 ['.txt', '.docx']，默认为None表示所有类型
        
        该方法完成以下初始化操作：
        1. 调用父类QThread的构造函数
        2. 保存要搜索的根目录路径
        3. 将关键词转换为小写并保存，以便进行不区分大小写的匹配
        4. 保存文件类型过滤器列表，转换为小写以便匹配
        5. 初始化运行状态标志is_running为True，表示线程正在运行
        6. 初始化总文件数和已处理文件数
        """
        super().__init__()
        self.root_path = root_path
        self.keyword = keyword.lower()
        self.is_running = True
        self.total_files = 0
        self.processed_files = 0
        self.found_files = []
        
        if file_types:
            self.file_types = [ext.lower() for ext in file_types]
        else:
            self.file_types = None
        
        if logger:
            logger.debug(f"SearchThread初始化 - 路径: {root_path}, 关键词: {keyword}, 文件类型: {file_types}")

    def matches_file_type(self, filename):
        """
        检查文件名是否匹配指定的文件类型
        
        参数:
            filename (str): 要检查的文件名
        
        返回值:
            bool: 如果文件名匹配指定的文件类型或没有指定类型则返回True，否则返回False
        
        该方法会检查文件的扩展名是否在指定的文件类型列表中
        """
        if not self.file_types:
            return True
        
        _, ext = os.path.splitext(filename.lower())
        return ext in self.file_types

    def count_total_files(self):
        """
        统计目录下的总文件数
        
        返回值:
            int: 目录下匹配文件类型的总文件数量
        
        该方法会快速遍历目录，统计符合文件类型过滤条件的文件总数，用于计算搜索进度
        """
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                if not self.is_running:
                    break
                for file in filenames:
                    if self.matches_file_type(file):
                        count += 1
        except Exception as e:
            if logger:
                logger.warning(f"统计文件数时出错: {str(e)}")
        return count

    def run(self):
        """
        执行搜索任务的主方法，线程启动后会自动调用此方法
        
        该方法完成以下操作：
        1. 先统计目录下符合文件类型条件的总文件数
        2. 发射total_counted信号，传递总文件数
        3. 使用os.walk()递归遍历指定根目录下的所有文件和子目录
        4. 在遍历过程中，检查is_running标志，如果为False则停止遍历
        5. 对于每个文件，先检查是否匹配文件类型
        6. 如果匹配文件类型，再将文件名转换为小写后检查是否包含关键词
        7. 如果都匹配成功，收集文件信息到found_files列表
        8. 每处理一个符合文件类型的文件，更新已处理文件数并发射progress_updated信号
        9. 遍历完成后，发射search_finished信号，通知主线程搜索结束
        
        异常处理:
            - 使用try-except捕获所有异常，避免搜索过程中的错误导致程序崩溃
            - 即使发生异常，也会确保发射search_finished信号
        """
        if logger:
            logger.debug("SearchThread.run()开始执行")
        try:
            # 第一步：统计总文件数并通知主线程
            if logger:
                logger.debug("开始统计总文件数")
            self.total_files = self.count_total_files()
            if logger:
                logger.info(f"统计完成，总文件数: {self.total_files}")
            self.total_counted.emit(self.total_files)
            
            # 初始化处理计数器和结果列表
            self.processed_files = 0
            self.found_files = []
            
            # 第二步：递归遍历目录
            if logger:
                logger.debug("开始递归遍历目录")
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                # 检查是否需要停止搜索
                if not self.is_running:
                    if logger:
                        logger.info("搜索被用户中断")
                    break
                
                # 遍历当前目录下的所有文件
                for file in filenames:
                    # 再次检查停止标志，确保及时响应停止请求
                    if not self.is_running:
                        break
                    
                    # 先检查文件类型是否匹配
                    if not self.matches_file_type(file):
                        continue
                    
                    # 增加已处理文件计数
                    self.processed_files += 1
                    
                    # 检查文件名是否包含关键词（不区分大小写）
                    if self.keyword in file.lower():
                        # 构建完整文件路径
                        full_path = os.path.join(dirpath, file)
                        try:
                            # 获取文件属性信息
                            stat = os.stat(full_path)
                            # 构建文件信息字典
                            file_info = {
                                'path': full_path,
                                'name': file.lower(),
                                'mtime': stat.st_mtime,  # 修改时间戳
                                'size': stat.st_size      # 文件大小（字节）
                            }
                            # 保存文件信息到结果列表
                            self.found_files.append(file_info)
                            # 通知主线程找到匹配文件
                            self.file_found.emit(full_path)
                        except:
                            # 如果获取文件属性失败，保存基本信息
                            self.found_files.append({'path': full_path, 'name': file.lower(), 'mtime': 0, 'size': 0})
                            self.file_found.emit(full_path)
                    
                    # 更新进度条（如果统计到了总文件数）
                    if self.total_files > 0 and self.processed_files % 100 == 0:
                        self.progress_updated.emit(self.processed_files, self.total_files)
            
            if logger:
                logger.info(f"搜索完成，找到 {len(self.found_files)} 个匹配文件")
        except Exception as e:
            # 捕获所有异常，确保搜索线程不会崩溃
            if logger:
                logger.error(f"搜索过程中发生异常: {str(e)}")
            pass
        
        # 无论搜索是否成功或中断，都发送完成信号
        if logger:
            logger.debug("发送search_finished信号")
        self.search_finished.emit()

    def stop(self):
        """
        停止搜索线程
        
        该方法将is_running标志设置为False，run()方法在遍历过程中会检查此标志，
        如果为False则会中断遍历，从而停止搜索。
        
        注意：
            - 该方法不会立即终止线程，而是通过设置标志让线程优雅地退出
            - 线程会在完成当前文件的处理后停止
        """
        self.is_running = False

# 主界面（美观版）
class FileSearchTool(QMainWindow):
    def __init__(self):
        """
        初始化文件搜索工具主窗口 - 使用Config模块配置
        
        该方法完成以下初始化操作：
        1. 调用父类构造函数
        2. 设置窗口标题为Config.APP_NAME
        3. 设置窗口几何位置和大小（从Config读取）
        4. 初始化搜索线程为None
        5. 初始化搜索结果列表为空
        6. 设置全局样式表
        7. 设置应用程序图标
        8. 初始化用户界面组件
        """
        if logger:
            logger.debug("FileSearchTool.__init__()开始执行")
        super().__init__()
        self.setWindowTitle(Config.APP_NAME)
        self.setGeometry(Config.WINDOW_X, Config.WINDOW_Y, Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
        self.search_thread = None
        self.search_results = []
        self.setStyleSheet(self.get_global_style())
        self.set_app_icon()
        self.init_ui()
        if logger:
            logger.debug("FileSearchTool.__init__()执行完成")
    
    def set_app_icon(self):
        """
        设置应用程序图标
        
        该方法完成以下操作：
        1. 获取正确的基础路径（支持 PyInstaller 打包环境）
        2. 构建图标文件的完整路径
        3. 检查图标文件是否存在
        4. 如果存在，则设置窗口图标为该图标文件
        
        注意：
        - 支持开发环境和 PyInstaller 打包后的运行环境（--onefile 和 --onedir 两种模式）
        - 如果图标文件不存在，该方法会静默跳过，不设置图标
        """
        if hasattr(sys, 'frozen'):
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_path, "img", "tb.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def get_global_style(self):
        """
        获取全局样式表，定义应用程序的视觉风格
        
        返回值:
            str: 包含完整Qt样式表的字符串，定义了以下组件的样式：
            - QMainWindow: 设置背景颜色为#f8f9fa
            - QWidget: 设置全局字体为9pt "Microsoft YaHei UI"
            - QLineEdit: 设置输入框样式，包括内边距、边框、圆角等
            - QLineEdit:focus: 设置输入框获取焦点时的样式
            - QPushButton: 设置按钮基础样式
            - QPushButton#btnBrowse: 设置浏览按钮的背景颜色和悬停效果
            - QPushButton#btnStart: 设置开始搜索按钮的背景颜色和悬停效果
            - QPushButton#btnStop: 设置停止搜索按钮的背景颜色和悬停效果
            - QListWidget: 设置结果列表的样式，包括边框、内边距、背景色等
            - QListWidget::item: 设置列表项的样式
            - QListWidget::item:selected: 设置选中列表项的样式
            - QLabel: 设置标签的字体和颜色
        
        样式特点:
            - 使用现代化的圆角设计
            - 柔和的颜色搭配
            - 响应式的悬停效果
            - 清晰的视觉层次
        """
        return """
        QMainWindow {
            background-color: #f8f9fa;
        }
        QWidget {
            font: 9pt "Microsoft YaHei UI";
        }
        QLineEdit {
            padding: 10px 12px;
            border: 1px solid #dcdfe6;
            border-radius: 10px;
            background-color: white;
            font-size: 10pt;
        }
        QLineEdit:focus {
            border: 1px solid #66b1ff;
            outline: none;
        }
        QPushButton {
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 10pt;
            color: white;
            border: none;
        }
        QPushButton#btnBrowse {
            background-color: #909399;
        }
        QPushButton#btnBrowse:hover {
            background-color: #7a7e84;
        }
        QPushButton#btnStart {
            background-color: #409eff;
        }
        QPushButton#btnStart:hover {
            background-color: #338ecc;
        }
        QPushButton#btnStop {
            background-color: #f56c6c;
        }
        QPushButton#btnStop:hover {
            background-color: #e05454;
        }
        QListWidget {
            border: 1px solid #dcdfe6;
            border-radius: 10px;
            padding: 8px;
            background-color: white;
            alternate-background-color: #fafafa;
        }
        QListWidget::item {
            padding: 10px;
            border-radius: 6px;
        }
        QListWidget::item:selected {
            background-color: #e8f3ff;
            color: #303133;
        }
        QLabel {
            font-size: 9pt;
            color: #606266;
        }
        """

    def init_ui(self):
        """
        初始化用户界面组件
        
        该方法完成以下操作：
        1. 创建中央部件并设置为主窗口的中央部件
        2. 创建垂直布局作为主布局，设置间距为12像素，边距为20像素
        3. 创建并配置标题标签，设置为居中对齐，使用大字体和粗体
        4. 创建路径选择区域，包含路径输入框和浏览按钮
        5. 创建关键词输入框，设置占位文本提示用户输入示例
        6. 创建文件类型过滤器区域，包含复选框和自定义输入
        7. 创建按钮区域，包含开始搜索按钮和停止搜索按钮
        8. 创建进度条控件，用于显示搜索进度
        9. 创建结果列表，设置交替行颜色，并连接双击事件到打开文件功能
        10. 创建状态标签，用于显示搜索状态信息
        11. 将所有组件按顺序添加到主布局中
        
        布局结构:
            - 标题 (QLabel)
            - 路径区域 (QHBoxLayout: QLineEdit + QPushButton)
            - 关键词输入 (QLineEdit)
            - 文件类型过滤器 (QGroupBox)
            - 按钮区域 (QHBoxLayout: QPushButton + QPushButton)
            - 进度条 (QProgressBar)
            - 结果标签 (QLabel)
            - 结果列表 (QListWidget)
            - 状态标签 (QLabel)
        """
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("🔍 文件搜索工具")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #303133;")
        title.setAlignment(Qt.AlignCenter)

        # 路径区域
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择搜索路径...")
        self.browse_btn = QPushButton("浏览文件夹")
        self.browse_btn.setObjectName("btnBrowse")
        self.browse_btn.clicked.connect(self.select_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)

        # 关键词
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入关键词，如：报告、pdf、照片、文档...")

        # 文件类型过滤器
        type_group = QGroupBox("文件类型过滤器")
        type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #606266;
                border: 1px solid #dcdfe6;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        type_layout = QVBoxLayout(type_group)
        
        # 全选/全不选按钮
        select_btn_layout = QHBoxLayout()
        select_btn_layout.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 9pt;
                color: white;
                background-color: #409eff;
                border: none;
            }
            QPushButton:hover {
                background-color: #338ecc;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_types)
        select_btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("全不选")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 9pt;
                color: white;
                background-color: #909399;
                border: none;
            }
            QPushButton:hover {
                background-color: #7a7e84;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselect_all_types)
        select_btn_layout.addWidget(deselect_all_btn)
        
        type_layout.addLayout(select_btn_layout)
        
        # 预设文件类型复选框 - 多列布局
        checkbox_grid = QGridLayout()
        checkbox_grid.setSpacing(10)
        
        self.type_checkboxes = {}
        preset_types = Config.PRESET_TYPES
        
        # 设置列数
        num_columns = Config.NUM_COLUMNS
        
        for i, (label, extensions) in enumerate(preset_types):
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                    color: #606266;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #dcdfe6;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #409eff;
                    border-color: #409eff;
                }
            """)
            checkbox.setProperty("extensions", extensions)
            self.type_checkboxes[label] = checkbox
            
            # 计算行列位置
            row = i // num_columns
            col = i % num_columns
            checkbox_grid.addWidget(checkbox, row, col)
        
        type_layout.addLayout(checkbox_grid)
        
        # 自定义文件类型
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("自定义类型："))
        self.custom_type_edit = QLineEdit()
        self.custom_type_edit.setPlaceholderText("例如：.txt,.docx,.pdf（多个用逗号分隔）")
        custom_layout.addWidget(self.custom_type_edit)
        type_layout.addLayout(custom_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始搜索")
        self.start_btn.setObjectName("btnStart")
        self.stop_btn = QPushButton("停止搜索")
        self.stop_btn.setObjectName("btnStop")
        self.start_btn.clicked.connect(self.start_search)
        self.stop_btn.clicked.connect(self.stop_search)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("搜索进度: %p% (%v/%m)")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dcdfe6;
                border-radius: 10px;
                text-align: center;
                background-color: white;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #409eff;
                border-radius: 8px;
            }
        """)
        self.progress_bar.hide()

        # 排序区域
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("排序方式："))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "按名称（升序）",
            "按名称（降序）",
            "按修改时间（新→旧）",
            "按修改时间（旧→新）",
            "按大小（大→小）",
            "按大小（小→大）"
        ])
        self.sort_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                background-color: white;
                font-size: 9pt;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #909399;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #e8f3ff;
                selection-color: #303133;
                padding: 4px;
            }
        """)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        sort_layout.addWidget(self.sort_combo)
        
        sort_layout.addStretch()

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 结果列表区域
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        result_header_layout = QHBoxLayout()
        result_header_layout.addWidget(QLabel("搜索结果："))
        result_header_layout.addLayout(sort_layout)
        
        # 导出按钮
        self.export_btn = QPushButton("导出CSV")
        self.export_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 9pt;
                color: white;
                background-color: #67c23a;
                border: none;
            }
            QPushButton:hover {
                background-color: #5da834;
            }
        """)
        self.export_btn.clicked.connect(self.export_results)
        result_header_layout.addWidget(self.export_btn)
        
        result_layout.addLayout(result_header_layout)
        
        self.result_list = QListWidget()
        self.result_list.setAlternatingRowColors(True)
        self.result_list.doubleClicked.connect(self.open_file)
        self.result_list.itemClicked.connect(self.on_result_clicked)
        result_layout.addWidget(self.result_list)
        
        splitter.addWidget(result_widget)
        
        # 预览区域
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_label = QLabel("文件预览：")
        preview_label.setStyleSheet("font-weight: bold; color: #606266;")
        preview_layout.addWidget(preview_label)
        
        self.preview_content = QStackedWidget()
        
        # 文本预览
        self.text_preview = QTextBrowser()
        self.text_preview.setReadOnly(True)
        self.text_preview.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #dcdfe6;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
                font-family: Consolas, Monaco, monospace;
                font-size: 9pt;
            }
        """)
        self.preview_content.addWidget(self.text_preview)
        
        # 图片预览
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #dcdfe6;
                border-radius: 10px;
                background-color: white;
            }
        """)
        self.image_preview.setMinimumSize(200, 200)
        self.preview_content.addWidget(self.image_preview)
        
        # 无预览提示
        self.no_preview_label = QLabel("选择一个文件进行预览")
        self.no_preview_label.setAlignment(Qt.AlignCenter)
        self.no_preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #dcdfe6;
                border-radius: 10px;
                background-color: white;
                color: #909399;
                font-size: 10pt;
            }
        """)
        self.preview_content.addWidget(self.no_preview_label)
        
        preview_layout.addWidget(self.preview_content)
        
        # 文件信息标签
        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("""
            QLabel {
                color: #606266;
                font-size: 9pt;
                padding: 5px;
            }
        """)
        self.file_info_label.setWordWrap(True)
        preview_layout.addWidget(self.file_info_label)
        
        splitter.addWidget(preview_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 300])
        
        # 状态
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)

        # 组装
        main_layout.addWidget(title)
        main_layout.addLayout(path_layout)
        main_layout.addWidget(self.key_edit)
        main_layout.addWidget(type_group)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(self.status_label)
    
    def select_all_types(self):
        """
        全选所有预设文件类型
        
        该方法会将所有预设文件类型的复选框设置为选中状态
        """
        for checkbox in self.type_checkboxes.values():
            checkbox.setChecked(True)

    def deselect_all_types(self):
        """
        全不选所有预设文件类型
        
        该方法会将所有预设文件类型的复选框设置为未选中状态
        """
        for checkbox in self.type_checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_file_types(self):
        """
        获取用户选择的文件类型列表
        
        返回值:
            list or None: 返回选中的文件类型扩展名列表，如果没有选择任何类型则返回None（表示搜索所有类型）
        
        该方法会：
        1. 遍历所有预设文件类型复选框，收集选中的扩展名
        2. 解析自定义文件类型输入框中的内容
        3. 将所有扩展名合并到一个列表中并去重
        4. 如果没有选择任何类型，返回None
        """
        selected_extensions = []
        
        # 第一步：收集所有选中的预设文件类型
        for checkbox in self.type_checkboxes.values():
            # 检查复选框是否被选中
            if checkbox.isChecked():
                # 从复选框属性中获取对应的扩展名列表
                extensions = checkbox.property("extensions")
                # 将扩展名添加到结果列表中
                selected_extensions.extend(extensions)
        
        # 第二步：解析自定义文件类型输入
        custom_types = self.custom_type_edit.text().strip()
        if custom_types:
            # 按逗号分割，去除每个扩展名的首尾空格，过滤空字符串
            custom_extensions = [ext.strip() for ext in custom_types.split(',') if ext.strip()]
            # 将自定义扩展名添加到结果列表
            selected_extensions.extend(custom_extensions)
        
        # 第三步：去重处理
        if selected_extensions:
            # 使用set()去重，然后转回list
            return list(set(selected_extensions))
        else:
            # 如果没有选择任何类型，返回None表示搜索所有类型
            return None

    def select_path(self):
        """
        打开文件夹选择对话框，让用户选择搜索目录
        
        该方法完成以下操作：
        1. 调用QFileDialog.getExistingDirectory()打开目录选择对话框
        2. 对话框标题为"选择搜索目录"
        3. 如果用户选择了目录（即返回值不为空），则将目录路径设置到路径输入框中
        
        注意：
            - 如果用户点击了取消按钮，则不进行任何操作
        """
        path = QFileDialog.getExistingDirectory(self, "选择搜索目录")
        if path:
            self.path_edit.setText(path)

    def start_search(self):
        """
        开始文件搜索操作
        
        该方法完成以下操作：
        1. 获取用户输入的搜索路径和关键词（去除首尾空格）
        2. 验证路径和关键词是否为空，为空则显示警告信息并返回
        3. 获取用户选择的文件类型过滤器
        4. 清空结果列表和搜索结果缓存，准备显示新的搜索结果
        5. 显示并重置进度条
        6. 更新状态标签，显示正在搜索的关键词和提示信息
        7. 设置状态标签颜色为蓝色（#409eff）
        8. 创建SearchThread搜索线程，传入路径、关键词和文件类型过滤器
        9. 连接线程的file_found信号到add_result槽函数
        10. 连接线程的search_finished信号到search_finished槽函数
        11. 连接线程的progress_updated信号到update_progress槽函数
        12. 连接线程的total_counted信号到on_total_counted槽函数
        13. 启动搜索线程
        
        注意：
        - 该方法会在后台线程中执行搜索，避免阻塞主线程
        - 搜索过程中会实时更新结果列表和进度条
        - 如果用户没有选择任何文件类型，则搜索所有类型的文件
        """
        if logger:
            logger.debug("FileSearchTool.start_search()开始执行")
        
        path = self.path_edit.text().strip()
        key = self.key_edit.text().strip()

        if logger:
            logger.info(f"用户输入 - 路径: {path}, 关键词: {key}")

        if not path or not key:
            if logger:
                logger.warning("搜索参数验证失败：路径或关键词为空")
            QMessageBox.warning(self, "提示", "路径和关键词不能为空！")
            return

        # 验证路径是否存在
        if not os.path.exists(path):
            if logger:
                logger.warning(f"搜索路径不存在: {path}")
            QMessageBox.warning(self, "提示", "指定的路径不存在！")
            return

        # 验证路径是否是目录
        if not os.path.isdir(path):
            if logger:
                logger.warning(f"指定路径不是目录: {path}")
            QMessageBox.warning(self, "提示", "指定的路径不是有效的目录！")
            return

        # 验证路径是否可读
        if not os.access(path, os.R_OK):
            if logger:
                logger.warning(f"没有权限访问路径: {path}")
            QMessageBox.warning(self, "提示", "没有权限访问该目录！")
            return

        # 获取文件类型过滤器
        file_types = self.get_selected_file_types()
        if logger:
            logger.debug(f"选择的文件类型: {file_types}")
        
        self.result_list.clear()
        self.search_results = []
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFormat("正在统计文件总数...")
        self.progress_bar.show()
        
        # 更新状态信息，包含文件类型
        if file_types:
            type_str = ", ".join(file_types[:3])
            if len(file_types) > 3:
                type_str += "..."
            status_text = f"正在搜索「{key}」（类型：{type_str}），请稍候..."
        else:
            status_text = f"正在搜索「{key}」（所有类型），请稍候..."
        
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet("color: #409eff;")

        if logger:
            logger.info("创建并启动SearchThread")
        self.search_thread = SearchThread(path, key, file_types)
        self.search_thread.file_found.connect(self.add_result)
        self.search_thread.search_finished.connect(self.search_finished)
        self.search_thread.progress_updated.connect(self.update_progress)
        self.search_thread.total_counted.connect(self.on_total_counted)
        self.search_thread.start()

    def stop_search(self):
        """
        停止当前正在进行的搜索
        
        该方法完成以下操作：
        1. 检查搜索线程是否存在且正在运行
        2. 如果是，则调用搜索线程的stop()方法停止搜索
        3. 更新状态标签显示"搜索已停止"
        4. 设置状态标签颜色为红色（#f56c6c）
        5. 隐藏进度条
        
        注意：
            - 该方法不会立即终止线程，而是通过设置标志让线程优雅地退出
            - 只有当搜索线程实际存在且正在运行时才会执行停止操作
        """
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()
            self.status_label.setText("搜索已停止")
            self.status_label.setStyleSheet("color: #f56c6c;")
            self.progress_bar.hide()

    def update_progress(self, processed, total):
        """
        更新搜索进度条
        
        参数:
            processed (int): 已处理的文件数量
            total (int): 总文件数量
        
        该方法是SearchThread的progress_updated信号的槽函数，
        用于实时更新进度条的显示值。
        """
        if total > 0:
            percentage = int((processed / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"搜索进度: %p% ({processed}/{total})")

    def on_total_counted(self, total):
        """
        当总文件数统计完成时的处理函数
        
        参数:
            total (int): 统计得到的总文件数
        
        该方法是SearchThread的total_counted信号的槽函数，
        用于设置进度条的最大值和格式。
        """
        self.progress_bar.setMaximum(100)
        if total > 0:
            self.progress_bar.setFormat(f"搜索进度: %p% (0/{total})")
        else:
            self.progress_bar.setFormat("搜索进度: %p%")

    def add_result(self, path):
        """
        将找到的文件路径添加到结果列表中
        
        参数:
            path (str): 找到的文件的完整路径
        
        该方法是SearchThread的file_found信号的槽函数，每当搜索线程找到匹配的文件时，
        就会调用此方法将文件路径添加到结果列表中，实现实时更新搜索结果。
        """
        self.result_list.addItem(path)

    def search_finished(self):
        """
        搜索完成后的处理函数
        
        该方法是SearchThread的search_finished信号的槽函数，当搜索线程完成搜索时会调用此方法。
        
        该方法完成以下操作：
        1. 从搜索线程获取搜索结果列表
        2. 按照当前选择的排序方式对结果进行排序
        3. 更新结果列表显示
        4. 更新状态标签，显示搜索完成信息和找到的文件数量
        5. 设置状态标签颜色为绿色（#67c23a）
        6. 隐藏进度条
        
        状态信息格式: "搜索完成 · 共找到 X 个文件"
        """
        if logger:
            logger.debug("FileSearchTool.search_finished()开始执行")
        
        if self.search_thread:
            self.search_results = self.search_thread.found_files
            if logger:
                logger.info(f"获取到搜索结果数量: {len(self.search_results)}")
        
        self.apply_sort_and_update()
        
        total = len(self.search_results)
        self.status_label.setText(f"搜索完成 · 共找到 {total} 个文件")
        self.status_label.setStyleSheet("color: #67c23a;")
        self.progress_bar.hide()
        
        if logger:
            logger.info(f"搜索完成处理完毕，共显示 {total} 个结果")

    def on_sort_changed(self, index):
        """
        排序方式改变时的处理函数
        
        参数:
            index (int): 新选择的排序方式的索引
        
        该方法是排序下拉框currentIndexChanged信号的槽函数，
        当用户改变排序方式时会调用此方法重新排序并更新结果列表。
        """
        self.apply_sort_and_update()

    def apply_sort_and_update(self):
        """
        应用当前选择的排序方式并更新结果列表
        
        该方法会：
        1. 获取当前选择的排序方式
        2. 根据排序方式对搜索结果进行排序
        3. 清空并重新填充结果列表
        """
        if not self.search_results:
            return
        
        sort_index = self.sort_combo.currentIndex()
        sorted_results = self.sort_results(self.search_results, sort_index)
        
        self.result_list.clear()
        for file_info in sorted_results:
            self.result_list.addItem(file_info['path'])

    def sort_results(self, results, sort_index):
        """
        根据指定的排序方式对搜索结果进行排序
        
        参数:
            results (list): 搜索结果列表，每个元素是包含文件信息的字典
            sort_index (int): 排序方式索引
                0: 按名称（升序）
                1: 按名称（降序）
                2: 按修改时间（新→旧）
                3: 按修改时间（旧→新）
                4: 按大小（大→小）
                5: 按大小（小→大）
        
        返回值:
            list: 排序后的搜索结果列表
        """
        # 使用Python内置的sorted()函数配合lambda表达式进行排序
        # lambda x: x['key'] 指定排序关键字
        # reverse=True 表示降序排列，默认或reverse=False表示升序
        if sort_index == 0:
            # 按文件名字典序升序排列（A-Z）
            return sorted(results, key=lambda x: x['name'])
        elif sort_index == 1:
            # 按文件名字典序降序排列（Z-A）
            return sorted(results, key=lambda x: x['name'], reverse=True)
        elif sort_index == 2:
            # 按修改时间降序排列（新文件在前）
            return sorted(results, key=lambda x: x['mtime'], reverse=True)
        elif sort_index == 3:
            # 按修改时间升序排列（旧文件在前）
            return sorted(results, key=lambda x: x['mtime'])
        elif sort_index == 4:
            # 按文件大小降序排列（大文件在前）
            return sorted(results, key=lambda x: x['size'], reverse=True)
        elif sort_index == 5:
            # 按文件大小升序排列（小文件在前）
            return sorted(results, key=lambda x: x['size'])
        else:
            # 未知的排序方式，返回原始列表
            return results

    def on_result_clicked(self, item):
        """
        当用户点击搜索结果列表中的文件项时触发
        
        参数:
            item (QListWidgetItem): 被点击的列表项
        
        该方法会根据文件类型显示相应的预览内容
        """
        if not item:
            return
        
        file_path = item.text()
        self.show_file_preview(file_path)

    def show_file_preview(self, file_path):
        """
        显示文件预览内容 - 使用Config模块配置
        
        参数:
            file_path (str): 要预览的文件路径
        
        该方法会：
        1. 检查文件是否存在
        2. 获取文件基本信息并显示
        3. 根据文件扩展名判断文件类型（从Config读取）
        4. 对于文本文件，读取并显示前几行
        5. 对于图片文件，加载并缩放显示
        6. 对于其他类型文件，显示提示信息
        """
        if not os.path.exists(file_path):
            self.show_no_preview("文件不存在")
            return
        
        # 显示文件信息
        self.update_file_info(file_path)
        
        # 判断文件类型
        _, ext = os.path.splitext(file_path.lower())
        
        # 从Config模块读取文件类型配置
        text_extensions = Config.TEXT_EXTENSIONS
        image_extensions = Config.IMAGE_EXTENSIONS
        
        if ext in text_extensions:
            self.show_text_preview(file_path)
        elif ext in image_extensions:
            self.show_image_preview(file_path)
        else:
            self.show_no_preview(f"不支持预览 {ext} 类型的文件")

    def update_file_info(self, file_path):
        """
        更新文件信息显示
        
        参数:
            file_path (str): 文件路径
        """
        try:
            stat = os.stat(file_path)
            file_size = self.format_file_size(stat.st_size)
            import datetime
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
            
            info_text = f"""<b>文件名：</b> {os.path.basename(file_path)}<br>
<b>路径：</b> {file_path}<br>
<b>大小：</b> {file_size}<br>
<b>修改时间：</b> {mtime_str}"""
            
            self.file_info_label.setText(info_text)
        except Exception as e:
            self.file_info_label.setText(f"无法获取文件信息：{str(e)}")

    def format_file_size(self, size_bytes):
        """
        格式化文件大小为人类可读的格式
        
        参数:
            size_bytes (int): 文件大小（字节）
        
        返回值:
            str: 格式化后的文件大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def show_text_preview(self, file_path):
        """
        显示文本文件预览 - 使用Config模块配置
        
        参数:
            file_path (str): 文本文件路径
        
        该方法会读取文本文件的前Config.SEARCH_MAX_LINES行并显示
        """
        try:
            # 从Config模块读取预览限制
            max_lines = Config.SEARCH_MAX_LINES
            max_chars = Config.SEARCH_MAX_CHARS
            
            # 打开文件
            # 使用utf-8编码，errors='ignore'表示忽略无法解码的字符
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                char_count = 0
                
                # 逐行读取文件
                for i, line in enumerate(f):
                    # 检查是否超出限制
                    if i >= max_lines or char_count >= max_chars:
                        # 添加省略提示
                        lines.append("\n... (内容过长，仅显示前部分)")
                        break
                    
                    # 去除行尾的换行符，保留行内容
                    lines.append(line.rstrip('\n'))
                    # 累计字符数
                    char_count += len(line)
                
                # 将所有行用换行符连接成一个字符串
                content = '\n'.join(lines)
                # 设置到文本预览控件中
                self.text_preview.setPlainText(content)
                # 切换到文本预览页面
                self.preview_content.setCurrentWidget(self.text_preview)
        except Exception as e:
            # 如果读取失败，显示错误信息
            self.show_no_preview(f"无法读取文本文件：{str(e)}")

    def show_image_preview(self, file_path):
        """
        显示图片文件预览 - 使用Config模块配置
        
        参数:
            file_path (str): 图片文件路径
        
        该方法会：
        1. 使用Qt原生方式加载图片（不依赖PIL）
        2. 缩放图片到Config.PREVIEW_IMAGE_MAX_SIZE尺寸
        3. 显示图片
        """
        try:
            # 使用Qt原生方式加载图片（不依赖PIL）
            pixmap = QPixmap(file_path)
            
            if not pixmap.isNull():
                # 从Config模块读取最大尺寸
                max_size = Config.PREVIEW_IMAGE_MAX_SIZE
                if pixmap.width() > max_size or pixmap.height() > max_size:
                    # 获取缩放比例
                    ratio = min(max_size / pixmap.width(), max_size / pixmap.height())
                    new_width = int(pixmap.width() * ratio)
                    new_height = int(pixmap.height() * ratio)
                    pixmap = pixmap.scaled(new_width, new_height)
                self.image_preview.setPixmap(pixmap)
                self.preview_content.setCurrentWidget(self.image_preview)
                return
            else:
                self.show_no_preview("无法加载图片\n请确认文件是有效的图片格式")
                
        except Exception as e:
            self.show_no_preview(f"无法加载图片：{str(e)}")

    def show_no_preview(self, message):
        """
        显示无预览提示
        
        参数:
            message (str): 提示信息
        """
        self.no_preview_label.setText(message)
        self.preview_content.setCurrentWidget(self.no_preview_label)
        self.file_info_label.setText("")

    def export_results(self):
        """
        导出搜索结果为CSV文件
        
        该方法会：
        1. 检查是否有搜索结果可导出
        2. 打开文件保存对话框，让用户选择保存位置
        3. 生成默认文件名（包含时间戳）
        4. 将搜索结果写入CSV文件，包含以下列：
           - 文件名
           - 文件路径
           - 文件大小（字节）
           - 文件大小（格式化）
           - 修改时间
        5. 显示导出成功或失败的消息
        """
        if logger:
            logger.debug("FileSearchTool.export_results()开始执行")
        
        # 第一步：检查是否有搜索结果
        if not self.search_results:
            if logger:
                logger.warning("导出失败：没有搜索结果可导出")
            QMessageBox.information(self, "提示", "没有搜索结果可导出！")
            return
        
        if logger:
            logger.info(f"准备导出 {len(self.search_results)} 个搜索结果")
        
        # 第二步：生成带时间戳的默认文件名
        # 格式：搜索结果_YYYYMMDD_HHMMSS.csv
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"搜索结果_{timestamp}.csv"
        
        if logger:
            logger.debug(f"生成的默认文件名: {default_filename}")
        
        # 第三步：打开文件保存对话框
        # getSaveFileName返回两个值：文件路径和过滤器
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出搜索结果",
            default_filename,
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        # 检查用户是否点击了取消
        if not file_path:
            if logger:
                logger.info("用户取消了导出操作")
            return
        
        if logger:
            logger.info(f"用户选择的导出文件路径: {file_path}")
        
        try:
            # 第四步：写入CSV文件
            # 使用utf-8-sig编码，这样Excel可以正确打开中文
            # newline='' 避免csv模块自动添加空行
            if logger:
                logger.debug("开始写入CSV文件")
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # 定义CSV文件的列名
                fieldnames = ['文件名', '文件路径', '文件大小(字节)', '文件大小', '修改时间']
                # 创建DictWriter对象，用于按列名写入
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 写入表头（第一行）
                writer.writeheader()
                
                # 遍历所有搜索结果，逐行写入
                for file_info in self.search_results:
                    # 从文件信息字典中提取数据
                    file_path = file_info['path']
                    file_name = os.path.basename(file_path)  # 只获取文件名，不包含路径
                    file_size = file_info.get('size', 0)  # 获取文件大小，默认0
                    file_size_formatted = self.format_file_size(file_size)  # 格式化文件大小
                    
                    # 处理修改时间
                    mtime_str = ""
                    if file_info.get('mtime', 0) > 0:
                        # 将时间戳转换为datetime对象
                        mtime = datetime.datetime.fromtimestamp(file_info['mtime'])
                        # 格式化为可读的字符串
                        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 写入一行数据
                    writer.writerow({
                        '文件名': file_name,
                        '文件路径': file_path,
                        '文件大小(字节)': file_size,
                        '文件大小': file_size_formatted,
                        '修改时间': mtime_str
                    })
            
            # 第五步：显示成功提示
            if logger:
                logger.info(f"CSV文件写入成功，共导出 {len(self.search_results)} 条记录")
            QMessageBox.information(self, "成功", f"搜索结果已成功导出到：\n{file_path}")
            
        except Exception as e:
            # 捕获并显示任何异常
            if logger:
                logger.error(f"导出失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"导出失败：\n{str(e)}")

    def open_file(self):
        """
        打开用户在结果列表中双击选中的文件
        
        该方法是结果列表的doubleClicked信号的槽函数，当用户双击列表中的某个文件项时会调用此方法。
        
        该方法完成以下操作：
        1. 获取当前选中的列表项
        2. 如果没有选中项，则直接返回
        3. 获取选中项的文本内容（即文件路径）
        4. 尝试使用系统默认程序打开该文件
        
        平台兼容性:
            - Windows: 使用os.startfile()打开文件
            - macOS: 使用subprocess.run(["open", path])打开文件
            - Linux: 使用subprocess.run(["xdg-open", path])打开文件
        
        异常处理:
            - 如果打开文件失败，会记录错误并显示提示
        """
        item = self.result_list.currentItem()
        if not item:
            return
        path = item.text()
        
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", path], check=True)
            else:
                import subprocess
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            if logger:
                logger.error(f"无法打开文件 {path}: {str(e)}")
            QMessageBox.warning(self, "错误", f"无法打开文件：{str(e)}")

if __name__ == "__main__":
    # 配置模块已在导入时自动初始化（init_config()）
    
    # 验证配置
    is_config_valid = validate_config()
    if not is_config_valid:
        print("警告：配置验证失败，使用默认配置继续运行")
    
    # 初始化日志系统
    setup_logging()
    
    if logger:
        logger.debug("程序启动")
    
    # 先修复Qt插件路径
    if logger:
        logger.debug("开始修复Qt插件路径")
    fix_qt_plugin_path()
    if logger:
        logger.debug("Qt插件路径修复完成")
    
    # 创建应用程序
    if logger:
        logger.debug("创建QApplication")
    app = QApplication(sys.argv)
    
    # 创建主窗口
    if logger:
        logger.debug("创建FileSearchTool主窗口")
    window = FileSearchTool()
    
    # 显示窗口
    if logger:
        logger.debug("显示主窗口")
    window.show()
    
    if logger:
        logger.info("程序启动完成，进入主事件循环")
    # 进入主事件循环
    sys.exit(app.exec_())