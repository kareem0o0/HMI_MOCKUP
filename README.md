# Industrial Fuel Cell HMI (Mock SCADA) - `main.py`

This project is a Flet-based industrial HMI/SCADA-style interface for a fuel-cell system.
It uses fully simulated data and live UI updates to emulate real monitoring behavior.

## Current Features

## 1) Multi-Page HMI Interface
- Dashboard
- Sensors
- Analytics
- System
- Alarms (history/log)
- Network Settings (IoT connectivity mockup)

Navigation is available from the left sidebar, with alarm access also available from the top bar.

## 2) Real-Time Simulation Engine
- Continuous sensor updates (mock realistic ranges and drift/noise behavior)
- Rolling short and long history buffers
- Live KPI calculation and trend updates
- UI updates without manual refresh/navigation

## 3) Fuel-Cell Focused Dashboard
- Electricity generation KPIs:
  - Current power output (kW)
  - Total energy generated (kWh)
  - Voltage/current display
- Hydrogen usage and capacity:
  - Consumption rate
  - Remaining fuel (% and kg)
  - Runtime estimate
  - Two H2 tank ring indicators
- Efficiency and performance:
  - Electrical efficiency
  - Conversion efficiency
  - Performance ratio
- Health/status indicators:
  - Fuel-cell state
  - Stack health
  - Temperature stability
- Trend cards:
  - Separate cards for power, H2 rate, efficiency
  - Dedicated chart per metric with numeric Y-axis ticks

## 4) Sensors Monitoring
- Expanded sensor fleet:
  - Temperature sensors
  - Pressure sensors
  - Flow sensors
  - Hydrogen and Oxygen sensors
  - Additional environmental/auxiliary channels
- Card-based sensor widgets with live values and mini trends
- Clickable sensor cards leading to detailed sensor pages

## 5) Sensor Detail View
- Large live historical chart
- Current value
- Min / Max / Average tracked values
- Status (Normal/Warning/Fault)
- Past alarms related to selected sensor

## 6) Alarm Management System
- Threshold-based alarm generation from live sensor behavior
- Active and resolved alarm lifecycle tracking
- Alarm History Log includes:
  - Name/type
  - Severity
  - Raised and cleared timestamps
  - Duration
  - Active/Resolved status
- Alarm badge in top bar with active count
- Dynamically updating alarm feed/panel

## 7) Emergency Stop (E-STOP)
- Top-bar clickable E-STOP / RESET control
- On E-STOP:
  - Operations halt
  - Power/H2/efficiency outputs are forced to stopped state
  - Simulation status indicators switch to STOPPED
  - System-level critical alarm is added to alarm history
- On RESET:
  - Operations resume
  - E-STOP alarm is resolved with duration tracking

## 8) Network Settings Page (IoT)
- Dedicated network configuration page with:
  - Wi-Fi / Ethernet selection
  - SSID input
  - Masked password input
  - DHCP toggle
  - Static IP input (enabled when DHCP is off)
  - Connection status indicator (Connected/Connecting/Disconnected)
  - Dynamic IP display
  - Signal quality bar
  - Save/Apply button
- Mock connectivity state machine:
  - Connect attempts
  - Success/failure behavior
  - Signal fluctuation
  - Occasional link drops

## 9) UI/Design Notes
- Dark industrial HMI theme
- Card-based layout and consistent status color coding
- Live trends, badges, and visual indicators for operator readability

## Run

Use your existing Python/Flet setup and run:

```bash
python main.py
```

(If your environment uses `py`, run `py -3 main.py`.)

## Windows Desktop Build

This project is ready to package as a standalone Windows desktop app (no Python needed on client PC).

1. Build using the helper script:

```powershell
.\build_windows.ps1
```

2. Output artifacts:
- `build\desktop\FuelCellHMIDemo\FuelCellHMIDemo.exe` (standalone app folder)
- `build\FuelCellHMIDemo-win.zip` (ready-to-share zip for client)

You can also build directly with Flet:

```powershell
.\.venv\Scripts\flet.exe pack .\main.py -D -n FuelCellHMIDemo --distpath .\build\desktop -y
```

## Scope

This is currently a mock/simulation interface intended for UI, architecture, and workflow validation.
It is designed to be extendable for future integration with real PLC/DAQ/IoT backends.
