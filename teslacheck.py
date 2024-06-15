from main import *
from config import *

tls = TeslaAPI(TESLA_ID, TESLA_REFRESH_TOKEN)
tls.wake_up()
vehicle_data = tls.get_vehicle_data()
print(json.dumps(vehicle_data, indent=1))
# tls.honk_horn()
