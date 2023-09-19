# solartesla
Charge your Tesla for free using excess solar

# Supported hardware

## Cars

* Tesla Model Y
* Tesla Model 3

## Solar inverters

* SolarEdge

# Config
Configure your Tesla and SolarEdge tokens in `config.py` starting from the sample:

```
cp config.py.sample config.py
```

# Example log

```
2023-09-19T10:59:06 | ☀️37.87A +2.22A | 🔋79%/416km ⚡Charging 32/32/32A 80% 7kW 227V (1) +2.76kWh/19km 10m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T10:59:27 | ☀️37.83A +2.17A | 🔋79%/416km ⚡Charging 32/32/32A 80% 7kW 228V (1) +2.74kWh/19km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T10:59:48 | ☀️37.87A +2.35A | 🔋79%/417km ⚡Charging 32/32/32A 80% 7kW 229V (1) +2.89kWh/19km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:00:09 | ☀️37.91A +2.26A | 🔋79%/417km ⚡Charging 32/32/32A 80% 7kW 227V (1) +2.89kWh/19km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:00:30 | ☀️37.78A +2.35A | 🔋79%/417km ⚡Charging 32/32/32A 80% 7kW 228V (1) +2.89kWh/19km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:00:51 | ☀️37.87A +2.22A | 🔋79%/418km ⚡Charging 32/32/32A 80% 7kW 227V (1) +3.02kWh/20km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:01:12 | ☀️37.83A +2.26A | 🔋79%/418km ⚡Charging 32/32/32A 80% 7kW 227V (1) +3.02kWh/20km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:01:33 | ☀️37.91A -2.00A | 🔋79%/418km ⚡Charging 33/32/32A 80% 7kW 228V (1) +3.02kWh/20km 5m | 🏠True | 🎯31A | 🎯>0A 🆗 | ⚡→31A
2023-09-19T11:01:54 | ☀️37.70A +0.74A | 🔋79%/418km ⚡Charging 31/31/32A 80% 7kW 227V (1) +3.14kWh/21km 5m | 🏠True | 🎯31A | 🎯>0A 🆗
2023-09-19T11:02:16 | ☀️37.83A +3.00A | 🔋79%/418km ⚡Charging 31/31/32A 80% 7kW 229V (1) +3.14kWh/21km 5m | 🏠True | 🎯34A | 🎯>0A 🆗 | ⚡→32A
2023-09-19T11:02:37 | ☀️37.91A +0.74A | 🔋79%/418km ⚡Charging 32/32/32A 80% 7kW 227V (1) +3.14kWh/21km 5m | 🏠True | 🎯32A | 🎯>0A 🆗
2023-09-19T11:02:58 | ☀️37.87A +2.43A | 🔋79%/419km ⚡Charging 32/32/32A 80% 7kW 228V (1) +3.27kWh/22km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:03:19 | ☀️37.87A +2.30A | 🔋79%/419km ⚡Charging 32/32/32A 80% 7kW 228V (1) +3.29kWh/22km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:03:40 | ☀️38.09A +2.43A | 🔋79%/419km ⚡Charging 32/32/32A 80% 7kW 227V (1) +3.29kWh/22km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:04:01 | ☀️38.09A +2.35A | 🔋79%/419km ⚡Charging 32/32/32A 80% 7kW 228V (1) +3.29kWh/22km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:04:22 | ☀️38.13A +2.57A | 🔋79%/420km ⚡Charging 32/32/32A 80% 7kW 226V (1) +3.41kWh/23km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:04:43 | ☀️38.17A +2.61A | 🔋79%/420km ⚡Charging 32/32/32A 80% 7kW 227V (1) +3.41kWh/23km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:05:04 | ☀️38.13A +2.52A | 🔋79%/420km ⚡Charging 32/32/32A 80% 7kW 228V (1) +3.41kWh/23km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:05:25 | ☀️38.22A +2.57A | 🔋79%/420km ⚡Charging 32/32/32A 80% 7kW 228V (1) +3.54kWh/23km 5m | 🏠True | 🎯34A | 🎯>0A 🆗
2023-09-19T11:05:46 | ☀️38.13A -4.17A | 🔋79%/420km ⚡Charging 32/32/32A 80% 7kW 226V (1) +3.54kWh/23km 5m | 🏠True | 🎯27A | 🎯>0A 🆗 | ⚡→27A
2023-09-19T11:06:08 | ☀️38.00A +0.00A | 🔋79%/420km ⚡Charging 27/27/32A 80% 6kW 228V (1) +3.54kWh/23km 5m | 🏠True | 🎯27A | 🎯>0A 🆗
2023-09-19T11:06:49 | ☀️38.09A +32.04A | 🔋80%/422km ⚡Complete 0/27/32A 80% | 🏠True | SKIP ∵ ⚡Complete
2023-09-19T11:07:10 | ☀️38.09A +32.00A | 🔋80%/422km ⚡Complete 0/27/32A 80% | 🏠True | SKIP ∵ ⚡Complete
```
