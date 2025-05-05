import psycopg2
import json
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QHeaderView, QPushButton
from PyQt5.QtCore import Qt

DB_CONFIG = {
    "dbname": "ocpp_db",
    "user": "postgres",
    "password": "Sekeroptik.123",
    "host": "localhost",
    "port": 5432
}

class LogViewer(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window

        self.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; margin: 10px 0; }")

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Charge Point ID", "Action", "Payload", "Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
                alternate-background-color: #f9f9f9;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #2e86de;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("📄 Veritabanı Logları"))
        layout.addWidget(self.table)

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
        self.load_logs()

    def load_logs(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT id, charge_point_id, action, payload, timestamp FROM ocpp_logs ORDER BY id DESC")
            rows = cur.fetchall()

            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    if isinstance(value, dict):
                        value = json.dumps(value, indent=2)
                    elif isinstance(value, str) and value.startswith("{"):
                        try:
                            value = json.dumps(json.loads(value), indent=2)
                        except:
                            pass
                    item = QTableWidgetItem(str(value))
                    item.setFlags(Qt.ItemIsEnabled)
                    self.table.setItem(row_idx, col_idx, item)

            cur.close()
            conn.close()
        except Exception as e:
            print(f"[HATA] Veritabanı logları yüklenemedi: {e}")