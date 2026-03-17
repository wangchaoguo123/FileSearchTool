"""
用于生成可执行文件
"""

import os
import sys
import shutil
import subprocess

'''
程序项目创建独立的虚拟环境
1.创建虚拟环境（命名为 .venv）
    python -m venv .venv
2.激活虚拟环境（不同系统命令不同）
    Windows (CMD)	.venv\Scripts\activate.bat
    Windows (PowerShell)	.venv\Scripts\Activate.ps1（需先执行：Set-ExecutionPolicy RemoteSigned）
    macOS/Linux (bash/zsh)	source .venv/bin/activate
3.退出虚拟环境
    deactivate

python.exe -m pip install --upgrade pip
'''

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 检查是否安装了PyInstaller
try:
    import PyInstaller  # 仅用于检查安装状态，无实际调用
except ImportError:
    print("需要安装PyInstaller: pip install pyinstaller")
    sys.exit(1)

# 配置项（可根据实际需求修改）
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")  # 要打包的主脚本
OUT_FILE_NAME = "FileSearchTool"  # 使用英文名称避免编码问题
SET_ICON_FLG = 1
ICON_PATH = os.path.join(PROJECT_ROOT, "img", "tb.ico")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
# 打包模式: True=单文件模式(--onefile), False=目录模式(--onedir)
ONE_FILE_MODE = True

# 需要通过 PyInstaller --add-data 参数打包的资源文件
PYINSTALLER_DATAS = [
    # 格式: (源路径, 目标相对路径)
    (os.path.join(PROJECT_ROOT, "img"), "img"),  # img 文件夹
]

# 需要复制到 dist 目录的非代码文件和文件夹配置
RESOURCE_FILES = [
    # 格式: (源路径, 目标相对路径)
    # 目标相对路径为 None 或 "" 表示复制到 dist 根目录
    (os.path.join(PROJECT_ROOT, "README.md"), ""),  # 说明文档
]
# 是否启用资源文件复制功能
COPY_RESOURCES_FLG = 1

def check_icon():
    """检查图标文件是否有效"""
    if not os.path.exists(ICON_PATH):
        print(f"错误：图标文件 {ICON_PATH} 不存在！")
        sys.exit(1)
    if not ICON_PATH.endswith(".ico"):
        print("错误：图标文件必须是.ico格式！")
        sys.exit(1)

def copy_resources():
    """复制非代码文件和文件夹到 dist 目录"""
    if not COPY_RESOURCES_FLG:
        print("资源文件复制功能已禁用，跳过")
        return
    
    print("\n开始复制资源文件...")
    copied_count = 0
    
    for src_path, dest_rel_path in RESOURCE_FILES:
        if not os.path.exists(src_path):
            print(f"警告：源路径不存在，跳过 - {src_path}")
            continue
        
        # 构建目标路径
        if dest_rel_path:
            dest_path = os.path.join(DIST_DIR, dest_rel_path)
        else:
            dest_path = os.path.join(DIST_DIR, os.path.basename(src_path))
        
        try:
            if os.path.isdir(src_path):
                # 复制目录
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(src_path, dest_path)
                print(f"已复制目录: {os.path.basename(src_path)} -> {dest_rel_path or './'}")
            else:
                # 复制文件
                dest_dir = os.path.dirname(dest_path)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                shutil.copy2(src_path, dest_path)
                print(f"已复制文件: {os.path.basename(src_path)} -> {dest_rel_path or './'}")
            copied_count += 1
        except Exception as e:
            print(f"错误：复制失败 - {src_path}，原因: {str(e)}")
    
    print(f"资源文件复制完成，共复制 {copied_count} 项")

def build_executable():
    """构建可执行文件"""
    # 0. 检查前置条件
    if SET_ICON_FLG:
        check_icon()

    # 1. 检查主脚本是否存在
    if not os.path.exists(MAIN_SCRIPT):
        print(f"错误：主脚本文件 {MAIN_SCRIPT} 不存在！")
        sys.exit(1)
    
    # 2. 清理之前的构建文件
    for dir_name in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理旧目录: {dir_name}")
    
    # 3. 构建PyInstaller命令
    pyinstaller_cmd = [
        "pyinstaller",
        "--windowed",         # 无控制台窗口（GUI程序适用）
        "--clean",            # 清理临时文件
        "--noconfirm",        # 覆盖输出目录不询问
        f"--name={OUT_FILE_NAME}",  # 可执行文件名称
    ]
    
    # 选择打包模式
    if ONE_FILE_MODE:
        pyinstaller_cmd.append("--onefile")
    else:
        pyinstaller_cmd.append("--onedir")
    
    # 添加图标（如果启用）
    if SET_ICON_FLG:
        pyinstaller_cmd.append(f"--icon={ICON_PATH}")
    
    # 添加 --add-data 参数来打包资源文件
    for src_path, dest_rel_path in PYINSTALLER_DATAS:
        if os.path.exists(src_path):
            # Windows 使用 ; 分隔，Linux/macOS 使用 :
            sep = ";" if os.name == "nt" else ":"
            pyinstaller_cmd.append(f"--add-data={src_path}{sep}{dest_rel_path}")
    
    # 添加主脚本
    pyinstaller_cmd.append(MAIN_SCRIPT)
    
    # 4. 执行打包命令并检查结果
    try:
        print(f"开始执行打包命令: {' '.join(pyinstaller_cmd)}")
        print("-" * 60)
        
        # 不捕获输出，直接显示到控制台
        result = subprocess.run(
            pyinstaller_cmd,
            check=True,
            cwd=PROJECT_ROOT
        )
        
        print("-" * 60)
        print("PyInstaller打包命令执行成功！")
    except subprocess.CalledProcessError as e:
        print(f"打包命令执行失败，返回码: {e.returncode}")
        print("\n请检查：")
        print("1. 确保已激活虚拟环境")
        print("2. 确保PyInstaller已正确安装: pip install pyinstaller")
        print("3. 检查是否有语法错误")
        sys.exit(1)
    
    # 5. 检查dist目录是否存在
    if not os.path.exists(DIST_DIR):
        print("构建失败，未生成dist目录")
        sys.exit(1)
    
    # 6. 复制资源文件到 dist 目录
    copy_resources()
    
    # 7. 查找生成的可执行文件
    exe_files = []
    for file in os.listdir(DIST_DIR):
        if file.endswith('.exe') or (not file.endswith('.py') and os.access(os.path.join(DIST_DIR, file), os.X_OK)):
            exe_files.append(file)
    
    if exe_files:
        print(f"\n构建完成！")
        print(f"可执行文件位于: {DIST_DIR}")
        for exe in exe_files:
            print(f"  - {exe}")
    else:
        print(f"\n构建完成，但未找到可执行文件在 {DIST_DIR} 目录")

if __name__ == "__main__":
    try:
        build_executable()
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程出现未预期错误：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)