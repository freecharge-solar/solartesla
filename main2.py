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
        print(f"{excess_current:+.2f}A", end=" | ")


        try:
            self.tesla_ble.guess_state()
        except FailedToFindBleBeacon:
            print("🏠False | SKIP ∵ 🏠False")
            self.tesla_ble.reset()
            return
        except CouldntVerifySuccess:
            print(f"🏠True | 🚗💤 |", end=" ")
#            self.tesla_ble.reset()
            if pv_status == "Idle":
                print("SLEEP ∵ 🌙")
                return
            elif self.tesla_ble.charge_state == "Disconnected":
                print("SLEEP ∵ ⚡Disconnected")
                return
            elif produced_current > 5:
                print("WAKEUP ∵ 🏠True and ☀️>5A")
                try:
                    p = self.tesla_ble.wake()
#                    print(p)
                except Exception as e:
                    print("Can't wake up: ", e)
                    return
                self.sleep_time = 5
                return
            else:
                print("SLEEP ∵ 🏠True and ☀️<=5A")
                return
        except FailedToEnumerateDeviceServices:
            print("BLE Error")
            self.sleep_time = 1
            return
        except HciDeviceBusy:
            print("HciDeviceBusy")
            self.tesla_ble.hciconfig_up()
            return
        except UnknownError as e:
            print("Unknown Error: ", e)
            return
        except subprocess.TimeoutExpired as e:
            print("TimeoutExpired:", e)
            return

#
#        charger_actual_current = vehicle_data["response"]["charge_state"]["charger_actual_current"]
#        charge_amps = vehicle_data["response"]["charge_state"]["charge_amps"]
#        battery_level = vehicle_data["response"]["charge_state"]["battery_level"]
#        battery_range = vehicle_data["response"]["charge_state"]["battery_range"]
#        charger_voltage = vehicle_data["response"]["charge_state"]["charger_voltage"]
#        charge_current_request_max = vehicle_data["response"]["charge_state"]["charge_current_request_max"]
#        charge_limit_soc = vehicle_data["response"]["charge_state"]["charge_limit_soc"]
#        charging_state = vehicle_data["response"]["charge_state"]["charging_state"]  # "Charging" "Stopped" "Disconnected"
#        charger_power = vehicle_data["response"]["charge_state"]["charger_power"]
#        minutes_to_full_charge = vehicle_data["response"]["charge_state"]["minutes_to_full_charge"]
#        charge_energy_added = vehicle_data["response"]["charge_state"]["charge_energy_added"]
#        charge_miles_added_rated = vehicle_data["response"]["charge_state"]["charge_miles_added_rated"]
#        charger_phases = vehicle_data["response"]["charge_state"]["charger_phases"]
#
##        print("🔋" if battery_level > 40 else "🪫", end="")
##        print(f"{battery_level}%/{1.609344 * battery_range:.0f}km", end=" ")
##        print(f"⚡{charging_state}", end=" ")
##
##        if charging_state != "Disconnected" and charging_state is not None:
##            # Charging, Stopped, Complete, Starting
##            print(f"{charger_actual_current}/{charge_amps}/{charge_current_request_max}A", end=" ")
##            print(f"{charge_limit_soc}%", end=" ")
##
##        if charging_state == "Charging" or charging_state == "Starting":
##            print(f"{charger_power}kW", end=" ")
##            print(f"{charger_voltage}V", end=" ")
##            if charger_phases == 2:
##                print("❸", end=" ")
##            else:
##                print(f"({charger_phases})", end=" ")
##            print(f"+{charge_energy_added}kWh/{1.609344 * charge_miles_added_rated:.0f}km", end=" ")
##            h, m = divmod(minutes_to_full_charge, 60)
##            print(f"{h}h" if h else "", end="")
##            print(f"{m}m", end=" ")
##
##        print("|", end=" ")
#
        print(f"🏠True", end=" ")
        print("|", end=" ")
#
#        # if pv_status == "Idle":
#        #     print("SKIP ∵ 🌙")
#        #     return
#        #
#        if not self.tesla.last_at_home:
#            print("SKIP ∵ 🏠False")
#            return
#
#        if charging_state == "Disconnected":
#            print("SKIP ∵ ⚡Disconnected")
#            return
#
#        if charging_state == "Complete":
#            print("SKIP ∵ ⚡Complete")
#            return
#
#        if charging_state is None:
#            print("SKIP ∵ ⚡None")
#            return
#

