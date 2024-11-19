import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                           QLabel, QHeaderView, QHBoxLayout, QStackedWidget)
from PyQt5.QtCore import QTimer, Qt
from zhipuai import ZhipuAI

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

class DailyPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gui = GUIManager(self)
        self.setup_ui()
        self.setup_connections()
        
        # 初始化智谱AI客户端
        self.client = ZhipuAI(api_key="your_api_key_here")
        
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
        if self.schedule_table.rowCount() > 0:
            current_time = datetime.now()
            
            # 找到当前应该执行的任务
            for row in range(self.schedule_table.rowCount()):
                start_time = datetime.strptime(self.schedule_table.item(row, 0).text(), "%H:%M").replace(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day
                )
                end_time = datetime.strptime(self.schedule_table.item(row, 1).text(), "%H:%M").replace(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day
                )
                
                if start_time <= current_time <= end_time:
                    self.current_task_end_time = end_time
                    self.current_task_label.setText(f"当前任务：{self.schedule_table.item(row, 2).text()}")
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
        """使用智谱AI解析用户输入的自然语言描述"""
        user_input = self.task_input.toPlainText()
        if not user_input.strip():
            return
            
        prompt = """请将以下自然语言描述转换为标准的任务时间格式。
输出格式要求：每行一个任务，格式为"任务名称 时间"
时间使用min或h为单位。例如：
写代码 30min
开会 1h

用户输入："""
        
        try:
            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": "你是一个任务规划助手，帮助用户将自然语言转换为标准的任务时间格式。"},
                    {"role": "user", "content": prompt + user_input}
                ]
            )
            
            parsed_text = response.choices[0].message.content
            self.task_input.setText(parsed_text)
            
        except Exception as e:
            self.task_input.setText(f"AI解析失败：{str(e)}")

    def update_task_status(self, task_name, remaining_time):
        """更新任务状态显示"""
        self.gui.get_widget('current_task').setText(f"当前任务：{task_name}")
        self.gui.get_widget('time_remaining').setText(f"剩余时间：{remaining_time}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DailyPlanner()
    window.show()
    sys.exit(app.exec_()) 