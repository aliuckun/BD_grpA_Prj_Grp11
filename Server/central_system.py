
import asyncio
import json
import logging
from datetime import datetime
from websockets.server import serve
from ocpp.v16 import ChargePoint as CP
from ocpp.v16.enums import Action
from ocpp.v16 import call_result
from ocpp.routing import on

from shared_signals import log_signal
from db_logger import insert_ocpp_log, insert_error_log

logging.basicConfig(level=logging.INFO)

class ChargePoint(CP):

    @on(Action.boot_notification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        logging.info(f"[BootNotification] Model: {charge_point_model}, Vendor: {charge_point_vendor}")
        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status="Accepted"
        )

    @on(Action.heartbeat)
    async def on_heartbeat(self):
        logging.info("[Heartbeat] Alındı")
        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())

    @on(Action.authorize)
    async def on_authorize(self, id_tag, **kwargs):
        logging.info(f"[Authorize] ID Tag: {id_tag}")
        return call_result.Authorize(id_tag_info={"status": "Accepted"})

    @on(Action.start_transaction)
    async def on_start_transaction(self, connector_id, id_tag, meter_start, timestamp, **kwargs):
        logging.info(f"[StartTransaction] ID Tag: {id_tag}, Connector: {connector_id}")
        return call_result.StartTransaction(
            transaction_id=1,
            id_tag_info={"status": "Accepted"}
        )

    @on(Action.meter_values)
    async def on_meter_values(self, connector_id, meter_value, **kwargs):
        logging.info(f"[MeterValues] Connector: {connector_id}, Value: {meter_value}")
        return call_result.MeterValues()

    @on(Action.stop_transaction)
    async def on_stop_transaction(self, meter_stop, timestamp, transaction_id, **kwargs):
        logging.info(f"[StopTransaction] ID: {transaction_id}")
        return call_result.StopTransaction(id_tag_info={"status": "Accepted"})

    @on(Action.data_transfer)
    async def on_data_transfer(self, vendor_id, message_id, data, **kwargs):
        logging.info(f"[DataTransfer] vendor_id={vendor_id}, message_id={message_id}")
        try:
            if vendor_id == "com.example.vendor" and message_id == "ClientError":
                error_info = json.loads(data)
                logging.warning(f"[ClientError] Alındı: {error_info}")
                insert_error_log("client", error_info.get("error_type", ""), error_info.get("error_message", ""))
                return call_result.DataTransfer(status="Accepted")
            else:
                return call_result.DataTransfer(status="Rejected")
        except Exception as e:
            logging.error(f"[DataTransfer] Hata oluştu: {e}")
            return call_result.DataTransfer(status="Rejected")

    @on(Action.status_notification)
    async def on_status_notification(self, connector_id, error_code, status, **kwargs):
        timestamp = kwargs.get("timestamp", datetime.utcnow().isoformat())


        log_message = (
            f"[StatusNotification] Connector: {connector_id}, Status: {status}, "
            f"Error: {error_code}, Time: {timestamp}"
        )
        logging.info(log_message)

        # Zorunlu: Mutlaka yanıt dönülmelidir
        return call_result.StatusNotification()


async def on_connect(websocket, path):
    cp_id = path.strip("/") or "CP_1"
    charge_point = ChargePoint(cp_id, websocket)
    log_signal.new_log.emit(f"[🔌 Bağlantı] Yeni Charge Point bağlandı: {cp_id}")

    try:
        async for message in websocket:
            try:
                log_signal.new_log.emit(f"[📥 Gelen Mesaj] {message}")
                insert_ocpp_log(cp_id, "incoming", json.loads(message))
                await charge_point.route_message(message)
            except Exception as e:
                error_msg = f"[İşleme Hatası] {e}"
                log_signal.new_log.emit(error_msg)
                insert_error_log("central_system", str(e), message)
                await websocket.close()
    except Exception as disconnect_error:
        # Sadece hata varsa buraya girer
        logging.warning(f"[Bağlantı Hatası] {disconnect_error}")
    finally:
        # Bağlantı kesildiği anda burası kesin çalışır!
        message = f"Charge Point '{cp_id}' bağlantısı kapandı."
        logging.info(message)
        log_signal.new_log.emit(f"[🔌 KAPANDI] {message}")
        try:
            insert_error_log("websocket", "ConnectionClosed", message)
        except Exception as db_error:
            logging.error(f"[Veritabanı Hatası] {db_error}")



async def main():
    server = await serve(on_connect, "0.0.0.0", 9000, subprotocols=["ocpp1.6"])
    logging.info("🔧 Central System listening at ws://0.0.0.0:9000")
    await server.wait_closed()
