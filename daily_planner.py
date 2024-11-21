import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                           QLabel, QHeaderView, QHBoxLayout, QStackedWidget)
from PyQt5.QtCore import QTimer, Qt
from zhipuai import ZhipuAI
import json
import asyncio
import sqlite3
from typing import Dict, List, Any

class GUIManager:
    """GUI界面管理器"""
    def __init__(self, parent):
        self.parent = parent
        self.widgets = {}
        self.layouts = {}
        self.current_view = None
        
        # 初始化堆叠窗口部件
        self.stack = QStackedWidget()
        
    def create_widget(self, widget_id, widget_type, **kwargs):
        """创建并存储部件"""
        widget = widget_type(**kwargs)
        self.widgets[widget_id] = widget
        return widget
        
    def create_layout(self, layout_id, layout_type):
        """创建并存储布局"""
        layout = layout_type()
        self.layouts[layout_id] = layout
        return layout
        
    def get_widget(self, widget_id):
        """获取部件"""
        return self.widgets.get(widget_id)
        
    def get_layout(self, layout_id):
        """获取布局"""
        return self.layouts.get(layout_id)
        
    def set_widget_visibility(self, widget_id, visible):
        """设置部件可见性"""
        widget = self.get_widget(widget_id)
        if widget:
            widget.setVisible(visible)
            
    def set_widget_enabled(self, widget_id, enabled):
        """设置部件启用状态"""
        widget = self.get_widget(widget_id)
        if widget:
            widget.setEnabled(enabled)

class CommandDatabase:
    """指令集数据库管理器"""
    def __init__(self):
        self.conn = sqlite3.connect('commands.db')
        self.cursor = self.conn.cursor()
        self.init_database()
        
    def init_database(self):
        """初始化数据库表"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS gui_commands (
            id INTEGER PRIMARY KEY,
            command_type TEXT NOT NULL,
            command_name TEXT NOT NULL,
            parameters TEXT,
            description TEXT,
            example TEXT
        )
        ''')
        
        # 预设指令集
        default_commands = [
            ('create_task', '创建任务', '{"task_name": "str", "duration": "int", "start_time": "str?"}', 
             '创建一个新的任务', '创建一个写代码任务，持续60分钟'),
            ('modify_task', '修改任务', '{"task_name": "str", "duration": "int?", "start_time": "str?"}',
             '修改现有任务的属性', '将写代码任务的时间改为90分钟'),
            ('delete_task', '删除任务', '{"task_name": "str"}',
             '删除指定的任务', '删除写代码任务'),
            ('clear_tasks', '清空任务', '{}',
             '清空所有任务', '清空所有任务'),
            ('start_timer', '开始计时', '{"task_name": "str?"}',
             '开始任务计时', '开始当前任务的计时'),
            ('pause_timer', '暂停计时', '{}',
             '暂停当前任务的计时', '暂停计时'),
            ('show_view', '切换视图', '{"view_name": "str"}',
             '切换到指定的界面视图', '切换到任务列表视图')
        ]
        
        self.cursor.executemany('''
        INSERT OR IGNORE INTO gui_commands 
        (command_type, command_name, parameters, description, example)
        VALUES (?, ?, ?, ?, ?)
        ''', default_commands)
        
        self.conn.commit()
    
    def get_command_info(self, command_type: str) -> Dict[str, Any]:
        """获取指令信息"""
        self.cursor.execute('''
        SELECT command_type, command_name, parameters, description, example
        FROM gui_commands
        WHERE command_type = ?
        ''', (command_type,))
        
        result = self.cursor.fetchone()
        if result:
            return {
                'type': result[0],
                'name': result[1],
                'parameters': json.loads(result[2]),
                'description': result[3],
                'example': result[4]
            }
        return None
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """获取所有指令信息"""
        self.cursor.execute('SELECT * FROM gui_commands')
        results = self.cursor.fetchall()
        return [{
            'type': r[1],
            'name': r[2],
            'parameters': json.loads(r[3]),
            'description': r[4],
            'example': r[5]
        } for r in results]
    
    def validate_command(self, command: Dict[str, Any]) -> bool:
        """验证指令格式是否正确"""
        cmd_info = self.get_command_info(command.get('type'))
        if not cmd_info:
            return False
            
        required_params = {k for k, v in cmd_info['parameters'].items() 
                         if not v.endswith('?')}
        actual_params = set(command.get('params', {}).keys())
        
        return required_params.issubset(actual_params)
    
    def get_prompt_template(self) -> str:
        """生成用于智谱AI的prompt模板"""
        commands = self.get_all_commands()
        prompt = """你是一个任务规划助手。请将用户输入的自然语言描述转换为标准的任务指令。