#################
#        charge_amps = 10
        charge_amps = self.tesla_ble.charge_amps
        charging_state = self.tesla_ble.charge_state
        charger_actual_current = charge_amps

        if charging_state == "Disconnected":
            print("SKIP ∵ ⚡Disconnected")
            return

        if charging_state == "Stopped":
            print("jalksdfajsfdl")
            charger_actual_current = 0

#################

        new_charge_amps = math.floor(charger_actual_current + excess_current)
        print(f"🎯{new_charge_amps}A", end=" ")
        print("|", end=" ")

        now = time.time()
#        if new_charge_amps > 0:
#            self.time_of_last_sufficient = now
#
#        if excess_current > 0:
#            self.self.time_of_last_positive = now
#        else:
#            self.time_of_last_negative = now
#
#        if now - self.time_of_last_positive > 600:
#            # it's been more than 600 seconds since we had positive solar excess, so stop charging
#            self.tesla_ble.charging_stop()
#        elif now - self.time_of_last_negative > 600:
#            # it's been more than 600 seconds since we had negative solar excess, so start charging
#            self.tesla_ble.charging_start()


        #### DANGER WE DON'T WANT FREQUENT START STOP CHARGE AS THIS MAY WEAR OUT CAR CHARGER
        if charging_state == "Stopped":
            if new_charge_amps < 5:
                print("🎯<5A Not enough solar to start", end="")
            else:
                print("🎯>=5A ⏯️", end=" ")
                timer = 600 - (now - self.time_of_last_stop)
                if timer <= 0:
                    print("⌛now", end=", ")
#                    self.tesla.set_charge_start()
#                    self.tesla_ble.charging_start()
                    self.time_of_last_start = time.time()
                else:
                    m, s = divmod(int(timer), 60)
                    print("⏳", end="")
                    print(f"{m}m" if m else "", end="")
                    print(f"{s}s", end="")

        elif charging_state == "Charging" or charging_state == "Starting":
            if new_charge_amps > 0:
                print("🎯>0A 🆗", end="")
            else:
                print("🎯<=0A ⏹️", end=" ")
                timer = 600 - (now - self.time_of_last_sufficient)
                if timer <= 0:
                    print(f"⌛now", end="")
#                    self.tesla.set_charge_stop()
#                    self.tesla_ble.charging_stop()
                    self.time_of_last_stop = time.time()
                else:
                    m, s = divmod(int(timer), 60)
                    print("⏳", end="")
                    print(f"{m}m" if m else "", end="")
                    print(f"{s}s", end="")
        #### DANGER


########################
        charge_current_request_max = 32
########################

        new_charge_amps = min(charge_current_request_max, max(5, new_charge_amps), math.floor(produced_current))
        try:

#            if charging_state == "Stopped":
#                print("")
#                p = self.tesla_ble.ping()
#                return


            if True or new_charge_amps != charge_amps:  # always set amps, even if unchanged, because we don't really know what we're currently charging at with BLE
                print(" |", end=" ")
                p = self.tesla_ble.charging_set_amps(new_charge_amps)
                print(f"⚡→{new_charge_amps}A")
            else:
#                p = self.tesla_ble.ping()
                print("")
        except FailedToFindBleBeacon:
            print("🏠False | SKIP ∵ 🏠False")
            # self.tesla_ble.reset()  # 23/11/2024 don't reset, because we should actually be at home!
            return
        except CouldntVerifySuccess:
            print(f"🏠True | 🚗💤 |", end=" ")
            self.tesla_ble.reset()
            if pv_status == "Idle":
                print("SLEEP ∵ 🌙")
                return
            elif produced_current > 5:
                print("WAKEUP ∵ 🏠True and ☀️>5A")
#                p = self.tesla_ble.wake()
                self.sleep_time = 5
                return
            else:
                print("SLEEP ∵ 🏠True and ☀️<=5A")
                return
        except FailedToEnumerateDeviceServices:
            print("BLE Error")
            self.sleep_time = 1
            return
        except HciDeviceBusy:
            print("HciDeviceBusy")
            self.tesla_ble.hciconfig_up()
            return
        except UnknownError as e:
            print("Unknown Error: ", e)
            return
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
                    time.sleep(60)
                elif e.response.status_code == 500:
                    print("HTTP 500 Server Error: Resetting connection")
                    self.solaredge.reset()
                    time.sleep(60)
