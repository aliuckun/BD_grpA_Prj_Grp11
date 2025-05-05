# gui/loading_screen.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer

class LoadingScreen(QWidget):
    def __init__(self, on_loaded_callback):
        super().__init__()
        self.setWindowTitle("Simülasyon Başlatılıyor...")
        self.setGeometry(400, 200, 400, 200)

        self.on_loaded_callback = on_loaded_callback
        self.progress = 0

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.label = QLabel("🔄 Simülasyon Başlatılıyor...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(30)  # Hızlı yükleme efekti

    def update_progress(self):
        self.progress += 2
        self.progress_bar.setValue(self.progress)

        if self.progress >= 100:
            self.timer.stop()
            self.close()
            self.on_loaded_callback()
