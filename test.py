import flet as ft
import flet.canvas as cv
import random
import time
import threading
import math
import types
from datetime import datetime
from typing import List

# --- COMPATIBILITY ---
if not hasattr(ft, 'colors'):
    ft.colors = ft.Colors
if not hasattr(ft, 'icons'):
    ft.icons = ft.Icons
if not hasattr(ft, "animation"):
    ft.animation = types.SimpleNamespace(Animation=ft.Animation)

# --- STYLING ---
BG_COLOR      = "#0D1117"
CARD_COLOR    = "#161B22"
ACCENT_BLUE   = "#58A6FF"
ACCENT_GREEN  = "#3FB950"
ACCENT_RED    = "#F85149"
ACCENT_YELLOW = "#D29922"
CHART_COLOR   = "#00B4FF"
SIDEBAR_COLOR = "#010409"
BORDER_COLOR  = "#30363D"


def b_all(width, color):
    try:
        return ft.Border.all(width, color)
    except Exception:
        return ft.border.all(width, color)


def p_only(left=0, right=0, top=0, bottom=0):
    try:
        return ft.Padding.only(left=left, right=right, top=top, bottom=bottom)
    except Exception:
        return ft.padding.only(left=left, right=right, top=top, bottom=bottom)


def safe_icon(name: str):
    icon_map = {
        "DASHBOARD":           "dashboard",
        "ANALYTICS":           "analytics",
        "SETTINGS":            "settings",
        "WARNING":             "warning",
        "FIBER_MANUAL_RECORD": "fiber_manual_record",
    }
    for src in [ft.Icons, getattr(ft, "icons", None)]:
        if src and hasattr(src, name):
            return getattr(src, name)
    return icon_map.get(name, "circle")


