# Charge Tesla with excess solar ▦

from datetime import datetime
import json
import math
import requests
import subprocess
import time

# import logging
# logging.basicConfig(level=logging.DEBUG, format="%(message)s")


class SolarEdgeMonitoring:

    URL = "https://monitoringapi.solaredge.com"

    def __init__(self, site, key):
        self.site = site
        self.key = key
        self.session = requests.Session()

    def reset(self):
        self.session.close()
        self.session = requests.Session()

    def get_site_inventory(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/inventory?api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_site_details(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/details?api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_site_energyDetails(self, meters, timeUnit, startTime, endTime):
        response = self.session.get(f"{self.URL}/site/{self.site}/energyDetails?meters={meters}&timeUnit={timeUnit}&startTime={startTime}&endTime={endTime}&api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_site_overview(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/overview?api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_site_currentPowerFlow(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/currentPowerFlow?api_key={self.key}", timeout=30)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def check_status(self, currentPowerFlow=None):
        if currentPowerFlow is None:
            currentPowerFlow = self.get_site_currentPowerFlow()
        pv_status = currentPowerFlow["siteCurrentPowerFlow"]["PV"]["status"]
        return pv_status

    def check_production(self, currentPowerFlow=None):
        if currentPowerFlow is None:
            currentPowerFlow = self.get_site_currentPowerFlow()
        produced_power = currentPowerFlow["siteCurrentPowerFlow"]["PV"]["currentPower"]
        power_amps = 1000 * produced_power / 230
        return power_amps

    def check_excess(self, currentPowerFlow=None):
        if currentPowerFlow is None:
            currentPowerFlow = self.get_site_currentPowerFlow()
        grid_power = (currentPowerFlow["siteCurrentPowerFlow"]["GRID"]["currentPower"])
        if {'from': 'GRID', 'to': 'Load'} in currentPowerFlow["siteCurrentPowerFlow"]["connections"]:
            grid_power = -grid_power
        power_amps = 1000 * grid_power / 230
        return power_amps


class SolarExcessCharger:
    def __init__(self, solaredge_site, solaredge_key):
        self.solaredge = SolarEdgeMonitoring(solaredge_site, solaredge_key)
        self.tesla_ble = TeslaBLE()
        self.charge_manager = ChargingManager()

        self.sleep_time_active = 15
        self.sleep_time_idle = 300
        self.sleep_time = self.sleep_time_active

    def runonce(self):
        print(f"{datetime.now().isoformat(timespec='seconds')}", end=" | ")

        try:
            self.tesla_ble.guess_state()
        except subprocess.TimeoutExpired as e:
            print("TimeoutExpired:", e)
            return
        
        currentPowerFlow = self.solaredge.get_site_currentPowerFlow()

        pv_status = self.solaredge.check_status(currentPowerFlow)
        if pv_status == "Idle":
            self.sleep_time = self.sleep_time_idle
        else:
            # assert pv_status == "Active"
            self.sleep_time = self.sleep_time_active

        produced_current = self.solaredge.check_production(currentPowerFlow)
        print("🌞" if pv_status == "Active" else "🌙", end="")
        print(f"{produced_current:.2f}A", end=" ")
        # {'siteCurrentPowerFlow': {'updateRefreshRate': 3, 'unit': 'kW', 'connections': [{'from': 'GRID', 'to': 'Load'}], 'GRID': {'status': 'Active', 'currentPower': 0.55}, 'LOAD': {'status': 'Active', 'currentPower': 0.55}, 'PV': {'status': 'Idle', 'currentPower': 0.0}}}

        excess_current = self.solaredge.check_excess(currentPowerFlow)
        load_current = produced_current - excess_current
        print(f"💡{load_current:.2f}A", end=" ")
        print(f"{excess_current:+.2f}A", end=" | ")

        # charge_manager is responsible for keeping time of to/from grid direction
        # this is used to determine when to start/stop charging, and even to wake up the car to start charging
        self.charge_manager.update(excess_current)

        ## 29/01/2025 keep checking car state throughout the night, which doesn't wake it up anymore
        # if pv_status == "Idle":
        #     ## ideally, check if vehicle is still charging and stop it
        #     ## however, for now, just skip because we can't start/stop anyways
        #     print("SKIP ∵ 🌙")
        #     return

        if not self.tesla_ble.home:
            print("🏠False | SKIP ∵ 🏠False")
            self.tesla_ble.reset()
            return
        else:
            print(f"🏠True |", end=" ")

        duration_threshold = 300

        if self.tesla_ble.sleeping:
            print(f"🚗💤", end=" ")
            # check if vehicle needs to be awoken if need to start
            if self.charge_manager.prev_direction == +1:
                print(f"⏳{self.charge_manager.prev_duration:.1f}s", end=" ")
                if self.charge_manager.prev_duration > duration_threshold:
                    print("WAKE!", end=" ")
                    self.tesla_ble.guess_wake()
                    print("START!", end=" ")
                    self.tesla_ble.guess_charging_start()
                    print("")
                    return
            print("| SKIP ∵ 🚗💤")
            return
        
        print(f"🔋{self.tesla_ble.battery_level}%/{1.60934 * self.tesla_ble.battery_range:.0f}km", end=" ")
        print(f"🔌{self.tesla_ble.charging_state}", end=" ")

        if self.tesla_ble.charging_state == "Disconnected":
            print("| SKIP ∵ ⚡Disconnected")
            return

        charge_current_request_max = self.tesla_ble.charge_current_request_max
        charge_amps = self.tesla_ble.charge_current_request
        charger_actual_current = self.tesla_ble.charger_actual_current
        charge_limit_soc = self.tesla_ble.charge_limit_soc
        charger_power = self.tesla_ble.charger_power
        charger_voltage = self.tesla_ble.charger_voltage
        charger_phases = self.tesla_ble.charger_phases

        print(f"⭕{charge_limit_soc}% ⚡{charger_actual_current}/{charge_amps}/{charge_current_request_max}A {charger_power}kW {charger_voltage}V ({charger_phases})", end=" | ")

        if self.tesla_ble.charging_state == "Complete":
            print("| SKIP ∵ ⚡Complete")
            return

        if self.tesla_ble.charging_state == "Stopped":
            if self.charge_manager.prev_direction == +1:
                print(f"⏳{self.charge_manager.prev_duration:.1f}s", end=" ")
                if self.charge_manager.prev_duration > duration_threshold:
                    print("START!", end=" ")
                    self.tesla_ble.guess_charging_start()
                    print("")
                    return
            print("| SKIP ∵ ⚡Stopped")
            return
        if self.tesla_ble.charging_state == "Charging" and pv_status == "Idle":
            if self.charge_manager.prev_direction == -1:
                print(f"⏳{self.charge_manager.prev_duration:.1f}s", end=" ")
                if self.charge_manager.prev_duration > duration_threshold:
                    print("STOP!", end=" ")
                    self.tesla_ble.guess_charging_stop()
                    print("")
                    return
            
        new_charge_amps = math.floor(charger_actual_current + excess_current)
        print(f"🎯{new_charge_amps}A", end=" ")
        print("|", end=" ")

        if new_charge_amps == charger_actual_current:
            print("")
            return

        new_charge_amps = min(charge_current_request_max, max(0, new_charge_amps), math.floor(produced_current))
        try:
            p = self.tesla_ble.guess_charging_set_amps(new_charge_amps)
            if p.returncode == 0:
                print(f"⚡→{new_charge_amps}A")
                time.sleep(3)  # always wait a few seconds after setting charging amps, to prevent immediate checking of usage before it is applied to vehicle and before solar monitor updates
            else:
                print(f"⚡→{new_charge_amps}A??")
        except subprocess.TimeoutExpired as e:
            print("TimeoutExpired:", e)
            return

    def loop(self):
        while True:
            start_time = time.time()
            try:
                self.runonce()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    print("HTTP 429 Too Many Requests: Resetting connection")
                    self.solaredge.reset()
                    time.sleep(30)
                elif e.response.status_code == 500:
                    print("HTTP 500 Server Error: Resetting connection")
                    self.solaredge.reset()
                    time.sleep(60)
                else:
                    print(str(e))
            except requests.exceptions.ConnectionError as e:
                print(str(e))
            except requests.exceptions.ReadTimeout as e:
                print(str(e))
            elapsed_time = time.time() - start_time
            sleep_time = max(0, self.sleep_time - elapsed_time)
            time.sleep(sleep_time)


class FailedToEnumerateDeviceServices(Exception):
    pass


class FailedToFindBleBeacon(Exception):
    pass


class CouldntVerifySuccess(Exception):
    pass


class UnknownError(Exception):
    pass


class HciDeviceBusy(Exception):
    pass


class TeslaBLE:
    def __init__(self):
        self.reset()

        # test
#        self.charge_amps = 0

    def reset(self):
        self.home = None
        self.sleeping = None

        # self.cable_state = None  # deprecated
        # self.charge_amps = None  # deprecated
        # self.charge_state = None  # deprecated

        self.charging_state = None
        self.charger_actual_current = None
        self.charge_current_request = None
        self.charge_current_request_max = None
        self.battery_level = None
        self.battery_range = None
        self.charge_limit_soc = None
        self.charger_power = None
        self.charger_voltage = None
        self.charger_phases = None

    def guess_state(self):
        # Home or Away
        #   Home + (Awake or Sleeping)
        #   Home + Awake + (Disconnected or Connected)
        #
        # FailedToFindBleBeacon means Away
        # CouldntVerifySuccess means Sleeping
        #
        # Only 3 states:
        # AWAY, AWAKE or SLEEPING
        #
        p = self.run_retryIfCommonError(5, self.state_charge)
        if p.returncode == 0:
            # successfully received charge state, so must be at home
            self.home = True
            self.sleeping = False
            json_response = json.loads(p.stdout)
            # # print(json_response)
            # print("chargingState", json_response["chargeState"]["chargingState"])
            # # {'Charging': {}}
            # # {'Stopped': {}}
            # # {'Disconnected': {}}
            # # {'Starting': {}}
            # print("chargeLimitSoc", json_response["chargeState"]["chargeLimitSoc"])
            # print("batteryRange", json_response["chargeState"]["batteryRange"])
            # print("batteryLevel", json_response["chargeState"]["batteryLevel"])
            # print("chargerVoltage", json_response["chargeState"]["chargerVoltage"])
            # print("chargerPilotCurrent", json_response["chargeState"]["chargerPilotCurrent"])
            # print("chargerActualCurrent", json_response["chargeState"]["chargerActualCurrent"])
            # print("minutesToChargeLimit", json_response["chargeState"]["minutesToChargeLimit"])
            # print("chargeCurrentRequest", json_response["chargeState"]["chargeCurrentRequest"])
            # print("chargeCurrentRequestMax", json_response["chargeState"]["chargeCurrentRequestMax"])
            # print("chargingAmps", json_response["chargeState"]["chargingAmps"])
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
        elif p.stderr.startswith(b"Couldn't verify success: context deadline exceeded"):
            # this happens when car is sleeping
            self.home = True
            self.sleeping = True
        elif p.stderr.startswith(b"Error: failed to find BLE beacon") or \
             p.stderr.startswith(b"Error: context deadline exceeded"):  # after Dec 2024 tesla ble changes, this happens when car is out of range / not at home
            # probably not at home, but should try a few times in case we have bad signal
            self.home = False
        else:
            # unknown state
            print(p.stderr)

        # if self.home and self.charge_amps is None:
        #     for _ in range(5):
        #         # retry up to 5 times
        #         p = self.guess_charging_set_amps(5)
        #         if p.returncode == 0:
        #             break

    def guess_charging_set_amps(self, amps):
        p = self.run_retryIfCommonError(5, lambda: self.charging_set_amps(amps))

        # if p.returncode == 0:
        #     # successfully set charging amps, so charge_amps is known
        #     # however this is not an indication that the car is connected because it returns 0 even when the car is disconnected
        #     # it is also not an indication that the car is charging because it returns 0 even when charging is stopped
        #     self.charge_amps = amps
        # elif not p.stderr.startswith(b"Error: failed to find BLE beacon") and \
        #      not p.stderr.startswith(b"Couldn't verify success: context deadline exceeded"):
        #     print("Unknown Error:")
        #     print(p.stderr)

        return p

    def guess_wake(self):
        p = self.run_retryIfCommonError(5, self.wake)
        print(p.stderr, end=" ")
        print(p.returncode, end=" ")

    def guess_charging_start(self):
        p = self.run_retryIfCommonError(5, self.charging_start)
        print(p.stderr, end=" ")
        print(p.returncode, end=" ")

    def guess_charging_stop(self):
        p = self.run_retryIfCommonError(5, self.charging_stop)
        print(p.stderr, end=" ")
        print(p.returncode, end=" ")

    def run_retryIfCommonError(self, retry, func):
        # robustly run the bluetooth command (it is quite unreliable without this)
        # retries on common errors, but always passes through the command result
        attempt = 0
        p = None
        while attempt <= retry:
            p = func()
            if p.returncode == 0:
                # success!
                return p
            elif p.stderr.startswith(b"Error: failed to find a BLE device: can't init hci: no devices available: (hci0: can't down device: device or resource busy)"):
                # this happens sometimes unexpectedly, and need to reset bluetooth
                # note this is different to "can't up device", which does not need bluetooth reset
                print("Retry: need bluetooth reset")
                print(p.stderr)
                self.hciconfig_up()
                attempt += 0 # don't count this as an attempt
                continue
            elif p.stderr.startswith(b"Error: ble: failed to enumerate device services") or \
                 p.stderr.startswith(b"Error: ble: couldn't fetch descriptors: ATT request failed: input channel closed: io: read/write on closed pipe") or \
                 p.stderr.startswith(b"Error: ble: failed to discover service characteristics: ATT request failed: input channel closed: io: read/write on closed pipe") or \
                 p.stderr.startswith(b"Error: the vehicle is already connected to the maximum number of BLE devices") or \
                 p.stderr.startswith(b"Failed to execute command: ATT request failed: input channel closed: io: read/write on closed pipe") or \
                 p.stderr.startswith(b"Error: failed to find a BLE device: can't init hci: no devices available: (hci0: can't up device: connection timed out)") or \
                 p.stderr.startswith(b"Error: failed to find a BLE device: can't init hci: no devices available: (hci0: can't up device: interrupted system call)"):
                # these happen sometimes unexpectedly, it seems to be a computer problem rather than car problem
                # print("Retry: known error")  ## DEBUG only
                # print(p.stderr)  ## DEBUG only
                print(attempt, end=" ")
                attempt += 1
                continue
            else:
                # unknown error, pass through the result
                return p
        # exhausted retries, pass through the result
        return p

    def hciconfig_up(self):
        p = subprocess.run(["sudo", "hciconfig", "hci0", "down"], capture_output=True, timeout=30)
        print(p)
        time.sleep(1)
        return p

    def charge_port_close(self):
        ## Note we're going to change the design so that these direct issued commands are simple, and wrapping retry and parsing results is outside
        ## these commands should not change vehicle state model
        p = subprocess.run(["tesla-control", "-ble", "charge-port-close"], capture_output=True, timeout=30)
        return p

    def charging_set_amps(self, amps):
        p = subprocess.run(["tesla-control", "-ble", "charging-set-amps", str(amps)], capture_output=True, timeout=30)
        return p

    def wake(self):
        p = subprocess.run(["tesla-control", "-ble", "wake"], capture_output=True, timeout=30)
        return p

    def charging_start(self):
        p = subprocess.run(["tesla-control", "-ble", "charging-start"], capture_output=True, timeout=30)
        return p

    def charging_stop(self):
        p = subprocess.run(["tesla-control", "-ble", "charging-stop"], capture_output=True, timeout=30)
        return p
    
    def state_charge(self):
        p = subprocess.run(["tesla-control", "-ble", "state", "charge"], capture_output=True, timeout=30)
        return p

    def body_controller_state(self):
        p = subprocess.run(["tesla-control", "-ble", "body-controller-state"], capture_output=True, timeout=30)
        return p


class ChargingManager:
    def __init__(self):
        self.low_threshold = 0.0  # amps  ## 0.0
        self.high_threshold = 2.0  # amps  ## 4.0   0.1

        self.prev_time = None
        self.prev_direction = None  # 0, -1, +1
        self.prev_duration = 0

    def update(self, excess_amps, duration_threshold=300):  ## 300  100
        now = time.time()
        direction = 0
        if excess_amps > self.high_threshold:
            direction = +1
        elif excess_amps < self.low_threshold:
            direction = -1
        if self.prev_direction != direction or direction == 0:
            self.prev_time = now
        self.prev_duration = now - self.prev_time
        self.prev_direction = direction


if __name__ == '__main__': 
    from config import *
    solartesla = SolarExcessCharger(SOLAREDGE_SITE, SOLAREDGE_KEY)
    solartesla.loop()
