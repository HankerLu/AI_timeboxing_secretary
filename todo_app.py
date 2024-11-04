import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QSpinBox, QComboBox, 
                           QPushButton, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt
from datetime import datetime, timedelta

class TodoItem:
    def __init__(self, description, duration, priority):
        self.description = description
        self.duration = duration  # 以分钟为单位
        self.priority = priority
        self.scheduled_time = None

class TodoListApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.todo_items = []
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('每日待办事项')
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建输入区域
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        
        # 描述输入
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText('输入待办事项描述')
        input_layout.addWidget(self.description_input)
        
        # 时间预算输入
        self.duration_input = QSpinBox()
        self.duration_input.setRange(5, 480)  # 5分钟到8小时
        self.duration_input.setSuffix(' 分钟')
        input_layout.addWidget(self.duration_input)
        
        # 优先级选择
        self.priority_input = QComboBox()
        self.priority_input.addItems(['高', '中', '低'])
        input_layout.addWidget(self.priority_input)
        
        # 添加按钮
        add_button = QPushButton('添加')
        add_button.clicked.connect(self.add_todo_item)
        input_layout.addWidget(add_button)
        
        layout.addWidget(input_widget)
        
        # 创建显示表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['计划时间', '描述', '时长', '优先级'])
        layout.addWidget(self.table)
        
        # 生成计划按钮
        schedule_button = QPushButton('生成时间安排')
        schedule_button.clicked.connect(self.generate_schedule)
        layout.addWidget(schedule_button)

    def add_todo_item(self):
        description = self.description_input.text()
        duration = self.duration_input.value()
        priority = self.priority_input.currentText()
        
        if description:
            todo_item = TodoItem(description, duration, priority)
            self.todo_items.append(todo_item)
            self.description_input.clear()
            self.duration_input.setValue(5)
            self.update_table()

    def generate_schedule(self):
        # 按优先级排序
        priority_map = {'高': 3, '中': 2, '低': 1}
        self.todo_items.sort(key=lambda x: priority_map[x.priority], reverse=True)
        
        # 从当前时间开始安排
        current_time = datetime.now().replace(minute=(datetime.now().minute // 5) * 5, second=0, microsecond=0)
        
        for item in self.todo_items:
            item.scheduled_time = current_time
            current_time += timedelta(minutes=item.duration)
        
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.todo_items))
        
        for row, item in enumerate(self.todo_items):
            # 时间列
            time_str = item.scheduled_time.strftime('%H:%M') if item.scheduled_time else '未安排'
            self.table.setItem(row, 0, QTableWidgetItem(time_str))
            
            # 描述列
            self.table.setItem(row, 1, QTableWidgetItem(item.description))
            
            # 时长列
            self.table.setItem(row, 2, QTableWidgetItem(f'{item.duration}分钟'))
            
            # 优先级列
            self.table.setItem(row, 3, QTableWidgetItem(item.priority))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    todo_app = TodoListApp()
    todo_app.show()
    sys.exit(app.exec_()) 