# ---------------------------------------------------------------------------
# Sparkline chart using ft.canvas
# ---------------------------------------------------------------------------
class Sparkline:
    """Canvas-drawn sparkline that works in Flet 0.82+"""

    def __init__(self, points: List[float], min_v: float, max_v: float,
                 width: int = 300, height: int = 85,
                 line_color: str = CHART_COLOR, fill_color: str = "#0D2535"):
        self.points     = list(points)
        self.min_v      = min_v
        self.max_v      = max_v
        self.w          = width
        self.h          = height
        self.line_color = line_color
        self.fill_color = fill_color
        self.canvas     = cv.Canvas(width=width, height=height)
        self._redraw()

        # The widget to embed in the layout
        self.widget = ft.Container(
            content=self.canvas,
            width=self.w,
            height=self.h,
            bgcolor="#0A0C10",
            border_radius=8,
            border=b_all(1, BORDER_COLOR),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def update_points(self, points: List[float]):
        self.points = list(points)
        self._redraw()
        try:
            self.canvas.update()
        except Exception:
            pass

    def _redraw(self):
        if not self.points:
            return

        n   = len(self.points)
        rng = self.max_v - self.min_v or 1
        w, h = float(self.w), float(self.h)
        pad  = 6.0

        def px(i):
            return pad + (i / max(n - 1, 1)) * (w - 2 * pad)

        def py(v):
            norm = (v - self.min_v) / rng
            return h - pad - norm * (h - 2 * pad)

        shapes = []

        # Horizontal grid lines
        grid_paint = cv.Paint(color="#1C2128", stroke_width=1,
                               style=cv.PaintingStyle.STROKE)
        for frac in [0.25, 0.5, 0.75]:
            y = pad + frac * (h - 2 * pad)
            shapes.append(cv.Line(pad, y, w - pad, y, grid_paint))

        # Fill polygon under line
        fill_pts = (
            [ft.Offset(px(0), h - pad)]
            + [ft.Offset(px(i), py(v)) for i, v in enumerate(self.points)]
            + [ft.Offset(px(n - 1), h - pad)]
        )
        fill_paint = cv.Paint(color=self.fill_color, style=cv.PaintingStyle.FILL)
        shapes.append(cv.Path(
            elements=[
                cv.Path.MoveTo(fill_pts[0].x, fill_pts[0].y),
                *[cv.Path.LineTo(p.x, p.y) for p in fill_pts[1:]],
                cv.Path.Close(),
            ],
            paint=fill_paint,
        ))

        # Smooth line using cubic bezier segments
        line_paint = cv.Paint(
            color=self.line_color, stroke_width=2,
            style=cv.PaintingStyle.STROKE,
            stroke_cap=cv.StrokeCap.ROUND,
            stroke_join=cv.StrokeJoin.ROUND,
        )
        elems = [cv.Path.MoveTo(px(0), py(self.points[0]))]
        for i in range(1, n):
            x0, y0 = px(i - 1), py(self.points[i - 1])
            x1, y1 = px(i),     py(self.points[i])
            cx = (x0 + x1) / 2
            elems.append(cv.Path.CubicTo(cx, y0, cx, y1, x1, y1))
        shapes.append(cv.Path(elements=elems, paint=line_paint))

        # Dot at last point
        lx, ly = px(n - 1), py(self.points[-1])
        shapes.append(cv.Circle(lx, ly, 4, cv.Paint(color="#0A0C10",       style=cv.PaintingStyle.FILL)))
        shapes.append(cv.Circle(lx, ly, 3, cv.Paint(color=self.line_color, style=cv.PaintingStyle.FILL)))

        self.canvas.shapes = shapes


# ---------------------------------------------------------------------------
# Data helper
# ---------------------------------------------------------------------------
class DataPoint:
    def __init__(self, max_points: int = 30):
        self.max_points = max_points
        self.points: List[float] = [50.0] * max_points

    def add(self, value: float):
        self.points.pop(0)
        self.points.append(float(value))

    def avg(self) -> float:
        return sum(self.points) / len(self.points)


# ---------------------------------------------------------------------------
# Sensor card
# ---------------------------------------------------------------------------
class SensorCard:
    def __init__(self, title, unit, min_v, max_v, warn, crit):
        self.title   = title
        self.unit    = unit
        self.min_v   = min_v
        self.max_v   = max_v
        self.warn    = warn
        self.crit    = crit
        self.data    = DataPoint(30)
        self.current = (min_v + max_v) / 2

        self.txt_value  = ft.Text(f"{self.current:.1f}", size=40,
                                   weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        self.txt_unit   = ft.Text(unit, size=14, color=ft.colors.GREY_500)
        self.txt_avg    = ft.Text("Avg: --", size=10, color=ft.colors.GREY_400)
        self.txt_time   = ft.Text(f"Updated: {datetime.now():%H:%M:%S}",
                                   size=9, color=ft.colors.GREY_700)
        self.dot        = ft.Container(width=8, height=8,
                                        bgcolor=ACCENT_GREEN, border_radius=4)
        self.txt_status = ft.Text("Online", size=11, color=ft.colors.GREY_400)

        self.spark = Sparkline(self.data.points, min_v, max_v, width=340, height=85)

        self.container = ft.Container(
            bgcolor=CARD_COLOR,
            padding=18,
            border_radius=12,
            border=b_all(1, BORDER_COLOR),
            expand=True,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title.upper(), size=11,
                                     color=ft.colors.GREY_500,
                                     weight=ft.FontWeight.BOLD),
                            ft.Row(controls=[self.dot, self.txt_status], spacing=5),
                        ]
                    ),
                    ft.Row(
                        controls=[self.txt_value, self.txt_unit],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    self.txt_avg,
                    self.spark.widget,
                    self.txt_time,
                ],
            ),
        )

    def update_value(self, new_val: float):
        self.current = max(self.min_v, min(self.max_v, new_val))
        self.data.add(self.current)

        self.txt_value.value = f"{self.current:.1f}"
        self.txt_avg.value   = f"Avg: {self.data.avg():.1f}"
        self.txt_time.value  = f"Updated: {datetime.now():%H:%M:%S}"
        self.spark.update_points(self.data.points)

        if self.current >= self.crit:
            color, status, bw = ACCENT_RED,    "Critical", 2
        elif self.current >= self.warn:
            color, status, bw = ACCENT_YELLOW, "Warning",  2
        else:
            color, status, bw = ACCENT_GREEN,  "Online",   1

        self.dot.bgcolor      = color
        self.txt_status.value = status
        self.container.border = b_all(bw, color if bw == 2 else BORDER_COLOR)


