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
import random, time, threading, math, collections
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

STATUS_COLOR = {"OK": C["green"], "WARN": C["amber"], "FAULT": C["red"]}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  SIMULATED SENSOR ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
HISTORY_LEN = 60   # data-points kept per sensor

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

    def tick(self):
        # slowly drift target, then add noise
        self._target += random.uniform(-self.drift_speed, self.drift_speed)
        self._target  = max(self.low * 0.9, min(self.high * 1.1, self._target))
        self.value    = self._target + random.gauss(0, self.noise)
        self.value    = max(self.low * 0.85, min(self.high * 1.15, self.value))
        self.history.append(self.value)

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

ALARMS: collections.deque = collections.deque(maxlen=50)

def _gen_alarm_seed():
    """Seed with a few past alarms for realism."""
    for i in range(6):
        t = datetime.now() - timedelta(minutes=random.randint(5, 120))
        s = random.choice(list(SENSORS.values()))
        lvl = random.choice(["WARN", "FAULT"])
        ALARMS.appendleft({
            "time": t.strftime("%H:%M:%S"),
            "sensor": s.name,
            "level": lvl,
            "msg": f"{s.name} {'exceeded limit' if lvl=='FAULT' else 'near threshold'}",
        })

_gen_alarm_seed()

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
def build_sensor_panel(refs: dict):
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

        return card(ft.Column([
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

        return card(ft.Column([
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


def build_dashboard(refs: dict):
    return ft.Column([
        card(ft.Column([
            hdr("DASHBOARD", "Overview"),
            ft.Container(height=8),
            ft.Text(
                "Primary monitoring widgets were moved to the Sensors section.",
                color=C["gray"], size=12
            ),
            ft.Container(height=8),
            ft.Text(
                "Open Sensors to view the full live card layout with mini trends.",
                color=C["white"], size=12
            ),
        ]), padding=16),
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
            f"{len(ALARMS)} events"),
        ft.Container(height=8),
        ft.Column(full_alarm_rows(), ref=alarm_log_ref, spacing=5),
    ]), expand=True)

    return ft.Column([
        health_row,
        ft.Container(height=12),
        ft.Row([device_card, alarm_card], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.START),
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

    # â”€â”€ Build all pages once (lazy rebuild on nav) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pages_cache = {}

    def get_page(idx):
        if idx not in pages_cache:
            builders = [build_dashboard, build_sensors,
                        build_analytics, build_system]
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

    def simulate():
        while True:
            time.sleep(1.5)
            try:
                # Tick all sensors
                for s in SENSORS.values():
                    s.tick()

                # Generate alarms from faults
                for s in SENSORS.values():
                    if s.status != "OK" and random.random() < 0.15:
                        ALARMS.appendleft({
                            "time":   datetime.now().strftime("%H:%M:%S"),
                            "sensor": s.name,
                            "level":  s.status,
                            "msg":    f"{s.name} {'exceeded limit' if s.status=='FAULT' else 'near threshold'}",
                        })

                fault_count = sum(
                    1 for s in SENSORS.values() if s.status != "OK"
                )

                # â”€â”€ Clock & alarm badge (always visible) â”€â”€â”€â”€â”€â”€
                clock_ref.current.value       = datetime.now().strftime("%H:%M:%S  %d %b %Y")
                alarm_badge.current.value     = str(fault_count)

                idx = current_page["idx"]

                # â”€â”€ PAGE 1: Sensors (full monitoring panel) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                if idx == 1:
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

                page.update()

            except Exception as ex:
                print(f"[SIM] {ex}")
                break

    threading.Thread(target=simulate, daemon=True).start()


ft.run(main)
