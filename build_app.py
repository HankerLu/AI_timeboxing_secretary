import os
import sys
import shutil
import subprocess
from datetime import datetime

def clean_up():
    """清理构建文件"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    if os.path.exists('daily_planner.spec'):
        os.remove('daily_planner.spec')

def build_app():
    """构建应用程序"""
    try:
        # PyInstaller 命令行参数
        command = [
            sys.executable, '-m', 'PyInstaller',
            'daily_planner.py',
            '--name=DailyPlanner',
            '--onefile',
            '--windowed',
            '--clean',
            '--add-data', f'commands.db:.',
            '-i', 'app_icon.icns',  # 添加图标选项
        ]
        
        # 修改为 M1 芯片的 macOS 特定选项
        command.extend([
            '--target-architecture', 'arm64',
            '--codesign-identity', '-',
        ])
        
        # 修改 pydantic 相关的导入配置
        for module in ['PyQt5', 'sqlite3', 'zhipuai', 'json', 'asyncio']:
            command.extend(['--hidden-import', module])
            
        # 为 Pydantic V2 添加必要的隐式导入
        pydantic_imports = [
            'pydantic.json_schema',
            'pydantic.networks',
            'pydantic.types',
            'pydantic.validators',
            'pydantic.fields'
        ]
        for module in pydantic_imports:
            command.extend(['--hidden-import', module])
            
        # 执行打包命令
        subprocess.run(command, check=True)
        
        # 将生成的可执行文件复制到当前目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_name = f'DailyPlanner_{timestamp}'
        shutil.copy2(os.path.join('dist', 'DailyPlanner'), output_name)
        
        print(f"\n构建完成！")
        print(f"可执行文件位置: {output_name}")
        
        return True
        
    except Exception as e:
        print(f"构建失败: {str(e)}")
        return False

if __name__ == '__main__':
    print("开始构建应用程序...")
    
    # 清理旧的构建文件
    clean_up()
    
    # 构建应用
    if build_app():
        print("""
构建成功！可执行文件已生成在当前目录。

注意事项：
1. 如果系统提示"无法打开"，请在系统偏好设置的安全性与隐私中允许打开
2. 建议在发布前测试打包后的程序是否正常运行
""")
    else:
        print("构建失败，请检查错误信息。")
    
    # 清理构建文件
    clean_up() 