可用的指令集如下：

"""
        for cmd in commands:
            prompt += f"- {cmd['name']}({cmd['type']}):\n"
            prompt += f"  描述: {cmd['description']}\n"
            prompt += f"  参数: {cmd['parameters']}\n"
            prompt += f"  示例: {cmd['example']}\n\n"
        
        prompt += """
请将用户输入转换为以下JSON格式：
{
    "commands": [
        {
            "type": "指令类型",
            "params": {
                "参数名": "参数值"
            }
        }
    ]
}

注意：
1. 时间参数必须转换为标准格式（HH:MM或分钟数）
2. 指令类型必须是上述列表中的其中之一
3. 参数必须符合指令的要求
"""
        return prompt

class CommandParser:
    """指令解析器"""
    def __init__(self, planner):
        self.planner = planner
        self.db = CommandDatabase()
        self.commands = {
            'create_task': self.create_task,
            'add_time': self.add_time,
            'clear_tasks': self.clear_tasks,
            'start_now': self.start_now,
            'modify_task': self.modify_task,
            'delete_task': self.delete_task
        }
        
    async def parse_natural_language(self, text):
        """解析自然语言输入为指令"""
        try:
            prompt_template = self.db.get_prompt_template() + """
当用户没有明确指定时间时，请按照以下规则处理：
1. 如果没有指定开始时间，默认从当前时间开始
2. 如果没有指定持续时间，根据任务类型估算：
   - 短会议/休息: 15-30分钟
   - 一般任务: 45-60分钟
   - 复杂任务: 90-120分钟
3. 总是返回完整的JSON格式响应

