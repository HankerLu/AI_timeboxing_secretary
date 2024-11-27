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
        ]
        
        # 如果有图标文件，添加图标
        if os.path.exists('app_icon.icns'):
            command.extend(['--icon', 'app_icon.icns'])
        
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
        
        # 创建发布包
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        release_name = f'DailyPlanner_release_{timestamp}'
        release_path = os.path.join('dist', release_name)
        
        # 创建发布目录
        os.makedirs(release_path, exist_ok=True)
        
        # 复制文件到发布目录
        shutil.copy2(os.path.join('dist', 'DailyPlanner'), release_path)
        if os.path.exists('commands.db'):
            shutil.copy2('commands.db', release_path)
        
        # 创建说明文件
        with open(os.path.join(release_path, 'README.txt'), 'w', encoding='utf-8') as f:
            f.write('''每日计划管理器

使用说明：
1. 运行 DailyPlanner 启动程序
2. 在输入区域输入任务描述
3. 点击"AI解析输入"按钮生成计划
4. 程序会自动保存任务和输入内容

注意事项：
- 首次运行时会自动创建数据库文件
- 请勿删除程序目录下的 commands.db 文件
- 如遇到问题，请确保程序所在目录具有写入权限
- 如果提示"无法打开"，请在系统偏好设置中允许来自任何来源的应用

版本：1.0
发布日期：''' + datetime.now().strftime('%Y-%m-%d'))
        
        # 创建压缩包
        shutil.make_archive(release_path, 'zip', release_path)
        
        print(f"\n构建完成！")
        print(f"发布包位置: {release_path}.zip")
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
构建成功！请检查 dist 目录下的发布包。

发布包包含：
- DailyPlanner (主程序)
- commands.db (数据库文件)
- README.txt (使用说明)

注意事项：
1. 如果系统提示"无法打开"，请在系统偏好设置的安全性与隐私中允许打开
2. 建议在发布前测试打包后的程序是否正常运行
""")
    else:
        print("构建失败，请检查错误信息。")
    
    # 清理构建文件
    clean_up() 