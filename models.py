"""Shared models, theme, global state, and alarm helpers."""

import random, math, collections
from datetime import datetime, timedelta
import flet as ft

C = {
    "bg":        "#0b0e13",
    "panel":     "#12171f",
    "card":      "#171d27",
    "card2":     "#1c2333",
    "border":    "#1f2d3d",
    "teal":      "#00d4b4",
    "teal_dim":  "#00d4b420",
    "blue":      "#3b82f6",
    "amber":     "#f59e0b",
    "red":       "#ef4444",
    "green":     "#22c55e",
    "purple":    "#a855f7",
    "white":     "#e8edf5",
    "gray":      "#64748b",
    "gray2":     "#334155",
    "header":    "#0e1420",
}

STATUS_COLOR = {"OK": C["green"], "WARN": C["amber"], "FAULT": C["red"], "CRITICAL": C["red"]}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  SIMULATED SENSOR ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
HISTORY_LEN = 60   # data-points kept per sensor
HISTORY_LONG_LEN = 600  # long trend for per-sensor detail page

class Sensor:
    def __init__(self, name, unit, low, high, warn_lo, warn_hi,
                 initial, noise, drift_speed, color, tau_s=4.0, max_delta_s=None):
        self.name        = name
        self.unit        = unit
        self.low         = low
        self.high        = high
        self.warn_lo     = warn_lo
        self.warn_hi     = warn_hi
        self.value       = float(initial)
        self.noise       = noise
        self.drift_speed = drift_speed
        self.color       = color
        self.tau_s       = max(0.2, float(tau_s))
        span = max(abs(self.high - self.low), 1e-6)
        default_rate = span * 0.025
        self.max_delta_s = float(max_delta_s) if max_delta_s is not None else default_rate
        self._target     = float(initial)
        self.history     = collections.deque(
            [float(initial)] * HISTORY_LEN, maxlen=HISTORY_LEN
        )
        self.history_long = collections.deque(
            [float(initial)] * HISTORY_LONG_LEN, maxlen=HISTORY_LONG_LEN
        )
        self.min_seen = float(initial)
        self.max_seen = float(initial)
        self.sum_seen = float(initial)
        self.samples_seen = 1

    def tick(self, dt_s=1.0):
        dt = max(0.02, float(dt_s))
        status_before = self.status
        fault_mult = 1.8 if status_before != "OK" else 1.0

        # Drift process target with limited random walk.
        drift_step = self.drift_speed * dt * fault_mult
        self._target += random.uniform(-drift_step, drift_step)
        self._target = max(self.low * 0.9, min(self.high * 1.1, self._target))

        # First-order lag dynamics (inertia) toward target.
        alpha = 1.0 - math.exp(-dt / self.tau_s)
        proposed = self.value + (self._target - self.value) * alpha

        # Small measurement/process noise; scaled by sqrt(dt).
        proposed += random.gauss(0.0, self.noise * math.sqrt(dt))

        # Rate limiter avoids non-physical jumps between consecutive updates.
        max_step = max(1e-6, self.max_delta_s * dt * fault_mult)
        delta = proposed - self.value
        if delta > max_step:
            delta = max_step
        elif delta < -max_step:
            delta = -max_step
        self.value += delta
        self.value = max(self.low * 0.85, min(self.high * 1.15, self.value))
        self.history.append(self.value)
        self.history_long.append(self.value)
        self.min_seen = min(self.min_seen, self.value)
        self.max_seen = max(self.max_seen, self.value)
        self.sum_seen += self.value
        self.samples_seen += 1

    @property
    def status(self):
        v = self.value
        if v < self.warn_lo or v > self.warn_hi:
            return "FAULT" if (v < self.low or v > self.high) else "WARN"
        return "OK"

    @property
    def pct(self):
        return max(0.0, min(1.0, (self.value - self.low) / (self.high - self.low)))

    def fmt(self, decimals=1):
        return f"{self.value:.{decimals}f}"

    @property
    def avg_seen(self):
        return self.sum_seen / self.samples_seen if self.samples_seen else self.value


