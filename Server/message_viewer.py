from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from shared_signals import log_signal

class MessageViewer(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout()
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("font-size: 14px; background-color: #fff; padding: 8px;")

        layout.addWidget(self.text_area)

        if self.main_window:
            back_btn = QPushButton("🔙 Ana Menüye Dön")
            back_btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    background-color: #007acc;
                    color: white;
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #005b9a;
                }
            """)
            back_btn.clicked.connect(lambda: self.main_window.stack.setCurrentWidget(self.main_window.main_menu))
            layout.addWidget(back_btn)

        self.setLayout(layout)
        log_signal.new_log.connect(self.display_message)

    def display_message(self, message):
        print("📥 GUI mesaj alındı:", message)
        self.text_area.append(message)
