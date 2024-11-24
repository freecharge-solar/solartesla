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
        response = self.session.get(f"{self.URL}/site/{self.site}/currentPowerFlow?api_key={self.key}")
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
        self.time_of_last_start = 0
        self.time_of_last_stop = 0
        self.time_of_last_sufficient = 0

        self.time_of_last_positive = 0
        self.time_of_last_negative = 0

        self.sleep_time_active = 15
        self.sleep_time_idle = 300
        self.sleep_time = self.sleep_time_active

    def runonce(self):
        print(f"{datetime.now().isoformat(timespec='seconds')}", end=" | ")

        currentPowerFlow = self.solaredge.get_site_currentPowerFlow()

        pv_status = self.solaredge.check_status(currentPowerFlow)
        if pv_status == "Idle":
            self.sleep_time = self.sleep_time_idle
        else:
            # assert pv_status == "Active"
            self.sleep_time = self.sleep_time_active

        produced_current = self.solaredge.check_production(currentPowerFlow)
        print("☀️" if pv_status == "Active" else "🌙", end="")
        print(f"{produced_current:.2f}A", end=" ")
        # {'siteCurrentPowerFlow': {'updateRefreshRate': 3, 'unit': 'kW', 'connections': [{'from': 'GRID', 'to': 'Load'}], 'GRID': {'status': 'Active', 'currentPower': 0.55}, 'LOAD': {'status': 'Active', 'currentPower': 0.55}, 'PV': {'status': 'Idle', 'currentPower': 0.0}}}

        excess_current = self.solaredge.check_excess(currentPowerFlow)
        load_current = produced_current - excess_current
        print(f"💡{load_current:.2f}A", end=" ")
        print(f"{excess_current:+.2f}A", end=" | ")

        if pv_status == "Idle":
            ## ideally, check if vehicle is still charging and stop it
            ## however, for now, just skip because we can't start/stop anyways
            print("SKIP ∵ 🌙")
            return

        try:
            self.tesla_ble.guess_state()
        except subprocess.TimeoutExpired as e:
            print("TimeoutExpired:", e)
            return
        
        if not self.tesla_ble.home:
            print("🏠False | SKIP ∵ 🏠False")
            self.tesla_ble.reset()
            return
        else:
            print(f"🏠True", end=" ")
            if self.tesla_ble.sleeping:
                ## ideally, check if vehicle needs to be awoken to check if need to start/stop
                ## however, for now, just skip because we can't start/stop anyways
                print(f"| 🚗💤")
                return
            elif self.tesla_ble.cable_state == "Disconnected":
                print("SKIP ∵ ⚡Disconnected")
                return

        print("|", end=" ")

        charge_current_request_max = 32

        charge_amps = self.tesla_ble.charge_amps
        if charge_amps is None:
            print("Warning: charge_amps is None, assuming 5A")
            charge_amps = 5
        charger_actual_current = charge_amps
        # with BLE, we don't actually know charger_actual_current, so we just assume it
        if charger_actual_current > load_current:
            print(f"⚡Stopped?", end=" ")
            # print("Probably not charging because charger_actual_current > home_current")
            # print("Setting charger_actual_current to 0")
            charger_actual_current = 0
        else:
            print(f"⚡Charging?", end=" ")

        print(f"{charger_actual_current}/{charge_amps}/{charge_current_request_max}A", end=" | ")

        new_charge_amps = math.floor(charger_actual_current + excess_current)
        print(f"🎯{new_charge_amps}A", end=" ")
        print("|", end=" ")

        new_charge_amps = min(charge_current_request_max, max(5, new_charge_amps), math.floor(produced_current))
        try:
            p = self.tesla_ble.guess_charging_set_amps(new_charge_amps)
            if p.returncode == 0:
                print(f"⚡→{new_charge_amps}A")
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
        self.cable_state = None
        self.charge_amps = None

    def guess_state(self):
        # charge_port_close() is gives good clues about charging state
        # BLE close-charge-port can give some clues about the vehicle state
        # 
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
        p = self.run_retryIfCommonError(5, self.charge_port_close)

        if p.returncode == 0:
            # successfully closed charge port, so must be disconnected at home
            self.home = True
            self.sleeping = False
            self.cable_state = "Disconnected"
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: already closed"):
            # charge port already closed, so must be disconnected at home
            self.home = True
            self.sleeping = False
            self.cable_state = "Disconnected"
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: cable connected"):
            # must be connected at home, but don't know if charging or stopped
            self.home = True
            self.sleeping = False
            self.cable_state = "Connected"
        elif p.stderr.startswith(b"Couldn't verify success: context deadline exceeded") or \
             p.stderr.startswith(b"Error: context deadline exceeded"):
            # this happens when car is sleeping
            self.home = True
            self.sleeping = True
        elif p.stderr.startswith(b"Error: failed to find BLE beacon"):
            # probably not at home, but should try a few times in case we have bad signal
            self.home = False
        else:
            # unknown state
            print(p.stderr)

        if self.charge_amps is None:
            for _ in range(5):
                # retry up to 5 times
                p = self.guess_charging_set_amps(5)
                if p.returncode == 0:
                    break

    def guess_charging_set_amps(self, amps):
        p = self.run_retryIfCommonError(5, lambda: self.charging_set_amps(amps))

        if p.returncode == 0:
            # successfully set charging amps, so charge_amps is known
            # however this is not an indication that the car is connected because it returns 0 even when the car is disconnected
            # it is also not an indication that the car is charging because it returns 0 even when charging is stopped
            self.charge_amps = amps
        elif not p.stderr.startswith(b"Error: failed to find BLE beacon"):
            print("Unknown Error:")
            print(p.stderr)

        return p

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


if __name__ == '__main__': 
    from config import *
    solartesla = SolarExcessCharger(SOLAREDGE_SITE, SOLAREDGE_KEY)
    solartesla.loop()