# Define the sensor fleet
SENSORS: dict[str, Sensor] = {
    "temp_1":    Sensor("Reactor Temp",     "Â°C",  0,   200, 20, 160,  85, 0.35, 0.22, C["red"],    tau_s=5.0,  max_delta_s=1.20),
    "temp_2":    Sensor("Coolant Temp",     "Â°C",  0,   120, 10,  90,  42, 0.25, 0.16, C["amber"],  tau_s=6.5,  max_delta_s=0.80),
    "temp_3":    Sensor("Exhaust Temp",     "Â°C",  0,   180, 15, 145,  76, 0.30, 0.20, C["red"],    tau_s=5.5,  max_delta_s=1.00),
    "pressure":  Sensor("Line Pressure",    "bar", 0,    12, 1,    9,  5.2, 0.03, 0.06, C["blue"],   tau_s=2.2,  max_delta_s=0.25),
    "pressure_2":Sensor("Reactor Pressure", "bar", 0,    18, 2,   14,  8.4, 0.04, 0.06, C["blue"],   tau_s=2.5,  max_delta_s=0.30),
    "pressure_3":Sensor("Feed Pressure",    "bar", 0,    10, 1,    8,  4.7, 0.03, 0.05, C["blue"],   tau_s=2.2,  max_delta_s=0.25),
    "pressure_4":Sensor("Purge Pressure",   "bar", 0,     8, 0.8,  6,  3.2, 0.025,0.04, C["blue"],   tau_s=2.0,  max_delta_s=0.20),
    "flow_in":   Sensor("Inlet Flow",       "L/m", 0,   500, 50, 420, 220, 1.00, 1.20, C["teal"],   tau_s=1.8,  max_delta_s=8.00),
    "flow_out":  Sensor("Outlet Flow",      "L/m", 0,   500, 50, 420, 215, 0.95, 1.05, C["purple"], tau_s=1.9,  max_delta_s=7.50),
    "flow_3":    Sensor("Recycle Flow",     "L/m", 0,   350, 40, 300, 132, 0.85, 0.90, C["teal"],   tau_s=2.1,  max_delta_s=6.00),
    "h2":        Sensor("Hydrogen (H2)",    "%",   0,     4, 0.1,  3.0, 0.82,0.008,0.006,C["amber"], tau_s=4.0,  max_delta_s=0.030),
    "oxygen":    Sensor("Oxygen",           "%",   0,    25, 18,  23.5,20.9,0.010,0.003,C["green"], tau_s=8.0,  max_delta_s=0.020),
    "humidity":  Sensor("Ambient Humidity", "%",   0,   100, 20,  80,  55, 0.12, 0.08, C["green"],  tau_s=9.0,  max_delta_s=0.25),
    "vibration": Sensor("Vibration",        "mm/s",0,    20, 0,   12,  3.5, 0.06, 0.07, C["amber"],  tau_s=3.5,  max_delta_s=0.25),
    "power":     Sensor("Power Draw",       "kW",  0,   150, 10, 120,  68, 0.35, 0.55, C["blue"],   tau_s=1.8,  max_delta_s=3.00),
    "ph":        Sensor("pH Level",         "pH",  0,    14, 6,    8,  7.1, 0.008,0.003,C["green"], tau_s=12.0, max_delta_s=0.020),
    "level":     Sensor("Tank Level",       "%",   0,   100, 10,  90,  72, 0.04, 0.02, C["teal"],   tau_s=28.0, max_delta_s=0.08),
}

ALARMS: collections.deque = collections.deque(maxlen=80)            # recent event feed
ALARM_HISTORY: collections.deque = collections.deque(maxlen=500)    # full lifecycle log
ACTIVE_ALARMS: dict[str, dict] = {}
_ALARM_SEQ = {"id": 0}


def _next_alarm_id():
    _ALARM_SEQ["id"] += 1
    return _ALARM_SEQ["id"]


def _alarm_severity(sensor: Sensor):
    if sensor.status == "WARN":
        return "WARN"
    if sensor.status == "FAULT":
        if sensor.value < sensor.low * 0.95 or sensor.value > sensor.high * 1.05:
            return "CRITICAL"
        return "FAULT"
    return "OK"


