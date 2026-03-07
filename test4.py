"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘         INDUSTRIAL HMI DASHBOARD  â€”  Full Prototype         â•‘
â•‘         Flet 0.80+   |   Pure Python   |   Mock Data        â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Pages:
  1. Dashboard   â€” live KPI overview + mini trend lines
  2. Sensors     â€” all sensor readings with status indicators
  3. Analytics   â€” historical plots (line + bar charts)
  4. System      â€” system health, alarms log, device status

Run:  python hmi_dashboard.py
"""

import flet as ft
import flet.canvas as cv
import asyncio
import random, math, collections
from datetime import datetime, timedelta

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  THEME
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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
                 initial, noise, drift_speed, color):
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

    def tick(self):
        # slowly drift target, then add noise
        self._target += random.uniform(-self.drift_speed, self.drift_speed)
        self._target  = max(self.low * 0.9, min(self.high * 1.1, self._target))
        self.value    = self._target + random.gauss(0, self.noise)
        self.value    = max(self.low * 0.85, min(self.high * 1.15, self.value))
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
    "temp_1":    Sensor("Reactor Temp",     "Â°C",  0,   200, 20, 160,  85,  1.2, 0.8, C["red"]),
    "temp_2":    Sensor("Coolant Temp",     "Â°C",  0,   120, 10,  90,  42,  0.8, 0.5, C["amber"]),
    "temp_3":    Sensor("Exhaust Temp",     "Â°C",  0,   180, 15, 145,  76,  1.0, 0.7, C["red"]),
    "pressure":  Sensor("Line Pressure",    "bar", 0,    12, 1,    9,  5.2, 0.15,0.1, C["blue"]),
    "pressure_2":Sensor("Reactor Pressure", "bar", 0,    18, 2,   14,  8.4, 0.18,0.1, C["blue"]),
    "pressure_3":Sensor("Feed Pressure",    "bar", 0,    10, 1,    8,  4.7, 0.13,0.1, C["blue"]),
    "pressure_4":Sensor("Purge Pressure",   "bar", 0,     8, 0.8,  6,  3.2, 0.12,0.08,C["blue"]),
    "flow_in":   Sensor("Inlet Flow",       "L/m", 0,   500, 50, 420, 220,  4.0, 3.0, C["teal"]),
    "flow_out":  Sensor("Outlet Flow",      "L/m", 0,   500, 50, 420, 215,  3.8, 2.8, C["purple"]),
    "flow_3":    Sensor("Recycle Flow",     "L/m", 0,   350, 40, 300, 132,  3.3, 2.2, C["teal"]),
    "h2":        Sensor("Hydrogen (H2)",    "%",   0,     4, 0.1,  3.0, 0.82,0.04,0.02,C["amber"]),
    "oxygen":    Sensor("Oxygen",           "%",   0,    25, 18,  23.5,20.9,0.08,0.05,C["green"]),
    "humidity":  Sensor("Ambient Humidity", "%",   0,   100, 20,  80,  55,  0.5, 0.3, C["green"]),
    "vibration": Sensor("Vibration",        "mm/s",0,    20, 0,   12,  3.5, 0.3, 0.2, C["amber"]),
    "power":     Sensor("Power Draw",       "kW",  0,   150, 10, 120,  68,  1.5, 1.0, C["blue"]),
    "ph":        Sensor("pH Level",         "pH",  0,    14, 6,    8,  7.1, 0.05,0.03,C["green"]),
    "level":     Sensor("Tank Level",       "%",   0,   100, 10,  90,  72,  0.4, 0.5, C["teal"]),
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
    return ft.Row([
        ft.Container(width=3, height=26, bgcolor=col, border_radius=2),
        ft.Container(width=8),
        ft.Text(rec["name"], color=C["white"], size=11, width=ALM_COL["name"]),
        ft.Container(width=ALM_COL["sev"], alignment=ft.Alignment(0, 0),
                     content=badge(_severity_label(rec["severity"]), col)),
        ft.Text(raised, color=C["gray"], size=10, width=ALM_COL["raised"]),
        ft.Text(cleared, color=C["gray"], size=10, width=ALM_COL["cleared"]),
        ft.Container(width=ALM_COL["dur"], alignment=ft.Alignment(0, 0),
                     content=ft.Text(_duration_text(rec["duration_s"]), color=C["gray"], size=10)),
        ft.Container(width=ALM_COL["status"], alignment=ft.Alignment(0, 0),
                     content=badge(rec["status"], status_col)),
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
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  DRAWING HELPERS  (canvas-based, no external libs)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def draw_arc(value: float, size=170, stroke=12,
             label="", unit="", label_size=36, color=C["teal"]):
    start   = math.pi * 0.75
    sweep_f = math.pi * 1.5
    sweep_v = sweep_f * max(0.0, min(1.0, value))
    pad     = stroke + 2
    d       = size - pad * 2
    shapes  = [
        cv.Arc(x=pad, y=pad, width=d, height=d,
               start_angle=start, sweep_angle=sweep_f,
               paint=ft.Paint(style=ft.PaintingStyle.STROKE,
                              stroke_width=stroke, color=C["gray2"],
                              stroke_cap=ft.StrokeCap.ROUND)),
    ]
    if sweep_v > 0.01:
        shapes.append(cv.Arc(x=pad, y=pad, width=d, height=d,
                             start_angle=start, sweep_angle=sweep_v,
                             paint=ft.Paint(style=ft.PaintingStyle.STROKE,
                                            stroke_width=stroke, color=color,
                                            stroke_cap=ft.StrokeCap.ROUND)))
    canvas  = cv.Canvas(shapes=shapes, width=size, height=size)
    overlay = ft.Container(
        width=size, height=size,
        alignment=ft.Alignment(0, 0),
        content=ft.Column([
            ft.Text(label, color=C["white"], size=label_size,
                    weight=ft.FontWeight.BOLD),
            ft.Text(unit,  color=C["gray"],  size=int(label_size * 0.36)),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER, spacing=0),
    )
    return ft.Stack([canvas, overlay], width=size, height=size)


def draw_spark(history, w=160, h=50, color=C["teal"]):
    """Mini sparkline from a deque of values."""
    vals = list(history)
    if len(vals) < 2:
        return cv.Canvas(width=w, height=h)
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n   = len(vals)
    dx  = w / (n - 1)

    def px(i, v):
        x = i * dx
        y = h - ((v - lo) / rng) * (h - 4) - 2
        return x, y

    shapes = []
    # fill area
    pts_top  = [px(i, v) for i, v in enumerate(vals)]
    pts_fill = pts_top + [(w, h), (0, h)]
    shapes.append(cv.Path(
        elements=[cv.Path.MoveTo(*pts_fill[0])] +
                 [cv.Path.LineTo(x, y) for x, y in pts_fill[1:]],
        paint=ft.Paint(color=color + "22", style=ft.PaintingStyle.FILL),
    ))
    # line
    shapes.append(cv.Path(
        elements=[cv.Path.MoveTo(*pts_top[0])] +
                 [cv.Path.LineTo(x, y) for x, y in pts_top[1:]],
        paint=ft.Paint(color=color, style=ft.PaintingStyle.STROKE,
                       stroke_width=1.8, stroke_cap=ft.StrokeCap.ROUND,
                       stroke_join=ft.StrokeJoin.ROUND),
    ))
    return cv.Canvas(shapes=shapes, width=w, height=h)


def draw_bar_chart(series: list[tuple[str, float, str]],
                   w=340, h=160):
    """series = [(label, value_0_to_1, color), ...]"""
    n     = len(series)
    gap   = 8
    bar_w = (w - gap * (n + 1)) / n
    shapes = []
    for i, (lbl, v, col) in enumerate(series):
        bh = max(4.0, (h - 24) * v)
        x  = gap + i * (bar_w + gap)
        y  = h - 24 - bh
        shapes.append(cv.Rect(x=x, y=y, width=bar_w, height=bh,
                              border_radius=3,
                              paint=ft.Paint(color=col + "cc")))
        shapes.append(cv.Rect(x=x, y=y, width=bar_w, height=3,
                              border_radius=2,
                              paint=ft.Paint(color=col)))
    return cv.Canvas(shapes=shapes, width=w, height=h)


def draw_line_chart(histories: list[tuple, str], w=500, h=160):
    """histories = [(deque_of_values, color), ...]"""
    shapes = []
    # grid lines
    for i in range(1, 4):
        y = h * i / 4
        shapes.append(cv.Line(x1=0, y1=y, x2=w, y2=y,
                              paint=ft.Paint(color=C["gray2"], stroke_width=0.5)))

    for history, color in histories:
        vals = list(history)
        if len(vals) < 2:
            continue
        all_vals = vals
        lo, hi = min(all_vals), max(all_vals)
        rng = (hi - lo) or 1.0
        n   = len(vals)
        dx  = w / max(n - 1, 1)

        def px(i, v):
            x = i * dx
            y = h - ((v - lo) / rng) * (h - 6) - 3
            return x, y

        pts = [px(i, v) for i, v in enumerate(vals)]
        shapes.append(cv.Path(
            elements=[cv.Path.MoveTo(*pts[0])] +
                     [cv.Path.LineTo(x, y) for x, y in pts[1:]],
            paint=ft.Paint(color=color, style=ft.PaintingStyle.STROKE,
                           stroke_width=2, stroke_cap=ft.StrokeCap.ROUND,
                           stroke_join=ft.StrokeJoin.ROUND),
        ))
    return cv.Canvas(shapes=shapes, width=w, height=h)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  UI PRIMITIVES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def card(content, padding=14, expand=False, height=None):
    kw = dict(content=content, bgcolor=C["card"], border_radius=10,
               padding=padding, expand=expand,
               border=ft.Border(
                   left=ft.BorderSide(1, C["border"]),
                   right=ft.BorderSide(1, C["border"]),
                   top=ft.BorderSide(1, C["border"]),
                   bottom=ft.BorderSide(1, C["border"]),
               ))
    if height: kw["height"] = height
    return ft.Container(**kw)


def hdr(icon_name, title, subtitle=""):
    row = [ft.Icon(getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                   color=C["teal"], size=15),
           ft.Text(title, color=C["white"], size=13,
                   weight=ft.FontWeight.W_600)]
    if subtitle:
        row.append(ft.Text(subtitle, color=C["gray"], size=11))
    return ft.Row(row, spacing=6)


def badge(text, color):
    return ft.Container(
        content=ft.Text(text, color=color, size=10,
                        weight=ft.FontWeight.W_700),
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


def nav_btn(label, icon_name, active, on_click):
    col  = C["teal"] if active else C["gray"]
    bg   = C["teal_dim"] if active else "transparent"
    return ft.Container(
        content=ft.Column([
            ft.Icon(getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                    color=col, size=20),
            ft.Text(label, color=col, size=10,
                    weight=ft.FontWeight.W_600 if active else ft.FontWeight.NORMAL),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER, spacing=3),
        width=72, height=64,
        bgcolor=bg,
        border_radius=8,
        alignment=ft.Alignment(0, 0),
        ink=True,
        on_click=on_click,
    )


def divider():
    return ft.Container(height=1, bgcolor=C["border"])


def value_row(label, value_ref, unit, color=C["white"], val_size=22):
    return ft.Row([
        ft.Column([
            ft.Text(label, color=C["gray"], size=11),
            ft.Row([
                ft.Text("â€”", ref=value_ref, color=color,
                        size=val_size, weight=ft.FontWeight.BOLD),
                ft.Text(unit, color=C["gray"], size=11),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
        ], spacing=2),
    ])


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  PAGE BUILDERS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€ PAGE 1: Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_sensor_panel(refs: dict, on_sensor_click=None):
    """
    Top row: 4 KPI tiles (temp, pressure, flow, power)
    Middle:  big production arc + 2 trend lines
    Bottom:  alarm strip
    """

    def kpi_tile(sensor_key, icon_name):
        s = SENSORS[sensor_key]
        v_ref  = ft.Ref[ft.Text]()
        st_ref = ft.Ref[ft.Container]()
        sp_ref = ft.Ref[cv.Canvas]()
        refs[f"kpi_{sensor_key}_val"]    = v_ref
        refs[f"kpi_{sensor_key}_status"] = st_ref
        refs[f"kpi_{sensor_key}_spark"]  = sp_ref

        tile = card(ft.Column([
            ft.Row([
                ft.Icon(getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                        color=s.color, size=18),
                ft.Text(s.name, color=C["gray"], size=11, expand=True),
                ft.Container(
                    ref=st_ref,
                    width=8, height=8, border_radius=4,
                    bgcolor=STATUS_COLOR[s.status],
                ),
            ], spacing=6),
            ft.Container(height=6),
            ft.Row([
                ft.Text(s.fmt(), ref=v_ref, color=C["white"],
                        size=26, weight=ft.FontWeight.BOLD),
                ft.Text(s.unit, color=C["gray"], size=12),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
            ft.Container(height=8),
            ft.Row([draw_spark(s.history, w=140, h=38, color=s.color)],
                   ref=sp_ref),
        ], spacing=0), expand=True)
        if on_sensor_click:
            tile.ink = True
            tile.on_click = lambda e, key=sensor_key: on_sensor_click(key)
        return tile

    kpi_row = ft.Row([
        kpi_tile("temp_1",   "THERMOSTAT"),
        kpi_tile("pressure", "COMPRESS"),
        kpi_tile("flow_in",  "WATER_DROP"),
        kpi_tile("power",    "BOLT"),
    ], spacing=12, expand=False)
    def aux_sensor_tile(sensor_key, icon_name):
        s = SENSORS[sensor_key]
        v_ref = ft.Ref[ft.Text]()
        st_ref = ft.Ref[ft.Container]()
        sp_ref = ft.Ref[cv.Canvas]()
        refs[f"aux_{sensor_key}_val"] = v_ref
        refs[f"aux_{sensor_key}_status"] = st_ref
        refs[f"aux_{sensor_key}_spark"] = sp_ref

        tile = card(ft.Column([
            ft.Row([
                ft.Icon(getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                        color=s.color, size=16),
                ft.Text(s.name, color=C["gray"], size=11, expand=True),
                ft.Container(
                    ref=st_ref,
                    width=8, height=8, border_radius=4,
                    bgcolor=STATUS_COLOR[s.status],
                ),
            ], spacing=6),
            ft.Container(height=6),
            ft.Row([
                ft.Text(s.fmt(), ref=v_ref, color=C["white"],
                        size=22, weight=ft.FontWeight.BOLD),
                ft.Text(s.unit, color=C["gray"], size=11),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
            ft.Container(height=6),
            ft.Row([draw_spark(s.history, w=140, h=34, color=s.color)],
                   ref=sp_ref),
        ], spacing=0), expand=True)
        if on_sensor_click:
            tile.ink = True
            tile.on_click = lambda e, key=sensor_key: on_sensor_click(key)
        return tile

    aux_specs = [
        ("temp_2", "THERMOSTAT"),
        ("temp_3", "DEVICE_THERMOSTAT"),
        ("pressure_2", "COMPRESS"),
        ("pressure_3", "SPEED"),
        ("pressure_4", "AIR"),
        ("flow_out", "WATER_DROP"),
        ("flow_3", "WAVES"),
        ("h2", "SCIENCE"),
        ("oxygen", "AIR"),
    ]
    aux_tiles = [aux_sensor_tile(key, icon_name) for key, icon_name in aux_specs]
    aux_rows = []
    per_row = 3
    for i in range(0, len(aux_tiles), per_row):
        aux_rows.append(ft.Row(aux_tiles[i:i+per_row], spacing=12, expand=False))

    aux_grid = ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.HUB, color=C["teal"], size=16),
            ft.Text("Additional Process Sensors", color=C["white"], size=13,
                    weight=ft.FontWeight.W_600),
        ], spacing=6),
        ft.Container(height=8),
        *aux_rows,
    ], spacing=0)

    # Centre: arc gauge + two sparklines
    arc_ref  = ft.Ref[ft.Row]()
    lc_ref   = ft.Ref[ft.Row]()
    refs["dash_arc_row"]      = arc_ref
    refs["dash_linechart_row"] = lc_ref

    arc_card = card(ft.Column([
        hdr("FACTORY", "Production Overview"),
        ft.Container(height=10),
        ft.Row([draw_arc(SENSORS["level"].pct,
                         label=SENSORS["level"].fmt(0),
                         unit=SENSORS["level"].unit,
                         color=C["teal"])],
               ref=arc_ref,
               alignment=ft.MainAxisAlignment.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), expand=True)

    trend_card = card(ft.Column([
        hdr("SHOW_CHART", "Temp & Pressure Trend",
            f"last {HISTORY_LEN}s"),
        ft.Container(height=8),
        ft.Row([
            ft.Container(width=10, height=10,
                         bgcolor=C["red"], border_radius=2),
            ft.Text("Reactor Temp", color=C["gray"], size=11),
            ft.Container(width=10),
            ft.Container(width=10, height=10,
                         bgcolor=C["blue"], border_radius=2),
            ft.Text("Line Pressure (Ã—20)", color=C["gray"], size=11),
        ], spacing=4),
        ft.Container(height=8),
        ft.Row([draw_line_chart([
                    (SENSORS["temp_1"].history,   C["red"]),
                    (collections.deque(
                        [v * 20 for v in SENSORS["pressure"].history],
                        maxlen=HISTORY_LEN), C["blue"]),
                ], w=440, h=150)],
               ref=lc_ref,
               alignment=ft.MainAxisAlignment.CENTER),
    ]), expand=True)

    mid_row = ft.Row([arc_card, trend_card], spacing=12, expand=True,
                     vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    # Alarm strip
    alarm_col_ref = ft.Ref[ft.Column]()
    refs["dash_alarm_col"] = alarm_col_ref

    def alarm_row(a):
        col = STATUS_COLOR[a["level"]]
        return ft.Row([
            ft.Container(width=3, height=28, bgcolor=col, border_radius=2),
            ft.Container(width=8),
            ft.Text(a["time"], color=C["gray"], size=11, width=60),
            badge(a["level"], col),
            ft.Container(width=8),
            ft.Text(a["msg"], color=C["white"], size=12, expand=True),
        ], spacing=0)

    alarm_items = [alarm_row(a) for a in list(ALARMS)[:4]]

    alarm_card = card(ft.Column([
        hdr("NOTIFICATIONS_ACTIVE", "Recent Alarms"),
        ft.Container(height=8),
        ft.Column(alarm_items, ref=alarm_col_ref, spacing=6),
    ]))

    return ft.Column([
        kpi_row,
        ft.Container(height=12),
        aux_grid,
        ft.Container(height=12),
        mid_row,
        ft.Container(height=12),
        alarm_card,
    ], spacing=0, expand=True)


def build_sensor_detail(refs: dict, sensor_key: str, on_back):
    s = SENSORS[sensor_key]
    val_ref = ft.Ref[ft.Text]()
    st_dot_ref = ft.Ref[ft.Container]()
    st_txt_ref = ft.Ref[ft.Text]()
    min_ref = ft.Ref[ft.Text]()
    max_ref = ft.Ref[ft.Text]()
    avg_ref = ft.Ref[ft.Text]()
    plot_ref = ft.Ref[ft.Row]()
    alarm_ref = ft.Ref[ft.Column]()

    refs["sd_sensor_key"] = sensor_key
    refs["sd_val"] = val_ref
    refs["sd_st_dot"] = st_dot_ref
    refs["sd_st_txt"] = st_txt_ref
    refs["sd_min"] = min_ref
    refs["sd_max"] = max_ref
    refs["sd_avg"] = avg_ref
    refs["sd_plot"] = plot_ref
    refs["sd_alarm_col"] = alarm_ref

    def alarm_rows():
        rows = []
        for a in [x for x in ALARMS if x["sensor"] == s.name][:12]:
            col = STATUS_COLOR[a["level"]]
            rows.append(ft.Row([
                ft.Container(width=3, height=22, bgcolor=col, border_radius=2),
                ft.Container(width=8),
                ft.Text(a["time"], color=C["gray"], size=11, width=70),
                badge(a["level"], col),
                ft.Container(width=8),
                ft.Text(a["msg"], color=C["white"], size=11, expand=True),
            ], spacing=0))
        if not rows:
            rows.append(ft.Text("No alarms recorded for this sensor.", color=C["gray"], size=11))
        return rows

    return ft.Column([
        ft.Row([
            ft.TextButton(
                "Back to Sensors",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: on_back(),
            ),
            ft.Container(expand=True),
            badge(s.status, STATUS_COLOR[s.status]),
        ]),
        ft.Container(height=8),
        card(ft.Column([
            hdr("SENSORS", f"{s.name} Detailed View", f"unit: {s.unit}"),
            ft.Container(height=10),
            ft.Row([
                ft.Column([
                    ft.Text("Current Value", color=C["gray"], size=11),
                    ft.Row([
                        ft.Text(s.fmt(), ref=val_ref, color=s.color, size=34,
                                weight=ft.FontWeight.BOLD),
                        ft.Text(s.unit, color=C["gray"], size=14),
                    ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=6),
                ]),
                ft.Container(expand=True),
                ft.Column([
                    ft.Row([
                        ft.Container(width=9, height=9, border_radius=5, ref=st_dot_ref,
                                     bgcolor=STATUS_COLOR[s.status]),
                        ft.Text(s.status, ref=st_txt_ref, color=STATUS_COLOR[s.status], size=12,
                                weight=ft.FontWeight.W_700),
                    ], spacing=6),
                    ft.Container(height=8),
                    ft.Text("Min Recorded", color=C["gray"], size=10),
                    ft.Text(f"{s.min_seen:.2f}", ref=min_ref, color=C["white"], size=12),
                    ft.Text("Max Recorded", color=C["gray"], size=10),
                    ft.Text(f"{s.max_seen:.2f}", ref=max_ref, color=C["white"], size=12),
                    ft.Text("Average", color=C["gray"], size=10),
                    ft.Text(f"{s.avg_seen:.2f}", ref=avg_ref, color=C["white"], size=12),
                ], horizontal_alignment=ft.CrossAxisAlignment.END),
            ]),
            ft.Container(height=14),
            hdr("SHOW_CHART", "Historical Trend"),
            ft.Container(height=8),
            ft.Row([
                draw_line_chart([(s.history_long, s.color)], w=920, h=260)
            ], ref=plot_ref, alignment=ft.MainAxisAlignment.CENTER),
        ]), expand=True),
        ft.Container(height=12),
        card(ft.Column([
            hdr("NOTIFICATIONS_ACTIVE", "Past Alarms (with timing)"),
            ft.Container(height=8),
            ft.Column(alarm_rows(), ref=alarm_ref, spacing=6),
        ]), expand=True),
    ], spacing=0, expand=True)


def build_dashboard(refs: dict):
    def status_chip(ref_prefix, label, default_text="ACTIVE", default_color=C["green"]):
        txt_ref = ft.Ref[ft.Text]()
        dot_ref = ft.Ref[ft.Container]()
        refs[f"db_st_{ref_prefix}_txt"] = txt_ref
        refs[f"db_st_{ref_prefix}_dot"] = dot_ref
        return ft.Row([
            ft.Text(label, color=C["gray"], size=11, width=170),
            ft.Container(width=8, height=8, border_radius=4, bgcolor=default_color, ref=dot_ref),
            ft.Text(default_text, color=default_color, size=11, weight=ft.FontWeight.W_700, ref=txt_ref),
        ], spacing=6)

    # Electricity generation overview
    pwr_ref = ft.Ref[ft.Text]()
    energy_ref = ft.Ref[ft.Text]()
    volt_ref = ft.Ref[ft.Text]()
    curr_ref = ft.Ref[ft.Text]()
    pwr_sp_ref = ft.Ref[ft.Row]()
    refs["db_fc_power_kw"] = pwr_ref
    refs["db_fc_energy_kwh"] = energy_ref
    refs["db_fc_voltage"] = volt_ref
    refs["db_fc_current"] = curr_ref
    refs["db_fc_power_sp"] = pwr_sp_ref

    power_card = card(ft.Column([
        hdr("BOLT", "Electricity Generation Overview"),
        ft.Container(height=8),
        ft.Row([
            ft.Column([
                ft.Text("Current Power Output", color=C["gray"], size=11),
                ft.Row([
                    ft.Text("-", ref=pwr_ref, color=C["white"], size=30, weight=ft.FontWeight.BOLD),
                    ft.Text("kW", color=C["gray"], size=12),
                ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
            ]),
            ft.Container(expand=True),
            ft.Column([
                ft.Text("Total Energy Generated", color=C["gray"], size=11),
                ft.Row([
                    ft.Text("-", ref=energy_ref, color=C["amber"], size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("kWh", color=C["gray"], size=11),
                ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
                ft.Text("", ref=volt_ref, color=C["gray"], size=11),
                ft.Text("", ref=curr_ref, color=C["gray"], size=11),
            ], horizontal_alignment=ft.CrossAxisAlignment.END),
        ]),
        ft.Container(height=8),
        ft.Row([draw_spark(DASH_HIST["power_kw"], w=320, h=44, color=C["teal"])],
               ref=pwr_sp_ref),
    ]), expand=True)

    # Hydrogen usage and capacity
    h2_rate_ref = ft.Ref[ft.Text]()
    h2_pct_ref = ft.Ref[ft.Text]()
    h2_vol_ref = ft.Ref[ft.Text]()
    h2_runtime_ref = ft.Ref[ft.Text]()
    h2_bar_ref = ft.Ref[ft.ProgressBar]()
    refs["db_fc_h2_rate"] = h2_rate_ref
    refs["db_fc_h2_pct"] = h2_pct_ref
    refs["db_fc_h2_vol"] = h2_vol_ref
    refs["db_fc_h2_runtime"] = h2_runtime_ref
    refs["db_fc_h2_bar"] = h2_bar_ref

    h2_card = card(ft.Column([
        hdr("SCIENCE", "Hydrogen Usage & Remaining Capacity"),
        ft.Container(height=8),
        value_row("Current H2 Consumption", h2_rate_ref, "kg/h", color=C["amber"], val_size=20),
        ft.Container(height=8),
        value_row("Remaining H2 in Storage", h2_pct_ref, "%", color=C["green"], val_size=20),
        ft.Container(height=6),
        ft.Text("", ref=h2_vol_ref, color=C["gray"], size=11),
        ft.Container(height=8),
        ft.ProgressBar(ref=h2_bar_ref, value=1.0, color=C["teal"], bgcolor=C["gray2"], height=8),
        ft.Container(height=8),
        ft.Text("", ref=h2_runtime_ref, color=C["white"], size=11),
    ]), expand=True)

    # Efficiency and performance
    elec_eff_ref = ft.Ref[ft.Text]()
    conv_eff_ref = ft.Ref[ft.Text]()
    pr_ref = ft.Ref[ft.Text]()
    eff_sp_ref = ft.Ref[ft.Row]()
    refs["db_fc_elec_eff"] = elec_eff_ref
    refs["db_fc_conv_eff"] = conv_eff_ref
    refs["db_fc_pr"] = pr_ref
    refs["db_fc_eff_sp"] = eff_sp_ref

    eff_card = card(ft.Column([
        hdr("AUTO_GRAPH", "System Efficiency"),
        ft.Container(height=8),
        value_row("Electrical Efficiency", elec_eff_ref, "%", color=C["green"], val_size=18),
        ft.Container(height=6),
        value_row("Conversion Efficiency", conv_eff_ref, "%", color=C["teal"], val_size=18),
        ft.Container(height=6),
        value_row("Performance Ratio", pr_ref, "%", color=C["blue"], val_size=18),
        ft.Container(height=8),
        ft.Row([draw_spark(DASH_HIST["efficiency"], w=220, h=44, color=C["green"])], ref=eff_sp_ref),
    ]), expand=True)

    # Health indicators
    alarms_ref = ft.Ref[ft.Text]()
    temp_stab_ref = ft.Ref[ft.Text]()
    refs["db_fc_alarm_count"] = alarms_ref
    refs["db_fc_temp_stability"] = temp_stab_ref

    health_card = card(ft.Column([
        hdr("HEALTH_AND_SAFETY", "Performance & Health Indicators"),
        ft.Container(height=8),
        status_chip("fc_status", "Fuel Cell Status"),
        status_chip("stack", "Stack Health"),
        status_chip("temp", "Temperature Stability"),
        ft.Container(height=8),
        ft.Row([
            ft.Text("Active Alarms Count", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Text("-", ref=alarms_ref, color=C["amber"], size=20, weight=ft.FontWeight.BOLD),
        ]),
        ft.Text("", ref=temp_stab_ref, color=C["gray"], size=11),
    ]), expand=True)

    # Fuel-cell trend monitoring
    trend_ref = ft.Ref[ft.Row]()
    refs["db_fc_trend"] = trend_ref
    trend_card = card(ft.Column([
        hdr("SHOW_CHART", "Fuel Cell Trend Monitoring", f"last {HISTORY_LEN}s"),
        ft.Container(height=8),
        ft.Row([
            ft.Container(width=10, height=3, bgcolor=C["teal"]),
            ft.Text("Power Output", color=C["gray"], size=11),
            ft.Container(width=10),
            ft.Container(width=10, height=3, bgcolor=C["amber"]),
            ft.Text("H2 Consumption", color=C["gray"], size=11),
            ft.Container(width=10),
            ft.Container(width=10, height=3, bgcolor=C["green"]),
            ft.Text("Efficiency", color=C["gray"], size=11),
        ], spacing=4),
        ft.Container(height=10),
        ft.Row([
            draw_line_chart([
                (DASH_HIST["power_kw"], C["teal"]),
                (collections.deque([v * 8 for v in DASH_HIST["h2_rate"]], maxlen=HISTORY_LEN), C["amber"]),
                (DASH_HIST["efficiency"], C["green"]),
            ], w=860, h=210)
        ], ref=trend_ref, alignment=ft.MainAxisAlignment.CENTER),
    ]), expand=True)

    return ft.Column([
        ft.Row([power_card, h2_card, eff_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([health_card, trend_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


# â”€â”€ PAGE 2: Sensors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_sensors(refs: dict):
    return build_sensor_panel(refs)


# â”€â”€ PAGE 3: Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_analytics(refs: dict):
    """
    Row 1: multi-line trend chart (temp, coolant, flow_in)
    Row 2: bar chart snapshot + stats table
    """
    mc_ref  = ft.Ref[ft.Row]()
    bc_ref  = ft.Ref[ft.Row]()
    refs["ana_mc_row"] = mc_ref
    refs["ana_bc_row"] = bc_ref

    multi_card = card(ft.Column([
        hdr("ANALYTICS", "Multi-Sensor Trend",
            f"rolling {HISTORY_LEN}-sample window"),
        ft.Container(height=6),
        ft.Row([
            ft.Container(width=10, height=3, bgcolor=C["red"]),
            ft.Text("Reactor Temp", color=C["gray"], size=11),
            ft.Container(width=8),
            ft.Container(width=10, height=3, bgcolor=C["amber"]),
            ft.Text("Coolant Temp", color=C["gray"], size=11),
            ft.Container(width=8),
            ft.Container(width=10, height=3, bgcolor=C["teal"]),
            ft.Text("Inlet Flow Ã· 3", color=C["gray"], size=11),
            ft.Container(width=8),
            ft.Container(width=10, height=3, bgcolor=C["purple"]),
            ft.Text("Power Ã—1.2", color=C["gray"], size=11),
        ], spacing=4),
        ft.Container(height=10),
        ft.Row([
            draw_line_chart([
                (SENSORS["temp_1"].history,  C["red"]),
                (SENSORS["temp_2"].history,  C["amber"]),
                (collections.deque(
                    [v / 3 for v in SENSORS["flow_in"].history],
                    maxlen=HISTORY_LEN), C["teal"]),
                (collections.deque(
                    [v * 1.2 for v in SENSORS["power"].history],
                    maxlen=HISTORY_LEN), C["purple"]),
            ], w=700, h=180)
        ], ref=mc_ref, alignment=ft.MainAxisAlignment.CENTER),
    ]), expand=True)

    def bar_series():
        return [
            (s.name[:10], s.pct, s.color)
            for s in list(SENSORS.values())[:7]
        ]

    bar_card = card(ft.Column([
        hdr("BAR_CHART", "Sensor Utilisation", "% of operating range"),
        ft.Container(height=10),
        ft.Row([draw_bar_chart(bar_series(), w=380, h=170)],
               ref=bc_ref,
               alignment=ft.MainAxisAlignment.CENTER),
    ]), expand=True)

    # Stats table
    stat_rows = []
    for key, s in SENSORS.items():
        vals = list(s.history)
        avg  = sum(vals) / len(vals) if vals else 0
        stat_rows.append(ft.Row([
            ft.Text(s.name,           color=C["white"], size=12, width=130),
            ft.Text(s.fmt(),          color=s.color,   size=12, width=70,
                    weight=ft.FontWeight.BOLD),
            ft.Text(f"{min(vals):.1f}", color=C["gray"], size=12, width=70),
            ft.Text(f"{max(vals):.1f}", color=C["gray"], size=12, width=70),
            ft.Text(f"{avg:.1f}",      color=C["gray"], size=12, width=70),
            badge(s.status, STATUS_COLOR[s.status]),
        ], spacing=0))

    stats_card = card(ft.Column([
        hdr("TABLE_CHART", "Sensor Statistics"),
        ft.Container(height=8),
        ft.Row([
            ft.Text("Sensor",  color=C["gray"], size=11, width=130),
            ft.Text("Current", color=C["gray"], size=11, width=70),
            ft.Text("Min",     color=C["gray"], size=11, width=70),
            ft.Text("Max",     color=C["gray"], size=11, width=70),
            ft.Text("Avg",     color=C["gray"], size=11, width=70),
            ft.Text("Status",  color=C["gray"], size=11),
        ]),
        divider(),
        ft.Column(stat_rows, spacing=6),
    ], spacing=6))

    return ft.Column([
        ft.Row([multi_card], expand=False),
        ft.Container(height=12),
        ft.Row([bar_card, stats_card], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


# â”€â”€ PAGE 4: System Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_system(refs: dict):
    """
    System health tiles + full alarm log + device status table.
    """
    # Health tiles
    health_keys = [
        ("CPU Load",      "MEMORY",     C["blue"],   lambda: random.uniform(20, 85)),
        ("Network",       "WIFI",       C["green"],  lambda: random.uniform(90, 100)),
        ("Storage",       "STORAGE",    C["amber"],  lambda: random.uniform(40, 70)),
        ("PLC Uptime",    "TIMER",      C["teal"],   None),
    ]
    uptime_start = datetime.now()

    ht_refs = []
    for lbl, ico, col, _ in health_keys:
        r = ft.Ref[ft.Text]()
        ht_refs.append(r)
        refs[f"sys_health_{lbl}"] = r

    def health_tile(lbl, ico, col, val_fn, val_ref):
        init = val_fn() if val_fn else 0
        disp = f"{init:.0f}%" if val_fn else "00:00:00"
        return card(ft.Column([
            ft.Row([
                ft.Icon(getattr(ft.Icons, ico, ft.Icons.CIRCLE),
                        color=col, size=20),
                ft.Text(lbl, color=C["gray"], size=11, expand=True),
            ], spacing=6),
            ft.Container(height=8),
            ft.Text(disp, ref=val_ref, color=col,
                    size=22, weight=ft.FontWeight.BOLD),
        ]), expand=True)

    health_row = ft.Row([
        health_tile(lbl, ico, col, fn, ht_refs[i])
        for i, (lbl, ico, col, fn) in enumerate(health_keys)
    ], spacing=12)

    # Device status table
    devices = [
        ("PLC Unit 1",      "ONLINE",  C["green"]),
        ("PLC Unit 2",      "ONLINE",  C["green"]),
        ("SCADA Server",    "ONLINE",  C["green"]),
        ("HMI Terminal 1",  "ONLINE",  C["green"]),
        ("HMI Terminal 2",  "STANDBY", C["amber"]),
        ("Sensor Hub A",    "ONLINE",  C["green"]),
        ("Sensor Hub B",    "FAULT",   C["red"]),
        ("Data Logger",     "ONLINE",  C["green"]),
        ("OPC-UA Gateway",  "ONLINE",  C["green"]),
        ("Historian DB",    "STANDBY", C["amber"]),
    ]

    dev_rows = []
    for name, status, col in devices:
        dev_rows.append(ft.Row([
            ft.Container(width=8, height=8, border_radius=4,
                         bgcolor=col),
            ft.Container(width=8),
            ft.Text(name,   color=C["white"], size=12, expand=True),
            badge(status, col),
        ]))

    device_card = card(ft.Column([
        hdr("DEVELOPER_BOARD", "Device Status"),
        ft.Container(height=8),
        ft.Column(dev_rows, spacing=8),
    ]), expand=True)

    # Full alarm log
    alarm_log_ref = ft.Ref[ft.Column]()
    refs["sys_alarm_log"] = alarm_log_ref

    def full_alarm_rows():
        rows = []
        for a in list(ALARMS):
            col = STATUS_COLOR[a["level"]]
            rows.append(ft.Row([
                ft.Container(width=3, height=24, bgcolor=col, border_radius=2),
                ft.Container(width=8),
                ft.Text(a["time"],   color=C["gray"],  size=11, width=65),
                badge(a["level"], col),
                ft.Container(width=8),
                ft.Text(a["sensor"], color=C["amber"], size=11, width=110),
                ft.Text(a["msg"],    color=C["white"], size=11, expand=True),
            ], spacing=0))
        return rows

    alarm_card = card(ft.Column([
        hdr("NOTIFICATIONS_ACTIVE", "Alarm Log",
            f"{len(ALARM_HISTORY)} events"),
        ft.Container(height=8),
        ft.Column(full_alarm_rows(), ref=alarm_log_ref, spacing=5),
    ]), expand=True)

    return ft.Column([
        health_row,
        ft.Container(height=12),
        ft.Row([device_card, alarm_card], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


def build_alarm_history(refs: dict):
    title_ref = ft.Ref[ft.Text]()
    log_ref = ft.Ref[ft.Column]()
    refs["alm_title"] = title_ref
    refs["alm_log_col"] = log_ref

    def log_rows():
        rows = []
        for rec in list(ALARM_HISTORY):
            rows.append(alarm_history_row(rec))
        if not rows:
            rows.append(ft.Text("No alarm history available.", color=C["gray"], size=12))
        return rows

    active_count = len(ACTIVE_ALARMS)
    return ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=C["amber"], size=18),
            ft.Text(
                f"Alarm History Log  •  Active: {active_count}  •  Total Events: {len(ALARM_HISTORY)}",
                ref=title_ref, color=C["white"], size=15, weight=ft.FontWeight.W_700
            ),
        ], spacing=8),
        ft.Container(height=10),
        card(ft.Column([
            ft.Row([
                ft.Container(width=3),
                ft.Container(width=8),
                ft.Text("Alarm Name / Type", color=C["gray"], size=10, width=ALM_COL["name"]),
                ft.Container(width=ALM_COL["sev"], alignment=ft.Alignment(0, 0),
                             content=ft.Text("Severity", color=C["gray"], size=10)),
                ft.Text("Raised At", color=C["gray"], size=10, width=ALM_COL["raised"]),
                ft.Text("Cleared At", color=C["gray"], size=10, width=ALM_COL["cleared"]),
                ft.Container(width=ALM_COL["dur"], alignment=ft.Alignment(0, 0),
                             content=ft.Text("Duration", color=C["gray"], size=10)),
                ft.Container(width=ALM_COL["status"], alignment=ft.Alignment(0, 0),
                             content=ft.Text("Status", color=C["gray"], size=10)),
            ], spacing=0),
            divider(),
            ft.Column(log_rows(), ref=log_ref, spacing=6),
        ], spacing=6), expand=True),
    ], spacing=0, expand=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  MAIN APPLICATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def main(page: ft.Page):
    page.title         = "Industrial HMI Dashboard"
    page.bgcolor       = C["bg"]
    page.window.width  = 1200
    page.window.height = 780
    page.padding       = 0

    refs: dict = {}          # live-update reference store
    current_page = {"idx": 0}
    selected_sensor = {"key": None}

    # â”€â”€ Build all pages once (lazy rebuild on nav) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pages_cache = {}

    def open_sensor_detail(sensor_key: str):
        selected_sensor["key"] = sensor_key
        pages_cache.pop(1, None)
        refs.clear()
        if content_ref.current:
            content_ref.current.controls = [get_page(1)]
            page.update()

    def close_sensor_detail():
        selected_sensor["key"] = None
        pages_cache.pop(1, None)
        refs.clear()
        if content_ref.current:
            content_ref.current.controls = [get_page(1)]
            page.update()

    def build_sensors_page(local_refs: dict):
        if selected_sensor["key"] and selected_sensor["key"] in SENSORS:
            return build_sensor_detail(local_refs, selected_sensor["key"], close_sensor_detail)
        return build_sensor_panel(local_refs, on_sensor_click=open_sensor_detail)

    def get_page(idx):
        if idx not in pages_cache:
            builders = [build_dashboard, build_sensors_page,
                        build_analytics, build_system, build_alarm_history]
            pages_cache[idx] = builders[idx](refs)
        return pages_cache[idx]

    # â”€â”€ Top bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    clock_ref   = ft.Ref[ft.Text]()
    alarm_badge = ft.Ref[ft.Text]()

    topbar = ft.Container(
        bgcolor=C["header"],
        padding=ft.Padding.symmetric(horizontal=20, vertical=10),
        border=ft.Border(bottom=ft.BorderSide(1, C["border"])),
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.PRECISION_MANUFACTURING,
                        color=C["teal"], size=22),
                ft.Container(width=8),
                ft.Text("INDUSTRIAL HMI", color=C["white"],
                        size=16, weight=ft.FontWeight.W_700),
                ft.Container(width=4),
                ft.Text("v2.0 â€¢ PROTO", color=C["gray"], size=10),
            ]),
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE,
                                color=C["amber"], size=16),
                        ft.Text("0", ref=alarm_badge,
                                color=C["amber"], size=11,
                                weight=ft.FontWeight.W_700),
                        ft.Text("alarms", color=C["gray"], size=11),
                    ], spacing=4),
                    bgcolor=C["amber"] + "15",
                    border_radius=6,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    ink=True,
                    on_click=lambda e: switch_page(4),
                ),
                ft.Container(width=16),
                ft.Icon(ft.Icons.CIRCLE, color=C["green"], size=8),
                ft.Text("LIVE", color=C["green"], size=11,
                        weight=ft.FontWeight.W_700),
                ft.Container(width=16),
                ft.Text("", ref=clock_ref, color=C["gray"], size=12),
            ], spacing=6),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    )

    # â”€â”€ Sidebar nav â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    nav_items = [
        ("Dashboard", "DASHBOARD",    0),
        ("Sensors",   "SENSORS",      1),
        ("Analytics", "ANALYTICS",    2),
        ("System",    "MEMORY",       3),
        ("Alarms",    "WARNING_AMBER",4),
    ]

    nav_col_ref = ft.Ref[ft.Column]()

    def make_nav(active_idx):
        btns = []
        for lbl, ico, idx in nav_items:
            i = idx  # capture
            btns.append(nav_btn(lbl, ico, active_idx == i,
                                on_click=lambda e, x=i: switch_page(x)))
        return btns

    sidebar = ft.Container(
        bgcolor=C["panel"],
        width=84,
        border=ft.Border(right=ft.BorderSide(1, C["border"])),
        content=ft.Column(
            make_nav(0),
            ref=nav_col_ref,
            alignment=ft.MainAxisAlignment.START,
            spacing=4,
            scroll=ft.ScrollMode.HIDDEN,
        ),
        padding=ft.Padding.symmetric(vertical=10),
    )

    # â”€â”€ Content area â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    content_ref = ft.Ref[ft.Column]()

    content_area = ft.Container(
        content=ft.Column([
            ft.Column([get_page(0)], ref=content_ref, expand=True),
        ], expand=True, scroll=ft.ScrollMode.AUTO),
        expand=True,
        padding=16,
    )

    def switch_page(idx):
        current_page["idx"] = idx
        selected_sensor["key"] = None
        pages_cache.clear()          # force rebuild with fresh refs
        refs.clear()
        nav_col_ref.current.controls = make_nav(idx)
        content_ref.current.controls = [get_page(idx)]
        page.update()

    # â”€â”€ Status bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    statusbar = ft.Container(
        bgcolor=C["header"],
        padding=ft.Padding.symmetric(horizontal=16, vertical=5),
        border=ft.Border(top=ft.BorderSide(1, C["border"])),
        content=ft.Row([
            ft.Icon(ft.Icons.CIRCLE, color=C["green"], size=7),
            ft.Text("All systems nominal", color=C["gray"], size=10),
            ft.Container(expand=True),
            ft.Text("Simulation mode  â€¢  Mock data only",
                    color=C["gray2"], size=10),
        ], spacing=6),
    )

    # â”€â”€ Full layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    page.add(ft.Column([
        topbar,
        ft.Row([
            sidebar,
            content_area,
        ], spacing=0, expand=True,
           vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        statusbar,
    ], spacing=0, expand=True))

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  SIMULATION + LIVE-UPDATE THREAD
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    uptime_start = datetime.now()
    dash_state = {
        "energy_kwh": 0.0,
        "h2_capacity_kg": 120.0,
        "h2_remaining_kg": 120.0,
        "h2_consumed_kg": 0.0,
        "elec_eff_target": 52.0,
        "elec_eff": 52.0,
        "conv_eff": 57.0,
        "perf_ratio": 88.0,
    }

    async def simulate():
        while True:
            try:
                # Tick all sensors
                for s in SENSORS.values():
                    s.tick()

                # Alarm lifecycle management (active + resolved + history)
                now = datetime.now()
                for key, s in SENSORS.items():
                    if s.status == "OK":
                        _resolve_alarm(key, s, now)
                    else:
                        _raise_or_update_alarm(key, s, now)

                fault_count = sum(
                    1 for s in SENSORS.values() if s.status != "OK"
                )
                active_alarm_count = len(ACTIVE_ALARMS)
                dm = dashboard_metrics()
                DASH_HIST["avg_temp"].append(dm["avg_temp"])
                DASH_HIST["avg_pressure"].append(dm["avg_pressure"])
                DASH_HIST["total_flow"].append(dm["total_flow"])
                DASH_HIST["h2"].append(dm["h2"])
                DASH_HIST["o2"].append(dm["o2"])

                load_penalty = min(12.0, fault_count * 3.0)
                dash_state["elec_eff_target"] += random.uniform(-0.35, 0.35)
                dash_state["elec_eff_target"] = max(42.0, min(60.0, dash_state["elec_eff_target"] - load_penalty * 0.08))
                dash_state["elec_eff"] += (dash_state["elec_eff_target"] - dash_state["elec_eff"]) * 0.15 + random.uniform(-0.15, 0.15)
                dash_state["elec_eff"] = max(40.0, min(62.0, dash_state["elec_eff"]))
                dash_state["conv_eff"] = max(48.0, min(70.0, dash_state["elec_eff"] + 4.5 + random.uniform(-1.0, 1.0)))

                h2_rate_kg_h = max(1.2, min(10.0, (dm["total_flow"] * dm["h2"]) / 180.0))
                power_kw = h2_rate_kg_h * 33.3 * (dash_state["elec_eff"] / 100.0)
                power_kw = max(10.0, min(180.0, power_kw))
                voltage_v = max(360.0, min(760.0, 560.0 + random.uniform(-80.0, 90.0)))
                current_a = (power_kw * 1000.0) / max(voltage_v, 1.0)
                dash_state["perf_ratio"] = max(55.0, min(110.0, (power_kw / 120.0) * 100.0))

                step_hours = 1.5 / 3600.0
                dash_state["energy_kwh"] += power_kw * step_hours
                h2_used = h2_rate_kg_h * step_hours
                dash_state["h2_consumed_kg"] += h2_used
                dash_state["h2_remaining_kg"] = max(0.0, dash_state["h2_remaining_kg"] - h2_used)
                h2_remaining_pct = (dash_state["h2_remaining_kg"] / dash_state["h2_capacity_kg"]) * 100.0
                runtime_h = dash_state["h2_remaining_kg"] / max(h2_rate_kg_h, 0.05)

                DASH_HIST["power_kw"].append(power_kw)
                DASH_HIST["h2_rate"].append(h2_rate_kg_h)
                DASH_HIST["efficiency"].append(dash_state["elec_eff"])

                # â”€â”€ Clock & alarm badge (always visible) â”€â”€â”€â”€â”€â”€
                clock_ref.current.value       = datetime.now().strftime("%H:%M:%S  %d %b %Y")
                alarm_badge.current.value     = str(active_alarm_count)

                idx = current_page["idx"]

                # â”€â”€ PAGE 0: Dashboard overview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                if idx == 0:
                    # Electricity generation values
                    pwr_ref = refs.get("db_fc_power_kw")
                    eng_ref = refs.get("db_fc_energy_kwh")
                    v_ref = refs.get("db_fc_voltage")
                    c_ref = refs.get("db_fc_current")
                    psp_ref = refs.get("db_fc_power_sp")
                    if pwr_ref and pwr_ref.current:
                        pwr_ref.current.value = f"{power_kw:.1f}"
                    if eng_ref and eng_ref.current:
                        eng_ref.current.value = f"{dash_state['energy_kwh']:.1f}"
                    if v_ref and v_ref.current:
                        v_ref.current.value = f"Voltage Output: {voltage_v:.0f} V"
                    if c_ref and c_ref.current:
                        c_ref.current.value = f"Current Output: {current_a:.0f} A"
                    if psp_ref and psp_ref.current:
                        psp_ref.current.controls = [draw_spark(DASH_HIST["power_kw"], w=320, h=44, color=C["teal"])]

                    # Hydrogen monitoring
                    h2r_ref = refs.get("db_fc_h2_rate")
                    h2p_ref = refs.get("db_fc_h2_pct")
                    h2v_ref = refs.get("db_fc_h2_vol")
                    h2rt_ref = refs.get("db_fc_h2_runtime")
                    h2b_ref = refs.get("db_fc_h2_bar")
                    if h2r_ref and h2r_ref.current:
                        h2r_ref.current.value = f"{h2_rate_kg_h:.2f}"
                    if h2p_ref and h2p_ref.current:
                        h2p_ref.current.value = f"{h2_remaining_pct:.1f}"
                    if h2v_ref and h2v_ref.current:
                        h2v_ref.current.value = (
                            f"Remaining H2 Volume: {dash_state['h2_remaining_kg']:.1f} kg / "
                            f"{dash_state['h2_capacity_kg']:.0f} kg"
                        )
                    if h2rt_ref and h2rt_ref.current:
                        h2rt_ref.current.value = f"Estimated Runtime Remaining: {runtime_h:.1f} h"
                    if h2b_ref and h2b_ref.current:
                        h2b_ref.current.value = max(0.0, min(1.0, h2_remaining_pct / 100.0))

                    # Efficiency values
                    ee_ref = refs.get("db_fc_elec_eff")
                    ce_ref = refs.get("db_fc_conv_eff")
                    pr_ref = refs.get("db_fc_pr")
                    esp_ref = refs.get("db_fc_eff_sp")
                    if ee_ref and ee_ref.current:
                        ee_ref.current.value = f"{dash_state['elec_eff']:.1f}"
                    if ce_ref and ce_ref.current:
                        ce_ref.current.value = f"{dash_state['conv_eff']:.1f}"
                    if pr_ref and pr_ref.current:
                        pr_ref.current.value = f"{dash_state['perf_ratio']:.1f}"
                    if esp_ref and esp_ref.current:
                        esp_ref.current.controls = [draw_spark(DASH_HIST["efficiency"], w=220, h=44, color=C["green"])]

                    # Health indicators
                    temp_stability = max(0.0, 100.0 - abs(SENSORS["temp_1"].value - SENSORS["temp_2"].value) * 1.3)
                    if fault_count >= 2:
                        fc_status = ("FAULT", C["red"])
                    elif dash_state["elec_eff"] < 45.0:
                        fc_status = ("DEGRADED", C["amber"])
                    elif power_kw < 12.0:
                        fc_status = ("IDLE", C["gray"])
                    else:
                        fc_status = ("ACTIVE", C["green"])
                    stack_health = ("DEGRADED", C["amber"]) if dash_state["perf_ratio"] < 70 else ("GOOD", C["green"])
                    temp_health = ("UNSTABLE", C["amber"]) if temp_stability < 78 else ("STABLE", C["green"])

                    status_map = {
                        "fc_status": fc_status,
                        "stack": stack_health,
                        "temp": temp_health,
                    }
                    for key, (txt, col) in status_map.items():
                        t_ref = refs.get(f"db_st_{key}_txt")
                        d_ref = refs.get(f"db_st_{key}_dot")
                        if t_ref and t_ref.current:
                            t_ref.current.value = txt
                            t_ref.current.color = col
                        if d_ref and d_ref.current:
                            d_ref.current.bgcolor = col

                    al_ref = refs.get("db_fc_alarm_count")
                    ts_ref = refs.get("db_fc_temp_stability")
                    if al_ref and al_ref.current:
                        al_ref.current.value = str(active_alarm_count)
                    if ts_ref and ts_ref.current:
                        ts_ref.current.value = f"Temperature Stability Score: {temp_stability:.1f}%"

                    # Fuel-cell trend monitoring
                    tr_ref = refs.get("db_fc_trend")
                    if tr_ref and tr_ref.current:
                        tr_ref.current.controls = [
                            draw_line_chart([
                                (DASH_HIST["power_kw"], C["teal"]),
                                (collections.deque([v * 8 for v in DASH_HIST["h2_rate"]],
                                                   maxlen=HISTORY_LEN), C["amber"]),
                                (DASH_HIST["efficiency"], C["green"]),
                            ], w=860, h=210)
                        ]

                # â”€â”€ PAGE 1: Sensors (full monitoring panel) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                elif idx == 1:
                    detail_key = refs.get("sd_sensor_key")
                    if detail_key and detail_key in SENSORS:
                        s = SENSORS[detail_key]
                        v_ref = refs.get("sd_val")
                        dot_ref = refs.get("sd_st_dot")
                        txt_ref = refs.get("sd_st_txt")
                        min_ref = refs.get("sd_min")
                        max_ref = refs.get("sd_max")
                        avg_ref = refs.get("sd_avg")
                        plot_ref = refs.get("sd_plot")
                        alarm_ref = refs.get("sd_alarm_col")

                        if v_ref and v_ref.current:
                            v_ref.current.value = s.fmt(2)
                        if dot_ref and dot_ref.current:
                            dot_ref.current.bgcolor = STATUS_COLOR[s.status]
                        if txt_ref and txt_ref.current:
                            txt_ref.current.value = s.status
                            txt_ref.current.color = STATUS_COLOR[s.status]
                        if min_ref and min_ref.current:
                            min_ref.current.value = f"{s.min_seen:.2f}"
                        if max_ref and max_ref.current:
                            max_ref.current.value = f"{s.max_seen:.2f}"
                        if avg_ref and avg_ref.current:
                            avg_ref.current.value = f"{s.avg_seen:.2f}"
                        if plot_ref and plot_ref.current:
                            plot_ref.current.controls = [
                                draw_line_chart([(s.history_long, s.color)], w=920, h=260)
                            ]
                        if alarm_ref and alarm_ref.current:
                            rows = []
                            for a in [x for x in ALARMS if x["sensor"] == s.name][:12]:
                                col = STATUS_COLOR[a["level"]]
                                rows.append(ft.Row([
                                    ft.Container(width=3, height=22, bgcolor=col, border_radius=2),
                                    ft.Container(width=8),
                                    ft.Text(a["time"], color=C["gray"], size=11, width=70),
                                    badge(a["level"], col),
                                    ft.Container(width=8),
                                    ft.Text(a["msg"], color=C["white"], size=11, expand=True),
                                ], spacing=0))
                            if not rows:
                                rows.append(ft.Text("No alarms recorded for this sensor.", color=C["gray"], size=11))
                            alarm_ref.current.controls = rows
                    else:
                        for key in ["temp_1", "pressure", "flow_in", "power"]:
                            s = SENSORS[key]
                            vr = refs.get(f"kpi_{key}_val")
                            sr = refs.get(f"kpi_{key}_status")
                            pr = refs.get(f"kpi_{key}_spark")
                            if vr and vr.current:
                                vr.current.value = s.fmt()
                            if sr and sr.current:
                                sr.current.bgcolor = STATUS_COLOR[s.status]
                            if pr and pr.current:
                                pr.current.controls = [
                                    draw_spark(s.history, w=140, h=38, color=s.color)
                                ]

                        for key in [
                            "temp_2", "temp_3", "pressure_2", "pressure_3",
                            "pressure_4", "flow_out", "flow_3", "h2", "oxygen"
                        ]:
                            s = SENSORS[key]
                            vr_aux = refs.get(f"aux_{key}_val")
                            sr_aux = refs.get(f"aux_{key}_status")
                            pr_aux = refs.get(f"aux_{key}_spark")
                            if vr_aux and vr_aux.current:
                                vr_aux.current.value = s.fmt()
                            if sr_aux and sr_aux.current:
                                sr_aux.current.bgcolor = STATUS_COLOR[s.status]
                            if pr_aux and pr_aux.current:
                                pr_aux.current.controls = [
                                    draw_spark(s.history, w=140, h=34, color=s.color)
                                ]

                        ar = refs.get("dash_arc_row")
                        if ar and ar.current:
                            sl = SENSORS["level"]
                            ar.current.controls = [
                                draw_arc(sl.pct, label=sl.fmt(0),
                                         unit=sl.unit, color=C["teal"])
                            ]

                        lr = refs.get("dash_linechart_row")
                        if lr and lr.current:
                            lr.current.controls = [
                                draw_line_chart([
                                    (SENSORS["temp_1"].history,   C["red"]),
                                    (collections.deque(
                                        [v * 20 for v in SENSORS["pressure"].history],
                                        maxlen=HISTORY_LEN), C["blue"]),
                                ], w=440, h=150)
                            ]

                        acr = refs.get("dash_alarm_col")
                        if acr and acr.current:
                            def alarm_row_small(a):
                                col = STATUS_COLOR[a["level"]]
                                return ft.Row([
                                    ft.Container(width=3, height=24, bgcolor=col,
                                                 border_radius=2),
                                    ft.Container(width=8),
                                    ft.Text(a["time"],  color=C["gray"],  size=11, width=60),
                                    badge(a["level"], col),
                                    ft.Container(width=8),
                                    ft.Text(a["msg"],   color=C["white"], size=12, expand=True),
                                ], spacing=0)
                            acr.current.controls = [
                                alarm_row_small(a) for a in list(ALARMS)[:4]
                            ]

                # â”€â”€ PAGE 2: Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                elif idx == 2:
                    mcr = refs.get("ana_mc_row")
                    if mcr and mcr.current:
                        mcr.current.controls = [
                            draw_line_chart([
                                (SENSORS["temp_1"].history,  C["red"]),
                                (SENSORS["temp_2"].history,  C["amber"]),
                                (collections.deque(
                                    [v / 3 for v in SENSORS["flow_in"].history],
                                    maxlen=HISTORY_LEN), C["teal"]),
                                (collections.deque(
                                    [v * 1.2 for v in SENSORS["power"].history],
                                    maxlen=HISTORY_LEN), C["purple"]),
                            ], w=700, h=180)
                        ]

                    bcr = refs.get("ana_bc_row")
                    if bcr and bcr.current:
                        series = [(s.name[:10], s.pct, s.color)
                                  for s in list(SENSORS.values())[:7]]
                        bcr.current.controls = [
                            draw_bar_chart(series, w=380, h=170)
                        ]

                # â”€â”€ PAGE 3: System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                elif idx == 3:
                    health_data = {
                        "CPU Load": f"{random.uniform(20,85):.0f}%",
                        "Network":  f"{random.uniform(90,100):.0f}%",
                        "Storage":  f"{random.uniform(40,70):.0f}%",
                        "PLC Uptime": str(datetime.now() - uptime_start).split('.')[0],
                    }
                    for lbl, val in health_data.items():
                        r = refs.get(f"sys_health_{lbl}")
                        if r and r.current:
                            r.current.value = val

                    alr = refs.get("sys_alarm_log")
                    if alr and alr.current:
                        rows = []
                        for a in list(ALARMS):
                            col = STATUS_COLOR[a["level"]]
                            rows.append(ft.Row([
                                ft.Container(width=3, height=24, bgcolor=col,
                                             border_radius=2),
                                ft.Container(width=8),
                                ft.Text(a["time"],   color=C["gray"],  size=11, width=65),
                                badge(a["level"], col),
                                ft.Container(width=8),
                                ft.Text(a["sensor"], color=C["amber"], size=11, width=110),
                                ft.Text(a["msg"],    color=C["white"], size=11, expand=True),
                            ], spacing=0))
                        alr.current.controls = rows

                # â”€â”€ PAGE 4: Alarm History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                elif idx == 4:
                    title_ref = refs.get("alm_title")
                    log_ref = refs.get("alm_log_col")
                    if title_ref and title_ref.current:
                        title_ref.current.value = (
                            f"Alarm History Log  •  Active: {active_alarm_count}  •  Total Events: {len(ALARM_HISTORY)}"
                        )
                    if log_ref and log_ref.current:
                        rows = []
                        for rec in list(ALARM_HISTORY):
                            rows.append(alarm_history_row(rec))
                        if not rows:
                            rows.append(ft.Text("No alarm history available.", color=C["gray"], size=12))
                        log_ref.current.controls = rows

                page.update()

            except Exception as ex:
                print(f"[SIM] {ex}")
                continue
            await asyncio.sleep(1.5)

    page.run_task(simulate)


ft.run(main)
