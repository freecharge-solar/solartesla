import json
from main import TeslaAPI, TeslaAuth
from config import TESLA_ID, TESLA_VIN, TESLA_CLIENT_ID, TESLA_CLIENT_SECRET

tesla_auth = TeslaAuth(TESLA_CLIENT_ID, TESLA_CLIENT_SECRET)

tls = TeslaAPI(TESLA_ID, TESLA_VIN, tesla_auth)
vehicle_data = tls.get_vehicle_data()
print(json.dumps(vehicle_data, indent=1))
