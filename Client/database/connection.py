# database/connection.py

import psycopg2

class DatabaseManager:
    def __init__(self, db_name, user, password, host="localhost", port="5432"):
        try:
            self.conn = psycopg2.connect(
                dbname=db_name,
                user=user,
                password=password,
                host=host,
                port=port
            )
            self.cursor = self.conn.cursor()
            print("[Database] Bağlantı başarılı.")
        except Exception as e:
            print(f"[Database] Bağlantı hatası: {e}")

    def insert_vehicle(self, plate, vin, capacity_kwh):
        try:
            self.cursor.execute(
                "INSERT INTO vehicles (plate, vin, battery_capacity_kwh) VALUES (%s, %s, %s) RETURNING id",
                (plate, vin, capacity_kwh)
            )
            vehicle_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return vehicle_id
        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            self.cursor.execute("SELECT id FROM vehicles WHERE vin = %s", (vin,))
            return self.cursor.fetchone()[0]

    def start_session(self, vehicle_id, connector_id=1, initial_state="Araç Bağlandı"):
        self.cursor.execute(
            """
            INSERT INTO charging_sessions (vehicle_id, connector_id, state_at_start)
            VALUES (%s, %s, %s) RETURNING id
            """,
            (vehicle_id, connector_id, initial_state)
        )
        session_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return session_id

    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except Exception as e:
            print(f"[Database] Sorgu hatası: {e}")
            if self.conn:
                self.conn.rollback()

    def execute_and_fetchone(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            self.conn.commit()
            return result
        except Exception as e:
            print(f"[Database] Sorgu hatası: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def execute_and_fetchall(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            result = self.cursor.fetchall()
            self.conn.commit()
            return result
        except Exception as e:
            print(f"[Database] Liste çekme hatası: {e}")
            if self.conn:
                self.conn.rollback()
            return []

    def get_vehicle_capacity(self, vehicle_id):
        try:
            self.cursor.execute("SELECT battery_capacity_kwh FROM vehicles WHERE id = %s", (vehicle_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"[Database] Kapasite alma hatası: {e}")
            return None

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[Database] Bağlantı kapatıldı.")

