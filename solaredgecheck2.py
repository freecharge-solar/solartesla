from main2 import *
from config import *

solaredge = SolarEdgeMonitoring(SOLAREDGE_SITE, SOLAREDGE_KEY, SOLAREDGE_COOKIE)
print(json.dumps(solaredge.get_site_details(), indent=1))
print(json.dumps(solaredge.get_site_inventory(), indent=1))
print(json.dumps(solaredge.get_site_overview(), indent=1))
print(json.dumps(solaredge.get_site_currentPowerFlow(), indent=1))