def _duration_text(seconds: float | None):
    if seconds is None:
        return "-"
    total = int(max(0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _severity_label(level: str):
    return {"WARN": "Warning", "FAULT": "Fault", "CRITICAL": "Critical", "OK": "Info"}.get(level, level)


ALM_COL = {
    "name": 190,
    "sev": 100,
    "raised": 145,
    "cleared": 145,
    "dur": 80,
    "status": 100,
}


def alarm_history_row(rec: dict):
    col = STATUS_COLOR.get(rec["severity"], C["gray"])
    raised = rec["raised_at"].strftime("%Y-%m-%d %H:%M:%S")
    cleared = rec["cleared_at"].strftime("%Y-%m-%d %H:%M:%S") if rec["cleared_at"] else "-"
    status_col = C["green"] if rec["status"] == "Resolved" else C["amber"]

    def pill(text: str, color: str):
        return ft.Container(
            content=ft.Text(text, color=color, size=10, weight=ft.FontWeight.W_700),
            bgcolor=color + "22",
            border_radius=4,
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border=ft.Border(
                left=ft.BorderSide(1, color + "55"),
                right=ft.BorderSide(1, color + "55"),
                top=ft.BorderSide(1, color + "55"),
                bottom=ft.BorderSide(1, color + "55"),
            ),
        )

    return ft.Row([
        ft.Container(width=3, height=26, bgcolor=col, border_radius=2),
        ft.Container(width=8),
        ft.Text(rec["name"], color=C["white"], size=11, width=ALM_COL["name"]),
        ft.Container(width=ALM_COL["sev"], alignment=ft.Alignment(0, 0),
                     content=pill(_severity_label(rec["severity"]), col)),
        ft.Text(raised, color=C["gray"], size=10, width=ALM_COL["raised"]),
        ft.Text(cleared, color=C["gray"], size=10, width=ALM_COL["cleared"]),
        ft.Container(width=ALM_COL["dur"], alignment=ft.Alignment(0, 0),
                     content=ft.Text(_duration_text(rec["duration_s"]), color=C["gray"], size=10)),
        ft.Container(width=ALM_COL["status"], alignment=ft.Alignment(0, 0),
                     content=pill(rec["status"], status_col)),
    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _raise_or_update_alarm(sensor_key: str, sensor: Sensor, now: datetime):
    sev = _alarm_severity(sensor)
    if sev == "OK":
        return
    active = ACTIVE_ALARMS.get(sensor_key)
    if active is None:
        rec = {
            "id": _next_alarm_id(),
            "name": f"{sensor.name} threshold breach",
            "type": sensor.name,
            "sensor_key": sensor_key,
            "severity": sev,
            "raised_at": now,
            "cleared_at": None,
            "duration_s": None,
            "status": "Active",
            "message": f"{sensor.name} {_severity_label(sev)} condition detected",
        }
        ACTIVE_ALARMS[sensor_key] = rec
        ALARM_HISTORY.appendleft(rec)
        ALARMS.appendleft({
            "time": now.strftime("%H:%M:%S"),
            "sensor": sensor.name,
            "level": sev,
            "msg": rec["message"],
        })
        return
    rank = {"WARN": 1, "FAULT": 2, "CRITICAL": 3}
    if rank.get(sev, 0) > rank.get(active["severity"], 0):
        active["severity"] = sev
        active["message"] = f"{sensor.name} escalated to {_severity_label(sev)}"
        ALARMS.appendleft({
            "time": now.strftime("%H:%M:%S"),
            "sensor": sensor.name,
            "level": sev,
            "msg": active["message"],
        })


def _resolve_alarm(sensor_key: str, sensor: Sensor, now: datetime):
    active = ACTIVE_ALARMS.pop(sensor_key, None)
    if active is None:
        return
    active["cleared_at"] = now
    active["duration_s"] = (now - active["raised_at"]).total_seconds()
    active["status"] = "Resolved"
    ALARMS.appendleft({
        "time": now.strftime("%H:%M:%S"),
        "sensor": sensor.name,
        "level": "OK",
        "msg": f"{sensor.name} resolved ({_duration_text(active['duration_s'])})",
    })


def _activate_system_alarm(alarm_key: str, name: str, severity: str, message: str, now: datetime):
    active = ACTIVE_ALARMS.get(alarm_key)
    if active is not None:
        return
    rec = {
        "id": _next_alarm_id(),
        "name": name,
        "type": "System",
        "sensor_key": alarm_key,
        "severity": severity,
        "raised_at": now,
        "cleared_at": None,
        "duration_s": None,
        "status": "Active",
        "message": message,
    }
    ACTIVE_ALARMS[alarm_key] = rec
    ALARM_HISTORY.appendleft(rec)
    ALARMS.appendleft({
        "time": now.strftime("%H:%M:%S"),
        "sensor": "System",
        "level": severity,
        "msg": message,
    })


def _resolve_system_alarm(alarm_key: str, message: str, now: datetime):
    active = ACTIVE_ALARMS.pop(alarm_key, None)
    if active is None:
        return
    active["cleared_at"] = now
    active["duration_s"] = (now - active["raised_at"]).total_seconds()
    active["status"] = "Resolved"
    ALARMS.appendleft({
        "time": now.strftime("%H:%M:%S"),
        "sensor": "System",
        "level": "OK",
        "msg": f"{message} ({_duration_text(active['duration_s'])})",
    })


def _gen_alarm_seed():
    """Seed historical alarm log with resolved events for realism."""
    for i in range(10):
        start = datetime.now() - timedelta(hours=random.randint(1, 24), minutes=random.randint(0, 59))
        dur = random.randint(90, 2200)
        end = start + timedelta(seconds=dur)
        s = random.choice(list(SENSORS.values()))
        lvl = random.choice(["WARN", "FAULT", "CRITICAL"])
        rec = {
            "id": _next_alarm_id(),
            "name": f"{s.name} threshold breach",
            "type": s.name,
            "sensor_key": "seed",
            "severity": lvl,
            "raised_at": start,
            "cleared_at": end,
            "duration_s": float(dur),
            "status": "Resolved",
            "message": f"{s.name} {_severity_label(lvl)} condition detected",
        }
        ALARM_HISTORY.appendleft(rec)
        if i < 5:
            ALARMS.appendleft({
                "time": end.strftime("%H:%M:%S"),
                "sensor": s.name,
                "level": lvl,
                "msg": rec["message"],
            })


_gen_alarm_seed()


def dashboard_metrics():
    temps = [SENSORS["temp_1"].value, SENSORS["temp_2"].value, SENSORS["temp_3"].value]
    pressures = [
        SENSORS["pressure"].value,
        SENSORS["pressure_2"].value,
        SENSORS["pressure_3"].value,
        SENSORS["pressure_4"].value,
    ]
    total_flow = SENSORS["flow_in"].value + SENSORS["flow_out"].value + SENSORS["flow_3"].value
    h2_rate = max(1.2, min(10.0, (total_flow * SENSORS["h2"].value) / 180.0))
    elec_eff = 52.0
    power_kw = h2_rate * 33.3 * (elec_eff / 100.0)
    return {
        "avg_temp": sum(temps) / len(temps),
        "avg_pressure": sum(pressures) / len(pressures),
        "total_flow": total_flow,
        "h2": SENSORS["h2"].value,
        "o2": SENSORS["oxygen"].value,
        "h2_rate": h2_rate,
        "power_kw": power_kw,
        "efficiency": elec_eff,
        "conv_eff": elec_eff + 4.5,
        "perf_ratio": (power_kw / 120.0) * 100.0,
    }


_m0 = dashboard_metrics()
DASH_HIST = {
    "avg_temp": collections.deque([_m0["avg_temp"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "avg_pressure": collections.deque([_m0["avg_pressure"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "total_flow": collections.deque([_m0["total_flow"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "h2": collections.deque([_m0["h2"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "o2": collections.deque([_m0["o2"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "power_kw": collections.deque([_m0["power_kw"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "h2_rate": collections.deque([_m0["h2_rate"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "efficiency": collections.deque([_m0["efficiency"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "conv_eff": collections.deque([_m0["conv_eff"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
    "perf_ratio": collections.deque([_m0["perf_ratio"]] * HISTORY_LEN, maxlen=HISTORY_LEN),
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  DRAWING HELPERS  (canvas-based, no external libs)

