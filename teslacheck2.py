import json
from main2 import TeslaBLE

tesla_ble = TeslaBLE()

p = tesla_ble.state_charge()

if p.returncode == 0:
    json_response = json.loads(p.stdout)
    print(json.dumps(json_response, indent=4))
