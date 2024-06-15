# Charge Tesla with excess solar ▦

from datetime import datetime
import json
import math
import requests
import time

# import logging
# logging.basicConfig(level=logging.DEBUG, format="%(message)s")


class TeslaAPI:
    URL = "https://owner-api.teslamotors.com"
    AUTH_URL = "https://auth.tesla.com/oauth2/v3/token"

    def __init__(self, tesla_id, refresh_token, access_token=None, home=(0, 0)):
        self.tesla_id = tesla_id
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.home = home

        self.last_location = (0, 0)
        self.last_at_home = None
        self.last_disconnected = None
        self.session = requests.Session()

        if access_token is None:
            self.get_new_access_token()

    def get_new_access_token(self):
        url = self.AUTH_URL
        response = self.session.post(url, headers={"Content-Type": "application/json"},
                                     json={"refresh_token": self.refresh_token,
                                           "client_id": "ownerapi",
                                           "grant_type": "refresh_token",
                                           "scope": "openid email offline_access"})
        response.raise_for_status()
        json_response = response.json()
        self.access_token = json_response["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        return json_response

    def list_vehicles(self):
        url = f"{self.URL}/api/1/products"
        response = self.session.get(url)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def honk_horn(self):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/command/honk_horn"
        response = self.session.post(url)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def wake_up(self):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/wake_up"
        response = self.session.post(url)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def set_charge_start(self):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/command/charge_start"
        response = self.session.post(url)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def set_charge_stop(self):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/command/charge_stop"
        response = self.session.post(url)
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def set_charging_amps(self, amps):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/command/set_charging_amps"
        # print(url)
        response = self.session.post(url, json={"charging_amps": amps})
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_vehicle_data(self):
        url = f"{self.URL}/api/1/vehicles/{self.tesla_id}/vehicle_data"
        response = self.session.get(url, timeout=1)
        response.raise_for_status()
        json_response = response.json()
        self.get_vehicle_location(json_response)
        charging_state = json_response["response"]["charge_state"]["charging_state"]
        if charging_state == "Disconnected":
            self.last_disconnected = True
        else:
            self.last_disconnected = False
        return json_response

    def get_charge_state(self, vehicle_data=None):
        if vehicle_data is None:
            vehicle_data = self.get_vehicle_data()
        charge_amps = vehicle_data["response"]["charge_state"]["charge_amps"]
        charger_actual_current = vehicle_data["response"]["charge_state"]["charger_actual_current"]
        return charge_amps, charger_actual_current

    def get_vehicle_location(self, vehicle_data=None):
        if vehicle_data is None:
            vehicle_data = self.get_vehicle_data()
        latitude = vehicle_data["response"]["drive_state"]["latitude"]
        longitude = vehicle_data["response"]["drive_state"]["longitude"]
        if round(latitude, 3) == round(self.home[0], 3) and round(longitude, 3) == round(self.home[1], 3):
            self.last_at_home = True
        else:
            self.last_at_home = False
        self.last_location = latitude, longitude
        return latitude, longitude


class InvalidPowerFlow(Exception):
    pass


class SolarEdgeMonitoring:

    URL = "https://monitoringapi.solaredge.com"

    def __init__(self, site, key):
        self.site = site
        self.key = key
        self.session = requests.Session()
        self.previousPowerFlow = None

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

    def get_site_overview(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/overview?api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        return json_response

    def get_site_currentPowerFlow(self):
        response = self.session.get(f"{self.URL}/site/{self.site}/currentPowerFlow?api_key={self.key}")
        response.raise_for_status()
        json_response = response.json()
        if json_response == self.previousPowerFlow:
            # assume that the response is invalid if it is the same as the previous response
            raise InvalidPowerFlow()
        self.previousPowerFlow = json_response
        return json_response

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
    def __init__(self, solaredge_site, solaredge_key,
                 tesla_id, tesla_refresh_token, tesla_api_token=None, home=(0, 0)):
        self.solaredge = SolarEdgeMonitoring(solaredge_site, solaredge_key)
        self.tesla = TeslaAPI(tesla_id, tesla_refresh_token, tesla_api_token, home)
        self.time_of_last_start = 0
        self.time_of_last_stop = 0
        self.time_of_last_sufficient = 0

        self.sleep_time_active = 20
        self.sleep_time_idle = 300
        self.sleep_time = self.sleep_time_active

    def runonce(self):
        print(f"{datetime.now().isoformat(timespec='seconds')}", end=" | ")

        try:
            currentPowerFlow = self.solaredge.get_site_currentPowerFlow()
            # print(currentPowerFlow)
        except InvalidPowerFlow:
            print("ABORT due to invalid solar data")
            return

        pv_status = currentPowerFlow["siteCurrentPowerFlow"]["PV"]["status"]
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
            vehicle_data = self.tesla.get_vehicle_data()
        except requests.exceptions.Timeout:
            print(f"🚗Timeout")
            return
        except requests.HTTPError as e:
            if e.response.status_code == 408:
                print(f"🚗408💤 | 🏠{self.tesla.last_at_home} |", end=" ")
                if self.tesla.last_at_home is None:
                    print("WAKEUP ∵ 🏠None")
                    self.tesla.wake_up()
                    self.sleep_time = 5  # at night time, if we wait another 60s, car goes back to sleep again
                    return
                elif pv_status == "Idle":
                    print("SLEEP ∵ 🌙")
                    return
                elif self.tesla.last_at_home is False:
                    print("SLEEP ∵ 🏠False")
                    return
                elif self.tesla.last_disconnected:
                    print("SLEEP ∵ ⚡Disconnected")
                    return
                elif self.tesla.last_at_home is True:
                    if produced_current > 5:
                        print("WAKEUP ∵ 🏠True and ☀️>5A")
                        self.tesla.wake_up()
                        self.sleep_time = 5
                        return
                    else:
                        print("SLEEP ∵ 🏠True and ☀️<=5A")
                        return
            else:
                raise

        charger_actual_current = vehicle_data["response"]["charge_state"]["charger_actual_current"]
        charge_amps = vehicle_data["response"]["charge_state"]["charge_amps"]
        battery_level = vehicle_data["response"]["charge_state"]["battery_level"]
        battery_range = vehicle_data["response"]["charge_state"]["battery_range"]
        charger_voltage = vehicle_data["response"]["charge_state"]["charger_voltage"]
        charge_current_request_max = vehicle_data["response"]["charge_state"]["charge_current_request_max"]
        charge_limit_soc = vehicle_data["response"]["charge_state"]["charge_limit_soc"]
        charging_state = vehicle_data["response"]["charge_state"]["charging_state"]  # "Charging" "Stopped" "Disconnected"
        charger_power = vehicle_data["response"]["charge_state"]["charger_power"]
        minutes_to_full_charge = vehicle_data["response"]["charge_state"]["minutes_to_full_charge"]
        charge_energy_added = vehicle_data["response"]["charge_state"]["charge_energy_added"]
        charge_miles_added_rated = vehicle_data["response"]["charge_state"]["charge_miles_added_rated"]
        charger_phases = vehicle_data["response"]["charge_state"]["charger_phases"]

        print("🔋" if battery_level > 40 else "🪫", end="")
        print(f"{battery_level}%/{1.609344 * battery_range:.0f}km", end=" ")
        print(f"⚡{charging_state}", end=" ")

        if charging_state != "Disconnected" and charging_state is not None:
            # Charging, Stopped, Complete, Starting
            print(f"{charger_actual_current}/{charge_amps}/{charge_current_request_max}A", end=" ")
            print(f"{charge_limit_soc}%", end=" ")

        if charging_state == "Charging" or charging_state == "Starting":
            print(f"{charger_power}kW", end=" ")
            print(f"{charger_voltage}V", end=" ")
            if charger_phases == 2:
                print("❸", end=" ")
            else:
                print(f"({charger_phases})", end=" ")
            print(f"+{charge_energy_added}kWh/{1.609344 * charge_miles_added_rated:.0f}km", end=" ")
            h, m = divmod(minutes_to_full_charge, 60)
            print(f"{h}h" if h else "", end="")
            print(f"{m}m", end=" ")

        print("|", end=" ")

        print(f"🏠{self.tesla.last_at_home}", end=" ")
        print("|", end=" ")

        # if pv_status == "Idle":
        #     print("SKIP ∵ 🌙")
        #     return
        #
        if not self.tesla.last_at_home:
            print("SKIP ∵ 🏠False")
            return

        if charging_state == "Disconnected":
            print("SKIP ∵ ⚡Disconnected")
            return

        if charging_state == "Complete":
            print("SKIP ∵ ⚡Complete")
            return

        if charging_state is None:
            print("SKIP ∵ ⚡None")
            return

        new_charge_amps = math.floor(charger_actual_current + excess_current)
        print(f"🎯{new_charge_amps}A", end=" ")
        print("|", end=" ")

        now = time.time()
        if new_charge_amps > 0:
            self.time_of_last_sufficient = now

        #### DANGER WE DON'T WANT FREQUENT START STOP CHARGE AS THIS MAY WEAR OUT CAR CHARGER
        if charging_state == "Stopped":
            if new_charge_amps < 5:
                print("🎯<5A Not enough solar to start", end="")
            else:
                print("🎯>=5A ⏯️", end=" ")
                timer = 600 - (now - self.time_of_last_stop)
                if timer <= 0:
                    print("⌛now", end=", ")
                    self.tesla.set_charge_start()
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
                    self.tesla.set_charge_stop()
                    self.time_of_last_stop = time.time()
                else:
                    m, s = divmod(int(timer), 60)
                    print("⏳", end="")
                    print(f"{m}m" if m else "", end="")
                    print(f"{s}s", end="")
        #### DANGER

        new_charge_amps = min(charge_current_request_max, max(5, new_charge_amps))
        if new_charge_amps != charge_amps:
            print(" |", end=" ")
            self.tesla.set_charging_amps(new_charge_amps)
            print(f"⚡→{new_charge_amps}A")
        else:
            print("")

    def loop(self):
        while True:
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
                elif e.response.status_code == 401:
                    print("🚗 HTTP 401 Unauthorized: Getting new access token")
                    self.tesla.get_new_access_token()
                else:
                    print(str(e))
            except requests.exceptions.ConnectionError as e:
                print(str(e))
            time.sleep(self.sleep_time)


if __name__ == '__main__':
    from config import *
    solartesla = SolarExcessCharger(SOLAREDGE_SITE, SOLAREDGE_KEY, TESLA_ID, TESLA_REFRESH_TOKEN, home=(HOME_LATITUDE, HOME_LONGITUDE))
    solartesla.loop()
