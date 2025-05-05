import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QStackedWidget
from PyQt5.QtCore import QThread

from log_viewer import LogViewer
from error_viewer import ErrorLogViewer
from message_viewer import MessageViewer

import asyncio
from central_system import main as central_main

class CentralSystemThread(QThread):
    def run(self):
        try:
            asyncio.run(central_main())
        except Exception as e:
            print(f"[THREAD ERROR] {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔌 OCPP Central System UI")
        self.setGeometry(100, 100, 600, 400)

        self.stack = QStackedWidget()
        self.main_menu = QWidget()

        self.log_viewer = LogViewer(self)
        self.error_viewer = ErrorLogViewer(self)
        self.message_viewer = MessageViewer(self)

        layout = QVBoxLayout()
        for label, widget in [("📄 Log Kayıtları", self.log_viewer), ("🛑 Hata Kayıtları", self.error_viewer), ("📡 Canlı Mesajlar", self.message_viewer)]:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    background-color: #007acc;
                    color: white;
                    border-radius: 8px;
                    padding: 10px;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #005b9a;
                }
            """)
            btn.clicked.connect(lambda _, w=widget: self.stack.setCurrentWidget(w))
            layout.addWidget(btn)

        self.main_menu.setLayout(layout)

        self.stack.addWidget(self.main_menu)
        self.stack.addWidget(self.log_viewer)
        self.stack.addWidget(self.error_viewer)
        self.stack.addWidget(self.message_viewer)

        self.setCentralWidget(self.stack)

        self.central_thread = CentralSystemThread()
        self.central_thread.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())