import json
from main2 import SolarEdgeMonitoring
from config import SOLAREDGE_SITE, SOLAREDGE_KEY, SOLAREDGE_COOKIE

solaredge = SolarEdgeMonitoring(SOLAREDGE_SITE, SOLAREDGE_KEY, SOLAREDGE_COOKIE)
print(json.dumps(solaredge.get_site_currentPowerFlow(), indent=1))
