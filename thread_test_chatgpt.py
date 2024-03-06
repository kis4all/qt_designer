import sys
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton
import time

class Worker(QObject):
    finished = Signal()
    progress = Signal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        for i in range(1, 11):
            time.sleep(1)  # Simulate time-consuming task
            self.progress.emit(i * 10)
        self.finished.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle('Thread Communication Example')
        layout = QVBoxLayout()

        self.label = QLabel('Progress: 0%', self)
        layout.addWidget(self.label)

        self.start_button = QPushButton('Start Task', self)
        self.start_button.clicked.connect(self.start_task)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_task(self):
        self.worker_thread = QThread()
        self.worker = Worker()

        # Move the worker object to the thread
        self.worker.moveToThread(self.worker_thread)

        # Connect signals and slots
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.progress.connect(self.update_progress)

        # Start the thread
        self.worker_thread.start()

    def update_progress(self, value):
        self.label.setText(f'Progress: {value}%')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
