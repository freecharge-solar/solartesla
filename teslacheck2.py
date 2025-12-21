from main2 import *
from config import *

tesla_ble = TeslaBLE()
tesla_ble.guess_state()

"""
            self.charging_state = list(json_response["chargeState"]["chargingState"])[0]
            self.charger_actual_current = json_response["chargeState"]["chargerActualCurrent"]
            self.charge_current_request = json_response["chargeState"]["chargeCurrentRequest"]
            self.charge_current_request_max = json_response["chargeState"]["chargeCurrentRequestMax"]
            self.battery_level = json_response["chargeState"]["batteryLevel"]
            self.battery_range = json_response["chargeState"]["batteryRange"]
            self.charge_limit_soc = json_response["chargeState"]["chargeLimitSoc"]
            self.charger_power = json_response["chargeState"]["chargerPower"]
            self.charger_voltage = json_response["chargeState"]["chargerVoltage"]
            self.charger_phases = json_response["chargeState"].get("chargerPhases", None)
"""

print(tesla_ble.charging_state)
print(tesla_ble.charger_actual_current)
print(tesla_ble.charge_current_request)
print(tesla_ble.charge_current_request_max)
print(tesla_ble.battery_level)
print(tesla_ble.battery_range)
print(tesla_ble.charge_limit_soc)
print(tesla_ble.charger_power)
print(tesla_ble.charger_voltage)
print(tesla_ble.charger_phases)
