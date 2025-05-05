import psycopg2
import json
from datetime import datetime

DB_CONFIG = {
    "dbname": "ocpp_db",
    "user": "postgres",
    "password": "Sekeroptik.123",
    "host": "localhost",
    "port": 5432
}

def insert_ocpp_log(cp_id: str, action: str, payload: dict):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ocpp_logs (charge_point_id, action, payload, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (
            cp_id,
            action,
            json.dumps(payload),
            datetime.utcnow()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] OCPP log kaydedilemedi: {e}")

def insert_error_log(component: str, error_message: str, details: str = None):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO error_logs (component, error_message, details, timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (component, error_message, details))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Hata logu kaydedilemedi: {e}")