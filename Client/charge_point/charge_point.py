
import asyncio
import logging
import json
import os
from datetime import datetime
from websockets import connect
from ocpp.v16 import ChargePoint as CP
from ocpp.v16 import call

logging.basicConfig(level=logging.INFO)

def load_json(filename):
    # Dosyanın bulunduğu dizine göre tam yolu oluştur
    current_dir = os.path.dirname(__file__)
    full_path = os.path.join(current_dir, filename)
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)

class SmartChargePoint(CP):
    async def send_error_message(self, error_type: str, error_message: str):
        request = call.DataTransfer(
            vendor_id="com.example.vendor",
            message_id="ClientError",
            data=json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": error_type,
                "error_message": error_message
            })
        )
        try:
            response = await self.call(request)
            logging.info(f"[ClientError] Yanıt durumu: {response.status}")
        except Exception as e:
            logging.error(f"[ClientError] DataTransfer başarısız: {e}")

    async def send_boot_notification(self):
        try:
            data = load_json("BootNotification.json")
            request = call.BootNotification(
                charge_point_vendor=data.get("chargePointVendor"),
                charge_point_model=data.get("chargePointModel"),
                charge_box_serial_number=data.get("chargeBoxSerialNumber"),
                charge_point_serial_number=data.get("chargePointSerialNumber"),
                firmware_version=data.get("firmwareVersion"),
                iccid=data.get("iccid"),
                imsi=data.get("imsi"),
                meter_type=data.get("meterType"),
                meter_serial_number=data.get("meterSerialNumber")
            )
            response = await self.call(request)
            logging.info("BootNotification yanıtı: %s", response.status)
            await asyncio.sleep(response.interval)
        except Exception as e:
            logging.error(f"BootNotification failed: {e}")
            await self.send_error_message("BootNotificationError", str(e))

    async def send_heartbeat(self):
        try:
            _ = load_json("Heartbeat.json")
            response = await self.call(call.Heartbeat())
            logging.info("Heartbeat sent.")
        except Exception as e:
            logging.error(f"Heartbeat failed: {e}")
            await self.send_error_message("HeartbeatError", str(e))
        await asyncio.sleep(10)

    async def authorize_id_tag(self):
        try:
            data = load_json("Authorize.json")
            request = call.Authorize(
                id_tag=data.get("idTag", "UNKNOWN")
            )
            response = await self.call(request)
            logging.info(f"Authorize yanıtı: {response.id_tag_info['status']}")
        except Exception as e:
            logging.error(f"Authorize failed: {e}")
            await self.send_error_message("AuthorizeError", str(e))

    async def start_transaction(self):
        try:
            data = load_json("StartTransaction.json")
            request = call.StartTransaction(
                connector_id=data.get("connectorId", 1),
                id_tag=data.get("idTag"),
                meter_start=data.get("meterStart", 0),
                timestamp=data.get("timestamp", datetime.utcnow().isoformat())
            )
            response = await self.call(request)
            self.transaction_id = response.transaction_id
            logging.info(f"StartTransaction accepted. ID: {self.transaction_id}")
        except Exception as e:
            logging.error(f"StartTransaction failed: {e}")
            await self.send_error_message("StartTransactionError", str(e))

    async def send_meter_values(self):
        try:
            data = load_json("MeterValues.json")
            transaction_id = getattr(self, "transaction_id", None)
            request = call.MeterValues(
                connector_id=data.get("connectorId", 1),
                transaction_id=transaction_id,
                meter_value=data.get("meterValue", [])
            )
            await self.call(request)
            logging.info("MeterValues sent.")
        except Exception as e:
            logging.error(f"MeterValues failed: {e}")
            await self.send_error_message("MeterValuesError", str(e))

    async def stop_transaction(self):
        try:
            data = load_json("StopTransaction.json")
            transaction_id = getattr(self, "transaction_id", None)
            request = call.StopTransaction(
                meter_stop=data.get("meterStop", 0),
                timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
                transaction_id=transaction_id,
                id_tag=data.get("idTag"),
                reason=data.get("reason"),
                transaction_data=data.get("transactionData")
            )
            await self.call(request)
            logging.info("StopTransaction sent.")
        except Exception as e:
            logging.error(f"StopTransaction failed: {e}")
            await self.send_error_message("StopTransactionError", str(e))

    async def send_status_notification(self, data):
        try:
            request = call.StatusNotification(
                connector_id=data.get("connector_id", 1),
                error_code=data.get("error", "NoError"),
                status=data.get("status", "Available"),
                timestamp=data.get("timestamp")
            )
            response = await self.call(request)
            logging.info("StatusNotification yanıtı alındı.")
        except Exception as e:
            logging.error(f"StatusNotification failed: {e}")
            await self.send_error_message("StatusNotificationError", str(e))

    async def run_sequence(self):
        pass
        # await self.send_boot_notification()
        # await self.authorize_id_tag()
        # await self.start_transaction()
        # await self.send_meter_values()
        # await asyncio.sleep(2)
        # await self.stop_transaction()

async def main():
    try:
        async with connect("ws://192.168.20.71:9000/CP_1", subprotocols=["ocpp1.6"]) as ws:
            cp = SmartChargePoint("CP_1", ws)
            await asyncio.gather(cp.start(), cp.run_sequence(), cp.send_heartbeat())
    except Exception as e:
        logging.error(f"WebSocket bağlantısı başarısız: {e}")

if __name__ == "__main__":
    asyncio.run(main())
