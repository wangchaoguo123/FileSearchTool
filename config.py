"""
配置模块 - 集中管理程序中的所有配置信息

提供配置项的定义、初始化、验证功能，支持通过环境变量覆盖默认值。
"""

import os
import logging
from typing import Optional, Dict, Any


class Config:
    """
    配置类 - 封装所有配置项
    
    所有配置项作为类属性存储，便于访问和维护。
    """
    
    # ==================== 基础配置 ====================
    DEBUG_MODE: bool = False
    """调试模式开关，True启用调试模式，False为生产模式"""
    
    APP_NAME: str = "本地文件搜索工具"
    """应用程序名称"""
    
    APP_VERSION: str = "1.0.0"
    """应用程序版本号"""
    
    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "DEBUG"
    """日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL"""
    
    LOG_DIR: str = "Log"
    """日志文件存储目录"""
    
    LOG_FILE_PREFIX: str = "info"
    """日志文件前缀"""
    
    LOG_MAX_SIZE: int = 5 * 1024 * 1024
    """单个日志文件最大大小（字节），默认5MB"""
    
    LOG_BACKUP_COUNT: int = 5
    """保留的日志文件备份数量"""
    
    # ==================== 搜索配置 ====================
    SEARCH_MAX_LINES: int = 100
    """文本预览时最大读取行数"""
    
    SEARCH_MAX_CHARS: int = 50000
    """文本预览时最大读取字符数"""
    
    PREVIEW_IMAGE_MAX_SIZE: int = 400
    """图片预览时的最大尺寸（像素）"""
    
    # ==================== 数据库配置（预留） ====================
    DB_CONNECTION_STRING: Optional[str] = None
    """数据库连接字符串，例如：sqlite:///data.db"""
    
    DB_POOL_SIZE: int = 5
    """数据库连接池大小"""
    
    DB_POOL_MAX_OVERFLOW: int = 10
    """数据库连接池最大溢出数"""
    
    # ==================== API配置（预留） ====================
    API_KEY: Optional[str] = None
    """API密钥"""
    
    API_BASE_URL: str = "https://api.example.com"
    """API基础URL"""
    
    API_TIMEOUT: int = 30
    """API请求超时时间（秒）"""
    
    # ==================== UI配置 ====================
    WINDOW_WIDTH: int = 850
    """主窗口宽度"""
    
    WINDOW_HEIGHT: int = 550
    """主窗口高度"""
    
    WINDOW_X: int = 350
    """主窗口X坐标"""
    
    WINDOW_Y: int = 150
    """主窗口Y坐标"""

    NUM_COLUMNS: int = 4
    """主窗口文件类型复选框列数"""
    
    # ==================== 文件类型配置 ====================
    TEXT_EXTENSIONS: list = [
        '.txt', '.md', '.rtf', '.py', '.java', '.c', '.cpp', '.h',
        '.js', '.html', '.css', '.json', '.xml', '.csv', '.log',
        '.ini', '.cfg', '.bat', '.sh', '.conf'
    ]
    """支持预览的文本文件扩展名列表"""
    
    IMAGE_EXTENSIONS: list = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico'
    ]
    """支持预览的图片文件扩展名列表"""

    PRESET_TYPES: list = [
        ("文本文件", [".txt", ".md", ".rtf"]),
        ("Office文档", [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf"]),
        ("图片文件", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]),
        ("视频文件", [".mp4", ".avi", ".mov", ".wmv", ".mkv", ".flv"]),
        ("音频文件", [".mp3", ".wav", ".flac", ".aac", ".wma", ".ogg"]),
        ("压缩文件", [".zip", ".rar", ".7z", ".tar", ".gz"]),
        ("代码文件", [".py", ".java", ".c", ".cpp", ".h", ".js", ".html", ".css", ".json"]),
    ]
    """预设文件类型列表"""

    # ==================== 配置项元数据 ====================
    _REQUIRED_CONFIGS: list = []
    """必需配置项列表，用于验证"""
    
    _CONFIG_DESCRIPTIONS: Dict[str, str] = {
        'DEBUG_MODE': '调试模式开关',
        'APP_NAME': '应用程序名称',
        'APP_VERSION': '应用程序版本号',
        'LOG_LEVEL': '日志级别',
        'LOG_DIR': '日志文件存储目录',
        'LOG_FILE_PREFIX': '日志文件前缀',
        'LOG_MAX_SIZE': '单个日志文件最大大小（字节）',
        'LOG_BACKUP_COUNT': '保留的日志文件备份数量',
        'SEARCH_MAX_LINES': '文本预览时最大读取行数',
        'SEARCH_MAX_CHARS': '文本预览时最大读取字符数',
        'PREVIEW_IMAGE_MAX_SIZE': '图片预览时的最大尺寸（像素）',
        'DB_CONNECTION_STRING': '数据库连接字符串',
        'DB_POOL_SIZE': '数据库连接池大小',
        'DB_POOL_MAX_OVERFLOW': '数据库连接池最大溢出数',
        'API_KEY': 'API密钥',
        'API_BASE_URL': 'API基础URL',
        'API_TIMEOUT': 'API请求超时时间（秒）',
        'WINDOW_WIDTH': '主窗口宽度',
        'WINDOW_HEIGHT': '主窗口高度',
        'WINDOW_X': '主窗口X坐标',
        'WINDOW_Y': '主窗口Y坐标',
        'TEXT_EXTENSIONS': '支持预览的文本文件扩展名列表',
        'IMAGE_EXTENSIONS': '支持预览的图片文件扩展名列表',
        'PRESET_TYPES': '预设文件类型列表',
    }
    """配置项描述字典"""


def parse_log_level(level_str: str) -> int:
    """
    将日志级别字符串转换为logging模块的常量
    
    参数:
        level_str: 日志级别字符串（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    
    返回值:
        logging模块对应的日志级别常量
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_str.upper(), logging.DEBUG)


def init_config() -> None:
    """
    初始化配置 - 从环境变量读取配置项并覆盖默认值
    
    环境变量命名规则：
        - 配置类名 + 下划线 + 配置项名
        - 例如：CONFIG_DEBUG_MODE, CONFIG_LOG_LEVEL
    
    类型转换规则：
        - bool: 'true'/'false' (不区分大小写)
        - int: 直接转换为整数
        - list: 逗号分隔的字符串
        - str: 直接使用
    """
    # 遍历Config类的所有属性
    for attr_name in dir(Config):
        # 跳过私有属性和方法
        if attr_name.startswith('_') or callable(getattr(Config, attr_name)):
            continue
        
        # 尝试从环境变量读取
        env_var_name = f"CONFIG_{attr_name}"
        env_value = os.environ.get(env_var_name)
        
        if env_value is not None:
            # 获取原值类型，进行相应的类型转换
            original_value = getattr(Config, attr_name)
            
            if isinstance(original_value, bool):
                # 布尔类型转换
                new_value = env_value.lower() in ('true', '1', 'yes', 'on')
                setattr(Config, attr_name, new_value)
                
            elif isinstance(original_value, int):
                # 整数类型转换
                try:
                    new_value = int(env_value)
                    setattr(Config, attr_name, new_value)
                except ValueError:
                    print(f"警告: 无法将环境变量 {env_var_name} 的值 '{env_value}' 转换为整数，使用默认值")
                    
            elif isinstance(original_value, list):
                # 列表类型转换（逗号分隔）
                new_value = [item.strip() for item in env_value.split(',') if item.strip()]
                setattr(Config, attr_name, new_value)
                
            elif isinstance(original_value, str) or original_value is None:
                # 字符串类型（包括None）
                if env_value.lower() == 'none' or env_value == '':
                    setattr(Config, attr_name, None)
                else:
                    setattr(Config, attr_name, env_value)


def validate_config() -> bool:
    """
    验证配置的有效性
    
    返回值:
        bool: 配置有效返回True，否则返回False
    
    验证内容：
        1. 检查所有必需配置项是否已设置
        2. 检查配置项的值是否在合理范围内
        3. 检查日志级别是否有效
    """
    is_valid = True
    errors = []
    
    # 1. 检查必需配置项
    for config_name in Config._REQUIRED_CONFIGS:
        value = getattr(Config, config_name, None)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            errors.append(f"必需配置项 '{config_name}' 未设置")
            is_valid = False
    
    # 2. 检查日志级别
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if Config.LOG_LEVEL.upper() not in valid_log_levels:
        errors.append(f"日志级别 '{Config.LOG_LEVEL}' 无效，有效值为: {', '.join(valid_log_levels)}")
        is_valid = False
    
    # 3. 检查数值配置项是否为正数
    numeric_configs = [
        ('LOG_MAX_SIZE', Config.LOG_MAX_SIZE),
        ('LOG_BACKUP_COUNT', Config.LOG_BACKUP_COUNT),
        ('SEARCH_MAX_LINES', Config.SEARCH_MAX_LINES),
        ('SEARCH_MAX_CHARS', Config.SEARCH_MAX_CHARS),
        ('PREVIEW_IMAGE_MAX_SIZE', Config.PREVIEW_IMAGE_MAX_SIZE),
        ('DB_POOL_SIZE', Config.DB_POOL_SIZE),
        ('DB_POOL_MAX_OVERFLOW', Config.DB_POOL_MAX_OVERFLOW),
        ('API_TIMEOUT', Config.API_TIMEOUT),
        ('WINDOW_WIDTH', Config.WINDOW_WIDTH),
        ('WINDOW_HEIGHT', Config.WINDOW_HEIGHT),
    ]
    
    for config_name, value in numeric_configs:
        if isinstance(value, int) and value <= 0:
            errors.append(f"配置项 '{config_name}' 的值必须为正数，当前值: {value}")
            is_valid = False
    
    # 输出验证结果
    if errors:
        print("=" * 60)
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        print("=" * 60)
    else:
        print("配置验证通过")
    
    return is_valid


def get_config_summary() -> Dict[str, Any]:
    """
    获取当前配置的摘要信息
    
    返回值:
        Dict[str, Any]: 包含所有配置项及其值的字典
    """
    summary = {}
    for attr_name in dir(Config):
        if attr_name.startswith('_') or callable(getattr(Config, attr_name)):
            continue
        summary[attr_name] = getattr(Config, attr_name)
    return summary


def print_config_summary() -> None:
    """
    打印当前配置摘要（用于调试）
    """
    print("=" * 60)
    print("当前配置摘要:")
    print("=" * 60)
    
    summary = get_config_summary()
    for key, value in sorted(summary.items()):
        description = Config._CONFIG_DESCRIPTIONS.get(key, '')
        if description:
            print(f"  {key}: {value}  # {description}")
        else:
            print(f"  {key}: {value}")
    
    print("=" * 60)


# 模块初始化时自动执行配置初始化
init_config()
