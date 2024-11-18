import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                           QLabel, QHeaderView)
from PyQt5.QtCore import QTimer, Qt

class DailyPlanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("每日计划管理器")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建任务输入区
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("请输入任务，格式：\n任务1 30min\n任务2 45min\n...")
        layout.addWidget(QLabel("任务输入区域："))
        layout.addWidget(self.task_input)
        
        # 创建生成计划按钮
        self.generate_btn = QPushButton("生成计划")
        self.generate_btn.clicked.connect(self.generate_schedule)
        layout.addWidget(self.generate_btn)
        
        # 创建计划表格
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(3)
        self.schedule_table.setHorizontalHeaderLabels(["开始时间", "结束时间", "任务"])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("今日计划："))
        layout.addWidget(self.schedule_table)
        
        # 创建当前任务显示
        self.current_task_label = QLabel("当前任务：无")
        self.time_remaining_label = QLabel("剩余时间：00:00")
        layout.addWidget(self.current_task_label)
        layout.addWidget(self.time_remaining_label)
        
        # 初始化计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.current_task_end_time = None
        
    def generate_schedule(self):
        # 清空现有表格
        self.schedule_table.setRowCount(0)
        
        # 解析输入文本
        tasks = []
        for line in self.task_input.toPlainText().strip().split('\n'):
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
            
            self.schedule_table.insertRow(row)
            self.schedule_table.setItem(row, 0, QTableWidgetItem(current_time.strftime("%H:%M")))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(end_time.strftime("%H:%M")))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(task_name))
            
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DailyPlanner()
    window.show()
    sys.exit(app.exec_()) 