示例响应：
{
    "commands": [
        {
            "type": "create_task",
            "params": {
                "task_name": "写报告",
                "duration": 60,
                "start_time": "14:30"
            }
        }
    ]
}
"""
            
            current_time = datetime.now()
            
            response = self.planner.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": f"当前时间是{current_time.strftime('%H:%M')}，请解析以下任务描述：\n{text}"}
                ]
            )
            
            response_text = response.choices[0].message.content
            print(f"AI响应: {response_text}")
            
            # 提取JSON部分
            try:
                # 尝试直接解析
                parsed_commands = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果失败，尝试提取JSON部分
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    parsed_commands = json.loads(json_match.group())
                else:
                    raise ValueError("无法从响应中提取有效的JSON")
            
            # 验证每个指令
            valid_commands = []
            for cmd in parsed_commands.get('commands', []):
                if self.db.validate_command(cmd):
                    valid_commands.append(cmd)
                else:
                    print(f"无效指令: {cmd}")
                    
            return valid_commands if valid_commands else [{"type": "error", "params": {"message": "未能生成有效的任务指令"}}]
            
        except Exception as e:
            print(f"解析错误: {str(e)}")
            print(f"原始响应: {response_text if 'response_text' in locals() else 'None'}")
            return [{"type": "error", "params": {"message": f"解析失败：{str(e)}"}}]
    
    def execute_commands(self, commands):
        """执行指令列表"""
        results = []
        current_time = datetime.now()
        
        for cmd in commands:
            try:
                cmd_type = cmd.get('type')
                if cmd_type == 'error':
                    results.append(cmd['params'])
                    continue
                    
                if cmd_type in self.commands:
                    params = cmd.get('params', {})
                    print(f"执行命令: {cmd_type}, 参数: {params}")  # 调试输出
                    
                    # 处理缺失的参数
                    if cmd_type == 'create_task':
                        if 'duration' not in params:
                            # 默认设置为60分钟
                            params['duration'] = 60
                        
                        if 'start_time' not in params:
                            # 如果没有指定开始时间，使用当前时间
                            params['start_time'] = current_time
                        else:
                            # 处理start_time
                            try:
                                time_str = params['start_time']
                                time_obj = datetime.strptime(time_str, "%H:%M").time()
                                params['start_time'] = datetime.combine(current_time.date(), time_obj)
                            except Exception as e:
                                print(f"时间转换错误: {str(e)}")
                                params['start_time'] = current_time
                            
                    result = self.commands[cmd_type](**params)
                    results.append(result)
            except Exception as e:
                print(f"命令执行错误: {str(e)}")
                results.append({"status": "error", "message": f"执行失败：{str(e)}"})
                
        return results
    
    def create_task(self, task_name, duration, start_time=None, priority=None):
        """创建任务"""
        task = {
            'name': task_name,
            'duration': duration,
            'start_time': start_time,
            'priority': priority
        }
        return self.planner.add_task(task)
    
    def add_time(self, task_name, duration):
        """添加时间到现有任务"""
        return self.planner.modify_task_duration(task_name, duration)
    
    def clear_tasks(self):
        """清空任务列表"""
        return self.planner.clear_all_tasks()
    
    def start_now(self):
        """立即开始当前任务列表"""
        return self.planner.start_schedule()
    
    def modify_task(self, task_name, **modifications):
        """修改任务属性"""
        return self.planner.modify_task(task_name, modifications)
    
    def delete_task(self, task_name):
        """删除任务"""
        return self.planner.delete_task(task_name)

class DailyPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gui = GUIManager(self)
        self.command_db = CommandDatabase()  # 初始化指令数据库
        self.command_parser = CommandParser(self)
        self.tasks = []  # 存储任务列表
        
        self.setup_ui()
        self.setup_connections()
        
        # 初始化智谱AI客户端
        self.client = ZhipuAI(api_key="e64b996267bee6ba0252a5d46a143ff4.3RZ8v4qZ2DbYoJbk")
        
        # 初始化计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.current_task_end_time = None

    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("每日计划管理器")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = self.gui.create_layout('main', QVBoxLayout)
        central_widget.setLayout(main_layout)
        
        # 创建任务输入区
        self.setup_input_area(main_layout)
        
        # 创建按钮区
        self.setup_button_area(main_layout)
        
        # 创建计划表格
        self.setup_schedule_table(main_layout)
        
        # 创建状态显示区
        self.setup_status_area(main_layout)

    def setup_input_area(self, parent_layout):
        """设置输入区域"""
        input_label = self.gui.create_widget('input_label', QLabel, text="任务输入区域：")
        task_input = self.gui.create_widget('task_input', QTextEdit)
        task_input.setPlaceholderText("请输入任务，格式：\n任务1 30min\n任务2 45min\n...")
        
        parent_layout.addWidget(input_label)
        parent_layout.addWidget(task_input)

    def setup_button_area(self, parent_layout):
        """设置按钮区域"""
        button_layout = self.gui.create_layout('button', QHBoxLayout)
        
        generate_btn = self.gui.create_widget('generate_btn', QPushButton, text="生成计划")
        ai_parse_btn = self.gui.create_widget('ai_parse_btn', QPushButton, text="AI解析输入")
        
        button_layout.addWidget(generate_btn)
        button_layout.addWidget(ai_parse_btn)
        parent_layout.addLayout(button_layout)

    def setup_schedule_table(self, parent_layout):
        """设置计划表格"""
        table_label = self.gui.create_widget('table_label', QLabel, text="今日计划：")
        schedule_table = self.gui.create_widget('schedule_table', QTableWidget)
        schedule_table.setColumnCount(3)
        schedule_table.setHorizontalHeaderLabels(["开始时间", "结束时间", "任务"])
        schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        parent_layout.addWidget(table_label)
        parent_layout.addWidget(schedule_table)

    def setup_status_area(self, parent_layout):
        """设置状态显示区域"""
        current_task_label = self.gui.create_widget('current_task', QLabel, text="当前任务：无")
        time_remaining_label = self.gui.create_widget('time_remaining', QLabel, text="剩余时间：00:00")
        
        parent_layout.addWidget(current_task_label)
        parent_layout.addWidget(time_remaining_label)

    def setup_connections(self):
        """设置信号连接"""
        self.gui.get_widget('generate_btn').clicked.connect(self.generate_schedule)
        self.gui.get_widget('ai_parse_btn').clicked.connect(self.parse_with_ai)

    def show_view(self, view_name):
        """切换显示视图"""
        views = {
            'input': ['input_label', 'task_input', 'generate_btn', 'ai_parse_btn'],
            'schedule': ['table_label', 'schedule_table', 'current_task', 'time_remaining'],
        }
        
        for widget_id in self.gui.widgets:
            self.gui.set_widget_visibility(widget_id, widget_id in views.get(view_name, []))

    def generate_schedule(self):
        """生成计划表"""
        schedule_table = self.gui.get_widget('schedule_table')
        task_input = self.gui.get_widget('task_input')
        
        # 清空现有表格
        schedule_table.setRowCount(0)
        
        # 解析输入文本
        tasks = []
        for line in task_input.toPlainText().strip().split('\n'):
            if not line.strip():
                continue
            task_parts = line.strip().split()
            if len(task_parts) >= 2:
                task_name = ' '.join(task_parts[:-1])
                duration_str = task_parts[-1].lower()
                
                # 解析时间
                if 'min' in duration_str:
                    duration = int(duration_str.replace('min', ''))
                elif 'h' in duration_str:
                    duration = int(duration_str.replace('h', '')) * 60
                else:
                    continue
                
                tasks.append((task_name, duration))
        
        # 生成时间表
        current_time = datetime.now().replace(second=0, microsecond=0)
        row = 0
        
        for task_name, duration in tasks:
            end_time = current_time + timedelta(minutes=duration)
            
            schedule_table.insertRow(row)
            schedule_table.setItem(row, 0, QTableWidgetItem(current_time.strftime("%H:%M")))
            schedule_table.setItem(row, 1, QTableWidgetItem(end_time.strftime("%H:%M")))
            schedule_table.setItem(row, 2, QTableWidgetItem(task_name))
            
            current_time = end_time
            row += 1
        
        # 开始计时
        self.start_timer()

    def start_timer(self):
        """启动计时器"""
        schedule_table = self.gui.get_widget('schedule_table')
        if schedule_table.rowCount() > 0:
            current_time = datetime.now()
            
            # 找到当前应该执行的任务
            for row in range(schedule_table.rowCount()):
                start_time = datetime.strptime(schedule_table.item(row, 0).text(), "%H:%M").replace(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day
                )
                end_time = datetime.strptime(schedule_table.item(row, 1).text(), "%H:%M").replace(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day
                )
                
                if start_time <= current_time <= end_time:
                    self.current_task_end_time = end_time
                    current_task = self.gui.get_widget('current_task')
                    time_remaining = self.gui.get_widget('time_remaining')
                    
                    current_task.setText(f"当前任务：{schedule_table.item(row, 2).text()}")
                    self.timer.start(1000)  # 每秒更新一次
                    break
    
    def update_timer(self):
        if self.current_task_end_time:
            remaining = self.current_task_end_time - datetime.now()
            if remaining.total_seconds() > 0:
                minutes = int(remaining.total_seconds() // 60)
                seconds = int(remaining.total_seconds() % 60)
                self.time_remaining_label.setText(f"剩余时间：{minutes:02d}:{seconds:02d}")
            else:
                self.timer.stop()
                self.current_task_label.setText("当前任务：已完成")
                self.time_remaining_label.setText("剩余时间：00:00")
                self.current_task_end_time = None
                # 自动开始下一个任务
                self.start_timer()
    
    def parse_with_ai(self):
        """处理AI解析按钮点击事件"""
        user_input = self.gui.get_widget('task_input').toPlainText()
        if not user_input.strip():
            return
        
        try:
            print(f"处理用户输入: {user_input}")  # 调试输出
            
            # 清空现有任务
            self.clear_all_tasks()
            
            # 处理自然语言输入
            results = asyncio.run(self.process_natural_language(user_input))
            print(f"处理结果: {results}")  # 调试输出
            
            # 显示处理结果
            result_messages = []
            for result in results:
                if isinstance(result, dict):
                    message = result.get('message', str(result))
                    result_messages.append(message)
            
            if result_messages:
                # 保持原始输入，添加处理结果
                original_input = user_input
                result_text = "\n\n处理结果：\n" + "\n".join(result_messages)
                self.gui.get_widget('task_input').setText(original_input + result_text)
                
                # 更新显示并启动计时器
                self._update_schedule_display()
                self.start_timer()
            else:
                self.gui.get_widget('task_input').setText(user_input + "\n\n解析失败：未能生成有效的任务")
            
        except Exception as e:
            print(f"AI解析错误: {str(e)}")
            self.gui.get_widget('task_input').setText(user_input + f"\n\n处理失败：{str(e)}")

    def update_task_status(self, task_name, remaining_time):
        """更新任务状态显示"""
        self.gui.get_widget('current_task').setText(f"当前任务：{task_name}")
        self.gui.get_widget('time_remaining').setText(f"剩余时间：{remaining_time}")

    def add_task(self, task):
        """添加任务到列表"""
        self.tasks.append(task)
        self._update_schedule_display()
        return {"status": "success", "message": f"已添加任务：{task['name']}"}
    
    def modify_task_duration(self, task_name, duration):
        """修改任务时长"""
        for task in self.tasks:
            if task['name'] == task_name:
                task['duration'] = duration
                self._update_schedule_display()
                return {"status": "success", "message": f"已修改任务时长：{task_name}"}
        return {"status": "error", "message": f"未找到任务：{task_name}"}
    
    def clear_all_tasks(self):
        """清空所有任务"""
        self.tasks = []
        self._update_schedule_display()
        return {"status": "success", "message": "已清空所有任务"}
    
    def modify_task(self, task_name, modifications):
        """修改任务属性"""
        for task in self.tasks:
            if task['name'] == task_name:
                task.update(modifications)
                self._update_schedule_display()
                return {"status": "success", "message": f"已修改任务：{task_name}"}
        return {"status": "error", "message": f"未找到任务：{task_name}"}
    
    def delete_task(self, task_name):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task['name'] == task_name:
                self.tasks.pop(i)
                self._update_schedule_display()
                return {"status": "success", "message": f"已删除任务：{task_name}"}
        return {"status": "error", "message": f"未找到任务：{task_name}"}
    
    def _update_schedule_display(self):
        """更新界面显示"""
        schedule_table = self.gui.get_widget('schedule_table')
        schedule_table.setRowCount(0)
        
        current_time = datetime.now().replace(second=0, microsecond=0)
        
        for task in self.tasks:
            row = schedule_table.rowCount()
            schedule_table.insertRow(row)
            
            start_time = task.get('start_time', current_time)
            end_time = start_time + timedelta(minutes=task['duration'])
            
            schedule_table.setItem(row, 0, QTableWidgetItem(start_time.strftime("%H:%M")))
            schedule_table.setItem(row, 1, QTableWidgetItem(end_time.strftime("%H:%M")))
            schedule_table.setItem(row, 2, QTableWidgetItem(task['name']))
            
            current_time = end_time
    
    async def process_natural_language(self, text):
        """处理自然语言输入"""
        commands = await self.command_parser.parse_natural_language(text)
        results = self.command_parser.execute_commands(commands)
        return results

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DailyPlanner()
    window.show()
    sys.exit(app.exec_()) 