import sys
from PyQt5.QtCore import Qt, QTimer
from decimal import Decimal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QComboBox, QHBoxLayout, QProgressBar, QFrame
)
from simulation.simulator import Simulator
from database.connection import DatabaseManager
from gui.loading_screen import LoadingScreen
from datetime import datetime
from iso15118.messages.service_discovery import generate_service_discovery_req
from iso15118.utils.xml_validator import validate_xml
from iso15118.messages.service_discovery_res import generate_service_discovery_res
from charge_point.charge_point import SmartChargePoint
import asyncio
from websockets import connect



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ISO 15118 + OCPP Elektrikli Araç Simülasyonu")
        self.setGeometry(300, 100, 800, 720)
        self.charge_point = None  # Yeni eklenen satır
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.setup_charge_point())  # Yeni eklenen satır

        # --- Simülasyon ve DB ayarları ---
        self.simulator = Simulator()
        self.db = DatabaseManager(
            db_name="ev_charging_simulation",
            user="postgres",
            password="Sekeroptik.123",
            host="localhost",
            port="5432"
        )

        self.session_id = None
        self.selected_vehicle_id = None
        self.error_rules = self.simulator.get_error_rules()
        self.error_types = list(self.error_rules.keys())

        # --- Ana görünüm düzeni ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)

        # Araç Seçimi (Güncellenmiş)
        selection_layout = QHBoxLayout()
        selection_layout.setContentsMargins(10, 5, 10, 5)  # Kenar boşluklarını azalt
        selection_layout.setSpacing(8)  # Label ve dropdown arasındaki boşluk

        label = QLabel("🚘 Araç Seç:")
        label.setStyleSheet("font-size: 15px; font-weight: bold;")
        selection_layout.addWidget(label)

        self.vehicle_selector = QComboBox()
        self.vehicle_selector.setFixedWidth(180)  # Genişliği sınırla
        self.vehicle_selector.setStyleSheet("font-size: 14px; padding: 4px;")
        selection_layout.addWidget(self.vehicle_selector)
        self.layout.addLayout(selection_layout)

        self.load_vehicles()
        selection_layout.addStretch()

        # Batarya göstergesi
        self.battery_outer = QFrame()
        self.battery_outer.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 6px; background-color: #fefefe; }")
        self.battery_outer.setFixedHeight(35)

        battery_inner = QHBoxLayout(self.battery_outer)
        battery_inner.setContentsMargins(6, 4, 6, 4)
        battery_inner.setSpacing(8)

        self.battery_frame = QFrame()
        self.battery_frame.setFixedSize(60, 25)
        self.battery_frame.setStyleSheet("background-color: white; border: 1px solid #aaa; border-radius: 4px;")

        self.battery_level = QFrame(self.battery_frame)
        self.battery_level.setGeometry(0, 0, int(60 * 0.2), 25)
        self.battery_level.setStyleSheet("background-color: #ffcc00; border-radius: 2px;")

        self.battery_label = QLabel("🔋 %20")
        self.battery_label.setStyleSheet("font-size: 15px; font-weight: bold;")

        battery_inner.addWidget(self.battery_frame)
        battery_inner.addWidget(self.battery_label)

        selection_layout.addWidget(self.battery_outer)
        self.layout.addLayout(selection_layout)
        self.battery_outer.setVisible(False)

        self.vehicle_icon = QLabel("🚙")
        self.vehicle_icon.setAlignment(Qt.AlignCenter)
        self.vehicle_icon.setStyleSheet("font-size: 48px;")
        self.layout.addWidget(self.vehicle_icon)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        self.layout.addWidget(self.status_label)

        self.charge_progress = QProgressBar()
        self.charge_progress.setMinimum(0)
        self.charge_progress.setMaximum(100)
        self.charge_progress.setValue(20)
        self.charge_progress.setTextVisible(True)
        self.charge_progress.setStyleSheet("""
        QProgressBar {
            border: 1px solid #ccc;
            border-radius: 6px;
            height: 35px;
            font-weight: bold;
            font-size: 16px;
            background-color: #f0f0f0;
            text-align: center;
        }
        QProgressBar::chunk {
            background: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 #00ff00, stop:1 #006400
            );
            border-radius: 5px;
        }
        """)

        self.charge_status = QLabel("")
        self.charge_status.setStyleSheet("font-size: 15px; margin-bottom: 10px;")
        self.layout.addWidget(self.charge_status)
        self.layout.addWidget(self.charge_progress)
        self.charge_progress.setVisible(False)
        self.charge_status.setVisible(False)

        self.charge_timer = QTimer()
        self.charge_timer.timeout.connect(self.update_charge_progress)
        self.charge_level = 20
        self.charge_duration = 30

        # Ödeme işlemi zamanlayıcısı
        self.payment_timer = QTimer()
        self.payment_timer.setSingleShot(True)
        self.payment_timer.timeout.connect(self.complete_payment_process)

        # FSM butonları
        self.add_button("🔌 Aracı Bağla", "connect_vehicle", "#e0f7fa")
        self.add_button("📄 Sertifika Doğrula", "start_cert_check", "#f1f8e9")
        self.add_button("🔐 Kimlik Doğrula", "auth_ok", "#fff3e0")
        self.add_button("⚡ Şarj Başlat", "start_charging", "#fbe9e7")
        self.add_button("💳 Ödeme Onayı", "start_payment", "#ede7f6")
        self.add_button("🔌❌ Bağlantıyı Kes", "disconnect", "#ffcdd2")

        # PDA hataları
        self.error_title = QLabel("🔴 PDA Hata Yığını")
        self.error_title.setStyleSheet("margin-top:20px; font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.error_title)

        self.error_panel = QVBoxLayout()
        self.layout.addLayout(self.error_panel)

        dropdown_layout = QHBoxLayout()
        self.error_dropdown = QComboBox()
        self.error_dropdown.addItems(self.error_types)
        self.error_dropdown.setStyleSheet("font-size: 15px; padding: 4px;")
        dropdown_layout.addWidget(self.error_dropdown)

        add_button = QPushButton("⚠️ Hata Ekle")
        add_button.setStyleSheet("font-size: 15px; background-color: #ffeecc;")
        add_button.clicked.connect(self.add_selected_error)
        dropdown_layout.addWidget(add_button)

        self.layout.addLayout(dropdown_layout)
        self.add_error_button("✅ Hata Çöz", action="resolve")

        self.update_status()
        self.update_error_panel()

    async def setup_charge_point(self):
        try:
            ws_url = "ws://192.168.20.71:9000/CP_1"
            websocket = await connect(ws_url, subprotocols=["ocpp1.6"])
            self.charge_point = SmartChargePoint("CP_1", websocket)
            # Başlatma (gerekiyorsa)
            await self.charge_point.start()
            print("[WebSocket] ChargePoint bağlantısı kuruldu.")
        except Exception as e:
            print(f"[WebSocket HATA] Bağlantı kurulamadı: {e}")

    def load_vehicles(self):
        try:
            result = self.db.execute_and_fetchall("SELECT id, plate FROM vehicles ORDER BY id ASC")
            for vehicle_id, plate in result:
                self.vehicle_selector.addItem(plate, vehicle_id)
            if result:
                self.selected_vehicle_id = result[0][0]  # İlk plakayı varsayılan seç
            self.vehicle_selector.currentIndexChanged.connect(self.on_vehicle_changed)
        except Exception as e:
            print(f"[Veri Tabanı HATA] Araçlar yüklenemedi: {e}")

    def on_vehicle_changed(self, index):
        self.selected_vehicle_id = self.vehicle_selector.itemData(index)

    def log_action(self, action_name):
        if self.selected_vehicle_id is None:
            print("[Uyarı] Hiçbir araç seçilmedi.")
            return

        # ✅ BootNotification gönder
        if self.charge_point:
            print("[DEBUG] BootNotification tetikleniyor")
            self.loop.create_task(self.charge_point.send_boot_notification())
        else:
            print("[DEBUG] charge_point nesnesi hazır değil!")

        # Plaka bilgisi alınır
        selected_plate = self.vehicle_selector.currentText()

        # Veri tabanına logla
        result = self.db.execute_and_fetchone(
            "INSERT INTO charging_sessions (vehicle_id, connector_id, session_status, state_at_start) VALUES (%s, %s, %s, %s) RETURNING id",
            (self.selected_vehicle_id, 1, 'pending', 'Araç Bağlandı')
        )
        if result:
            self.session_id = result[0]
            print(f"[Veritabanı] Oturum başlatıldı: ID = {self.session_id}")
        else:
            print("[Hata] Oturum ID alınamadı.")

    def mark_session_started(self):
        if self.session_id is not None:
            try:
                self.db.execute_query(
                    "UPDATE charging_sessions SET session_status = %s WHERE id = %s",
                    ('started', self.session_id)
                )
                print(f"[Veri Tabanı] Oturum başlatıldı (status='started'): ID = {self.session_id}")
            except Exception as e:
                print(f"[Veri Tabanı HATA] Oturum başlatma başarısız: {e}")
        else:
            print("[Uyarı] session_id tanımlı değil. Şarj oturumu güncellenemez.")

    def mark_session_completed(self):
        global delivered
        print(f"[DEBUG] mark_session_completed çağrıldı – session_id: {self.session_id}")
        if self.session_id is not None:
            try:
                # Araç kapasitesi veri tabanından çekilir
                self.db.cursor.execute(
                    """
                    SELECT v.battery_capacity_kwh, cs.session_status
                    FROM charging_sessions cs
                    JOIN vehicles v ON cs.vehicle_id = v.id
                    WHERE cs.id = %s
                    """,
                    (self.session_id,)
                )
                result = self.db.cursor.fetchone()

                if result:
                    capacity_kwh, status = result
                    if capacity_kwh is None:
                        print("[Uyarı] Batarya kapasitesi boş, varsayılan 50.0 kWh kullanılıyor.")
                        capacity_kwh = Decimal('50.0')

                    # Şarj başlangıcı %20 → kalan %80
                    delivered = capacity_kwh * Decimal('0.80')
                    payment_status = 'paid'

                    self.db.execute_query(
                        """
                        UPDATE charging_sessions
                        SET
                            session_status = %s,
                            end_time = NOW(),
                            energy_delivered_kwh = %s,
                            payment_status = %s
                        WHERE id = %s
                        """,
                        ('completed', delivered, payment_status, self.session_id)
                    )
                    print(f"[Veri Tabanı] Şarj Bilgisi: ID = {self.session_id}, Enerji = {delivered} kWh")
                else:
                    print(f"[Hata] Seans veya batarya bilgisi bulunamadı. ID: {self.session_id}")

            except Exception as e:
                print(f"[Veri Tabanı HATA] Oturum tamamlama başarısız: {e}")
        else:
            print("[Uyarı] session_id tanımlı değil. Güncelleme yapılmadı.")

        self.send_charging_completed(delivered)

    def send_charging_completed(self, energy_kwh):
        if self.selected_vehicle_id is None:
            print("[Uyarı] Araç seçilmedi.")
            return

        # ✅ Stop Transaction gönder
        if self.charge_point:
            print("[DEBUG] Stop Transaction tetikleniyor")
            self.loop.create_task(self.charge_point.stop_transaction())
        else:
            print("[DEBUG] charge_point nesnesi hazır değil!")

        message = {
            "message_type": "StopTransaction",
            "vehicle_id": self.selected_vehicle_id,
            "plate": self.vehicle_selector.currentText(),
            "energy_delivered_kwh": float(round(energy_kwh, 2)),
            "final_charge_level": 100,
            "payment_status": "paid",
            "timestamp": datetime.utcnow().isoformat()
        }

        #send_ocpp_message(message)

    def add_button(self, label, event, bg_color="#ffffff"):
        button = QPushButton(label)
        button.setStyleSheet(f"""
            QPushButton {{
                font-size: 16px;
                padding: 10px;
                background-color: {bg_color};
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 5px;
            }}
            QPushButton:hover {{
                background-color: #d0d0d0;
            }}
        """)
        button.clicked.connect(lambda: self.handle_fsm_event(event, label))
        self.layout.addWidget(button)

    def trigger_event(self, event):
        self.simulator.trigger_event(event)
        # 🔧 Şarj başlatıldığında oturum güncelle
        if event == "start_charging":
            self.mark_session_started()
        elif event == "charging_complete":
            self.mark_session_completed()
        self.update_status()

    def handle_fsm_event(self, event, label):
        if event == "connect_vehicle":
            self.log_action(label)
            self.send_service_discovery_message()
            self.send_service_discovery_response()

        elif event == "auth_ok":
            self.send_auth_message()

        elif event == "start_charging":
            self.loop.create_task(self.send_charging_started())
            if self.session_id is not None:
                try:
                    self.db.execute_query(
                        "UPDATE charging_sessions SET session_status = %s WHERE id = %s",
                        ('started', self.session_id)
                    )
                    print(f"[Veri Tabanı] Şarj durumu güncellendi: ID = {self.session_id}")
                except Exception as e:
                    print(f"[Veri Tabanı HATA] Güncelleme başarısız: {e}")
            else:
                print("[Uyarı] session_id tanımlı değil. Şarj oturumu güncellenemez.")

        elif event == "charging_completed":
            self.send_charging_completed()
        elif event == "start_payment":
            self.send_payment_confirmation()
            self.status_label.setText("💳 Ödeme Gerçekleşiyor...")
            self.payment_timer.start(6500)  # 6.5 saniye bekle

        #elif event == "disconnect":
            #self.trigger_event("disconnect")

        self.trigger_event(event)

    def send_service_discovery_message(self):
        try:
            # Veritabanından alınan oturum ID'si string'e çevrilmeli
            session_id = str(self.session_id)

            # Araç tarafından desteklenen servisler (örnek)
            services = [
                (1, "AC Charging"),
                (2, "DC Charging"),
                (3, "PlugAndCharge")
            ]

            # XML üretimi
            xml_output = generate_service_discovery_req(session_id, services)

            if not xml_output:
                print("[HATA] XML üretilemedi.")
                return

            # XSD dosya yolu
            xsd_path = "iso15118/schemas/ServiceDiscoveryReq.xsd"
            # XSD doğrulama
            is_valid = validate_xml(xml_output, xsd_path)

            if is_valid:
                print(xml_output.decode("utf-8"))
                self.status_label.setText("📡 Servis Keşif Mesajı Gönderildi (Geçerli)")
            else:
                self.status_label.setText("⚠️ XML Geçersiz")

        except Exception as e:
            print("[HATA]", e)
            self.status_label.setText("⚠️ Bir hata oluştu")

    def send_service_discovery_response(self):
        try:
            # Veritabanından alınan oturum ID'si string'e çevrilmeli
            session_id = str(self.session_id)
            response_code = "OK"  # Gerçek senaryoda bu "FAILED", "OK" gibi olabilir

            matched_services = [
                {"id": 3, "name": "PlugAndCharge"}
            ]

            # XML üretimi
            xml_output = generate_service_discovery_res(session_id, response_code, matched_services)
            if not xml_output:
                print("[HATA] Yanıt XML üretilemedi.")
                return

            # XSD doğrulama
            xsd_path = "iso15118/schemas/ServiceDiscoveryRes.xsd"
            is_valid = validate_xml(xml_output, xsd_path)

            if is_valid:
                print(xml_output.decode("utf-8"))
                self.status_label.setText("✅ ServiceDiscoveryRes mesajı üretildi ve geçerli.")
            else:
                self.status_label.setText("⚠️ Yanıt XML doğrulaması başarısız.")

        except Exception as e:
            print("[HATA]", e)
            self.status_label.setText("⚠️ ServiceDiscoveryRes gönderiminde hata.")

    def complete_payment_process(self):
        self.trigger_event("payment_complete")
        #self.status_label.setText("✅ Ödeme Alındı")

    def send_auth_message(self):
        if self.selected_vehicle_id is None:
            print("[Uyarı] Araç seçilmedi.")
            return

        # ✅ Authorize gönder
        if self.charge_point:
            print("[DEBUG] Authorize tetikleniyor")
            self.loop.create_task(self.charge_point.authorize_id_tag())
        else:
            print("[DEBUG] charge_point nesnesi hazır değil!")

    def send_payment_confirmation(self):
        if self.selected_vehicle_id is None:
            print("[Uyarı] Araç seçilmedi.")
            return

        message = {
            "message_type": "PaymentConfirmation",
            "vehicle_id": self.selected_vehicle_id,
            "plate": self.vehicle_selector.currentText(),
            "payment_status": "confirmed",
            "timestamp": datetime.utcnow().isoformat()
        }

        #send_ocpp_message(message)

    async def send_charging_started(self):
        if self.selected_vehicle_id is None:
            print("[Uyarı] Araç seçilmedi.")
            return

        if self.charge_point:
            print("[DEBUG] Start Transaction tetikleniyor")
            await self.charge_point.start_transaction()

            # Ardışık heartbeat gönderimi
            for i in range(3):
                await self.charge_point.send_heartbeat()
                await asyncio.sleep(0.5)
        else:
            print("[DEBUG] charge_point nesnesi hazır değil!")

        message = {
            "message_type": "StartTransaction",
            "vehicle_id": self.selected_vehicle_id,
            "plate": self.vehicle_selector.currentText(),
            "charge_level_start": self.charge_level,
            "state_at_start": "Araç Bağlandı",
            "timestamp": datetime.utcnow().isoformat()
        }

        #send_ocpp_message(message)

    def add_error_button(self, label, error_msg=None, action=None):
        button = QPushButton(label)
        if action == "resolve":
            button.setStyleSheet("""
                QPushButton {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    font-size: 15px;
                    padding: 8px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #c3e6cb;
                }
            """)
            button.clicked.connect(self.resolve_error)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #fff3cd;
                    border: 1px solid #ffeeba;
                    color: #856404;
                    font-size: 15px;
                    padding: 8px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #ffeeba;
                }
            """)
            button.clicked.connect(lambda: self.simulate_error(error_msg))
        self.layout.addWidget(button)

    def add_selected_error(self):
        selected_error = self.error_dropdown.currentText()
        current_state = self.simulator.get_current_state()

        if self.simulator.pda.contains(selected_error):
            self.status_label.setText(f"⚠️ Zaten eklenmiş: {selected_error}")
            return

        allowed_states = self.error_rules.get(selected_error, [])
        if current_state.strip() not in [s.strip() for s in allowed_states]:
            self.status_label.setText(f"⛔ Bu durumda bu hata geçerli değil: {selected_error}")
            return

        self.simulate_error(selected_error)


    def simulate_error(self, error_msg):
        self.simulator.simulate_error(error_msg)
        self.update_status()
        self.update_error_panel()

        # Mevcut FSM durumu
        #current_state = self.simulator.get_current_state()
        #print("Heyyy buradayım/////..............", current_state)
        # ✅ JSON mesajı oluştur
        message = {
            "message_type": "StatusNotification",
            "connector_id": 1,
            "status": "Error",
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

        # ✅ charge_point varsa JSON mesajını gönder
        if self.charge_point:
            print("[DEBUG] StatusNotification gönderiliyor")
            self.loop.create_task(self.charge_point.send_status_notification(message))
        else:
            print("[DEBUG] charge_point nesnesi tanımlı değil, StatusNotification gönderilemedi.")

    def resolve_error(self):
        self.simulator.resolve_error()
        self.update_status()
        self.update_error_panel()

    def update_status(self):
        current_state = self.simulator.get_current_state()
        if current_state == "Ödeme Onayı" and self.payment_timer.isActive():
            self.status_label.setText("💳 Ödeme Gerçekleşiyor...")
        else:
            self.status_label.setText(f"Durum: {current_state}")

        icon_map = {
            "Boşta": "🚗",
            "Araç Bağlandı": "🚗🔌",
            "Sertifika Doğrulama": "🚗🔌",
            "Kimlik Doğrulandı": "🚗🔌",
            "Şarj Ediliyor": "🚗⚡",
            "Şarj Tamamlandı": "🚗✅",
            "Ödeme Onayı": "🚗💳",
            "Ödeme Alındı": "💸✅",
            "Error": "🚗❌"
        }
        self.vehicle_icon.setText(icon_map.get(current_state, "🚗"))

        self.battery_outer.setVisible(current_state != "Boşta")

        if current_state == "Şarj Ediliyor":
            self.charge_progress.setVisible(True)
            self.charge_status.setVisible(True)
            self.charge_progress.setValue(self.charge_level)
            self.charge_timer.start(200)
        else:
            self.charge_progress.setVisible(False)
            self.charge_status.setVisible(False)
            self.charge_timer.stop()

    def update_charge_progress(self):
        if self.charge_level < 100:
            self.charge_level += 1
            self.charge_progress.setValue(self.charge_level)
            self.battery_level.setGeometry(0, 0, int(60 * self.charge_level / 100), 25)

            if self.charge_level < 20:
                color = "#cc0000"
            elif self.charge_level < 60:
                color = "#ffcc00"
            else:
                color = "#33cc33"

            self.battery_level.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            self.battery_label.setText(f"🔋 %{self.charge_level}")

            kalan_saniye = self.charge_duration * (100 - self.charge_level) // 100
            self.charge_status.setText(
                f"🔌 <b>Şarj Oluyor</b> %{self.charge_level} &nbsp;&nbsp;⏳ <i>{kalan_saniye} sn kaldı</i>"
            )
            self.charge_status.setStyleSheet("color: #155724; font-size: 15px; margin-top: 5px;")
        else:
            self.charge_timer.stop()
            self.charge_status.setText("✅ <b>Şarj Dolu</b>")
            self.trigger_event("charging_complete")
            self.charge_level = 20  # Şarj dolunca tekrar 20%'ye çek
            self.update_status()

    def update_error_panel(self):
        while self.error_panel.count():
            item = self.error_panel.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        current_stack = self.simulator.pda.get_stack()
        hata_sayisi = len(current_stack)
        self.error_title.setText(f"🔴 PDA Hata Yığını ({hata_sayisi})")
        for idx, error in enumerate(current_stack, 1):
            label = QLabel(f"[{idx}] 🔴 {error}")
            label.setStyleSheet("background-color: #ffdddd; padding: 5px; border: 1px solid #cc0000; font-size: 14px;")
            label.setAlignment(Qt.AlignCenter)
            self.error_panel.addWidget(label)


def run_gui():
    app = QApplication(sys.argv)

    from qasync import QEventLoop  # pip install qasync
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    def start_main_window():
        window = MainWindow()
        window.show()

    loading = LoadingScreen(start_main_window)
    loading.show()

    with loop:
        loop.run_forever()