# ---------------------------------------------------------------------------
# Alarm panel
# ---------------------------------------------------------------------------
class AlarmPanel:
    def __init__(self):
        self._items: list = []
        self.alarm_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=130)
        self.no_alarms = ft.Text("No active alarms", size=12,
                                  color=ft.colors.GREY_600, italic=True)
        self.body = ft.Column(
            spacing=10,
            controls=[
                ft.Text("ACTIVE ALARMS", size=11,
                         color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
                self.no_alarms,
            ]
        )
        self.container = ft.Container(
            bgcolor=CARD_COLOR, padding=18,
            border_radius=12, border=b_all(1, BORDER_COLOR),
            expand=True, content=self.body,
        )

    def add_alarm(self, title: str, value: float):
        item = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon=safe_icon("WARNING"), color=ACCENT_RED, size=15),
                ft.Text(f"{title}: {value:.1f}", size=12, color=ft.colors.WHITE),
            ]),
            bgcolor="#2D1517", padding=8, border_radius=6,
        )
        self._items.append(item)
        self._items = self._items[-5:]
        self.alarm_col.controls = list(self._items)
        if self.no_alarms in self.body.controls:
            self.body.controls.remove(self.no_alarms)
        if self.alarm_col not in self.body.controls:
            self.body.controls.append(self.alarm_col)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    page.title      = "Industrial HMI Dashboard"
    page.bgcolor    = BG_COLOR
    page.padding    = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll     = ft.ScrollMode.HIDDEN

    try:
        page.window.width  = 1280
        page.window.height = 860
    except Exception:
        try:
            page.window_width  = 1280
            page.window_height = 860
        except Exception:
            pass

    # ---- sidebar ----
    sidebar = ft.Container(
        width=64, bgcolor=SIDEBAR_COLOR,
        padding=p_only(top=20, bottom=20, left=8, right=8),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.IconButton(icon=safe_icon("DASHBOARD"),
                               icon_color=ACCENT_BLUE, icon_size=26, tooltip="Dashboard"),
                ft.IconButton(icon=safe_icon("ANALYTICS"),
                               icon_color=ft.colors.GREY_600, icon_size=22, tooltip="Analytics"),
                ft.IconButton(icon=safe_icon("SETTINGS"),
                               icon_color=ft.colors.GREY_600, icon_size=22, tooltip="Settings"),
                ft.Container(expand=True),
                ft.CircleAvatar(content=ft.Text("KS", size=12),
                                 bgcolor=ft.colors.BLUE_GREY_800),
            ],
        )
    )

    # ---- cards ----
    prod_card      = SensorCard("Production Line",  "kg/h",  0,   150, 120, 135)
    temp_card      = SensorCard("Boiler Temp",      "°C",    20,  120,  90, 105)
    pressure_card  = SensorCard("Pressure Vessel",  "psi",   0,   200, 160, 180)
    vibration_card = SensorCard("Vibration",        "mm/s",  0,    50,  35,  45)
    alarm_panel    = AlarmPanel()

    cpu_bar = ft.ProgressBar(value=0.75, color=ACCENT_GREEN, bgcolor="#2D2D2D", expand=True)
    mem_bar = ft.ProgressBar(value=0.45, color=ACCENT_BLUE,  bgcolor="#2D2D2D", expand=True)

    system_health = ft.Container(
        bgcolor=CARD_COLOR, padding=18,
        border_radius=12, border=b_all(1, BORDER_COLOR),
        expand=True,
        content=ft.Column(spacing=10, controls=[
            ft.Text("SYSTEM HEALTH", size=11,
                     color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
            ft.Text("CPU  75%",    size=10, color=ft.colors.GREY_400),
            cpu_bar,
            ft.Text("Memory  45%", size=10, color=ft.colors.GREY_400),
            mem_bar,
        ])
    )

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Real-time Analytics Dashboard", size=22,
                     weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ft.Container(
                bgcolor="#1A1E24", border_radius=20,
                padding=p_only(left=12, right=12, top=4, bottom=4),
                content=ft.Row(spacing=6, controls=[
                    ft.Icon(icon=safe_icon("FIBER_MANUAL_RECORD"),
                             color=ACCENT_GREEN, size=10),
                    ft.Text("Live", size=12, color=ft.colors.GREY_400),
                ]),
            ),
        ]
    )

    main_col = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        expand=True,
        controls=[
            header,
            ft.Row(spacing=16, controls=[prod_card.container, temp_card.container]),
            ft.Row(spacing=16, controls=[pressure_card.container, vibration_card.container]),
            ft.Row(spacing=16, controls=[alarm_panel.container, system_health]),
        ]
    )

    page.add(
        ft.Row(
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                sidebar,
                ft.Container(expand=True, bgcolor=BG_COLOR, padding=24, content=main_col),
            ],
        )
    )
    page.update()

    # ---- background thread ----
    running = True
    t = 0.0

    def loop():
        nonlocal running, t
        while running:
            try:
                t += 0.1
                prod_val      = 100 + 20 * math.sin(t)       + random.uniform(-5, 5)
                temp_val      =  85 + 10 * math.sin(t * 0.5) + random.uniform(-3, 3)
                pressure_val  = 140 + 20 * math.sin(t * 0.3) + random.uniform(-5, 5)
                vibration_val =  30 + 10 * math.sin(t * 2.0) + random.uniform(-5, 5)

                if random.random() > 0.95:
                    temp_val += random.uniform(10, 20)

                prod_card.update_value(prod_val)
                temp_card.update_value(temp_val)
                pressure_card.update_value(pressure_val)
                vibration_card.update_value(vibration_val)

                if temp_val     > temp_card.crit:
                    alarm_panel.add_alarm("High Temperature", temp_val)
                if pressure_val > pressure_card.crit:
                    alarm_panel.add_alarm("High Pressure",    pressure_val)

                page.update()
                time.sleep(0.5)
            except Exception as ex:
                print(f"Update error: {ex}")
                break

    threading.Thread(target=loop, daemon=True).start()

    def on_close(e=None):
        nonlocal running
        running = False

    page.on_close = on_close


if __name__ == "__main__":
    ft.app(target=main)