#                elif e.response.status_code == 401:
#                    print("🚗 HTTP 401 Unauthorized: Getting new access token")
#                    self.tesla.get_new_access_token()
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
        self.charge_amps = None
        self.charge_state = None

    def guess_state(self):
        # charge_port_close() is gives good clues about charging state
        p = self.charge_port_close()
        if self.charge_amps is None:
            p = self.charging_set_amps(5)
            if p.returncode == 0:
                self.charge_amps = 5

    def run_retry(self, retry, *args, **kwargs):
        attempt = 0
        while attempt <= retry:
            p = subprocess.run(*args, **kwargs)
#            print(attempt + 1, end=": ")
#            print(p)
            if p.stderr.startswith(b"Error: ble: failed to enumerate device services"):
#                print("retry")
                attempt += 1
                continue
            else:
                break
        return p

    def hciconfig_up(self):
        p = subprocess.run(["sudo", "hciconfig", "hci0", "down"], capture_output=True, timeout=30)
        print(p)
        return p

    def ping(self, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "ping"], capture_output=True, timeout=30)
        self.raise_for_status(p)
        return p

    def charge_port_close(self, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "charge-port-close"], capture_output=True, timeout=30)

        if p.returncode == 0:
            # successfully closed charge port, so must be disconnected
            self.charge_stats = "Disconnected"
            return p
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: already closed"):
            # charge port already closed, so must be disconnected
            self.charge_state = "Disconnected"
            return p
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: cable connected"):
            # must be connected, but don't know if charging or stopped
            self.charge_state = "Connected"
            return p

        self.raise_for_status(p)
        return p

    def charging_stop(self, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "charging-stop"], capture_output=True, timeout=30)

        if p.returncode == 0:
            # must be connected and charging, action to stop charging
            self.charge_state = "Stopped"
            return p
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: not_charging"):
            # must be connected and not charging, no action, so either stopped or completed
            self.charge_state = "Stopped"
            return p

        self.raise_for_status(p)
        return p

    def charging_start(self, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "charging-start"], capture_output=True, timeout=30)

        if p.returncode == 0:
            # must be connected and not charging, action to start charging
            self.charge_state = "Charging"
            return p
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: complete"):
            # must be connected and not charging, no action, so either stopped or completed
            self.charge_state = "Stopped"
            return p

        self.raise_for_status(p)
        return p

    def charging_set_amps(self, amps, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "charging-set-amps", str(amps)], capture_output=True, timeout=30)

        if p.returncode == 0:
            self.charge_amps = amps
            return p
        elif p.stderr.startswith(b"Failed to execute command: car could not execute command: SetChargingAmps failed"):
            # unknown why sometimes SetChargingAmps will fail
            return p

        self.raise_for_status(p)
        return p

    def wake(self, retry=1):
        p = self.run_retry(retry, ["tesla-control", "-ble", "wake"], capture_output=True, timeout=30)
#        self.raise_for_status(p)
        return p

    def raise_for_status(self, p):
        if p.returncode != 0:
            if p.stderr.startswith(b"Error: ble: failed to enumerate device services"):
                # this happens sometimes unexpectedly, it seems to be a computer problem rather than car problem
                raise FailedToEnumerateDeviceServices(p.stderr)
            elif p.stderr.startswith(b"Error: failed to find BLE beacon"):
                # this happens when car is too far away
                raise FailedToFindBleBeacon(p.stderr)
            elif p.stderr.startswith(b"Couldn't verify success: context deadline exceeded"):
                # this happens when car is sleeping
                raise CouldntVerifySuccess(p.stderr)
            elif p.stderr.startswith(b"Error: context deadline exceeded"):
                # this happens when car is sleeping
                raise CouldntVerifySuccess(p.stderr)
            elif p.stderr.startswith(b"Error: failed to find a BLE device: can't init hci: no devices available: (hci0: can't down device: device or resource busy)"):
                # this happens sometimes unexpectedly, and need to reset bluetooth
                raise HciDeviceBusy(p.stderr)
            else:
                raise UnknownError(p.stderr)




if __name__ == '__main__':
    from config import *
    tesla_auth = None
    solartesla = SolarExcessCharger(SOLAREDGE_SITE, SOLAREDGE_KEY)
    solartesla.loop()
