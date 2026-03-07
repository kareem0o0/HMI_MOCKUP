import flet as ft
import random
import time
import threading
import math
import types
from datetime import datetime, timedelta
from typing import List, Dict
import json

# --- COMPATIBILITY MAPPING ---
if not hasattr(ft, 'colors'):
    ft.colors = ft.Colors
if not hasattr(ft, 'icons'):
    ft.icons = ft.Icons
if not hasattr(ft, "animation"):
    ft.animation = types.SimpleNamespace(Animation=ft.Animation)

HAS_LINE_CHART = all(
    hasattr(ft, name)
    for name in ["LineChart", "LineChartData", "LineChartDataPoint", "ChartGridLines", "ChartAxis"]
)

# --- STYLING ---
BG_COLOR      = "#0D1117"
CARD_COLOR    = "#161B22"
ACCENT_BLUE   = "#58A6FF"
ACCENT_GREEN  = "#3FB950"
ACCENT_RED    = "#F85149"
ACCENT_YELLOW = "#D29922"
ACCENT_PURPLE = "#BF7AF0"
CHART_COLOR   = "#00B4FF"
SIDEBAR_COLOR = "#010409"
BORDER_COLOR  = "#30363D"

def b_all(width, color):
    """Border.all with fallback."""
    try:
        return ft.Border.all(width, color)
    except Exception:
        return ft.border.all(width, color)

def p_only(left=0, right=0, top=0, bottom=0):
    """Padding.only with fallback."""
    try:
        return ft.Padding.only(left=left, right=right, top=top, bottom=bottom)
    except Exception:
        return ft.padding.only(left=left, right=right, top=top, bottom=bottom)

def safe_icon(name: str):
    icon_map = {
        "DASHBOARD": "dashboard",
        "ANALYTICS": "analytics",
        "SETTINGS": "settings",
        "WARNING": "warning",
        "FIBER_MANUAL_RECORD": "fiber_manual_record",
        "HISTORY": "history",
        "DOWNLOAD": "download",
        "REFRESH": "refresh",
        "DELETE": "delete",
        "EDIT": "edit",
        "SAVE": "save",
        "PLAY_ARROW": "play_arrow",
        "PAUSE": "pause",
        "STOP": "stop",
        "NOTIFICATIONS": "notifications",
        "PERSON": "person",
        "LOCK": "lock",
    }
    for src in [ft.Icons, ft.icons if hasattr(ft, "icons") else None]:
        if src and hasattr(src, name):
            return getattr(src, name)
    return icon_map.get(name, "circle")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
class DataLogger:
    """Logs historical data for trending"""
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.data: Dict[str, List[Dict]] = {}
    
    def log(self, sensor_name: str, value: float):
        if sensor_name not in self.data:
            self.data[sensor_name] = []
        
        self.data[sensor_name].append({
            'timestamp': datetime.now(),
            'value': value
        })
        
        # Keep only max_records
        if len(self.data[sensor_name]) > self.max_records:
            self.data[sensor_name].pop(0)
    
    def get_history(self, sensor_name: str, hours: int = 24) -> List[Dict]:
        if sensor_name not in self.data:
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        return [d for d in self.data[sensor_name] if d['timestamp'] > cutoff]

class UserSettings:
    """User preferences and system settings"""
    def __init__(self):
        self.theme = "dark"
        self.refresh_rate = 0.5
        self.alarm_sound = True
        self.temperature_unit = "C"
        self.show_notifications = True

class DataPoint:
    def __init__(self, max_points: int = 20):
        self.max_points = max_points
        self.points: List[float] = [50.0] * max_points
        self.timestamps: List[datetime] = [datetime.now()] * max_points

    def add(self, value: float):
        self.points.pop(0)
        self.timestamps.pop(0)
        self.points.append(float(value))
        self.timestamps.append(datetime.now())

    def avg(self) -> float:
        return sum(self.points) / len(self.points)
    
    def min(self) -> float:
        return min(self.points)
    
    def max(self) -> float:
        return max(self.points)

# ---------------------------------------------------------------------------
# Enhanced Sensor Card
# ---------------------------------------------------------------------------
class SensorCard:
    def __init__(self, title, unit, min_v, max_v, warn, crit, icon="sensors"):
        self.title = title
        self.unit  = unit
        self.min_v = min_v
        self.max_v = max_v
        self.warn  = warn
        self.crit  = crit
        self.data  = DataPoint()
        self.current = 50.0
        self.logger = DataLogger()

        # --- leaf controls we need to update later ---
        self.txt_value = ft.Text(
            f"{self.current:.1f}",
            size=40, weight=ft.FontWeight.BOLD,
            color=ft.colors.WHITE,
        )
        self.txt_unit  = ft.Text(unit, size=14, color=ft.colors.GREY_500)
        self.txt_avg   = ft.Text(f"Avg: {self.data.avg():.1f}", size=10, color=ft.colors.GREY_400)
        self.txt_min   = ft.Text(f"Min: {self.data.min():.1f}", size=10, color=ft.colors.GREY_500)
        self.txt_max   = ft.Text(f"Max: {self.data.max():.1f}", size=10, color=ft.colors.GREY_500)
        self.txt_time  = ft.Text(
            f"Updated: {datetime.now():%H:%M:%S}",
            size=9, color=ft.colors.GREY_700
        )

        # Status dot + label
        self.dot = ft.Container(width=8, height=8, bgcolor=ACCENT_GREEN, border_radius=4)
        self.txt_status = ft.Text("Online", size=11, color=ft.colors.GREY_400)

        # Chart or placeholder
        if HAS_LINE_CHART:
            self.series = ft.LineChartData(
                data_points=[ft.LineChartDataPoint(i, v) for i, v in enumerate(self.data.points)],
                stroke_width=2, color=CHART_COLOR, curved=True,
            )
            chart_widget = ft.LineChart(
                data_series=[self.series],
                border=b_all(0, ft.colors.TRANSPARENT),
                horizontal_grid_lines=ft.ChartGridLines(interval=25, color="#1C2128", width=1),
                vertical_grid_lines=ft.ChartGridLines(interval=5,  color="#1C2128", width=1),
                left_axis=ft.ChartAxis(labels_size=0),
                bottom_axis=ft.ChartAxis(labels_size=0),
                min_y=min_v, max_y=max_v,
                expand=True,
            )
        else:
            self.series = None
            chart_widget = ft.Text(
                "Chart unavailable", size=10, color=ft.colors.GREY_600
            )

        # Outer container
        self.container = ft.Container(
            bgcolor=CARD_COLOR,
            padding=20,
            border_radius=12,
            border=b_all(1, BORDER_COLOR),
            expand=True,
            content=ft.Column(
                spacing=10,
                controls=[
                    # header row with icon
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(controls=[
                                ft.Icon(icon, size=16, color=ft.colors.GREY_400),
                                ft.Text(title.upper(), size=11,
                                        color=ft.colors.GREY_500,
                                        weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Row(controls=[self.dot, self.txt_status], spacing=5),
                        ]
                    ),
                    # value row
                    ft.Row(
                        controls=[self.txt_value, self.txt_unit],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    # stats row
                    ft.Row(
                        controls=[self.txt_min, self.txt_avg, self.txt_max],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    # chart
                    ft.Container(
                        content=chart_widget,
                        height=90,
                        border=b_all(1, BORDER_COLOR),
                        border_radius=8,
                        padding=4,
                        bgcolor="#0A0C10",
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    # timestamp
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self.txt_time,
                            ft.IconButton(
                                icon=safe_icon("HISTORY"),
                                icon_size=14,
                                icon_color=ft.colors.GREY_500,
                                tooltip="View History",
                                on_click=lambda _: print(f"Show history for {title}")
                            )
                        ]
                    )
                ],
            ),
        )

    def update_value(self, new_val: float):
        self.current = max(self.min_v, min(self.max_v, new_val))
        self.data.add(self.current)
        self.logger.log(self.title, self.current)

        self.txt_value.value  = f"{self.current:.1f}"
        self.txt_avg.value    = f"Avg: {self.data.avg():.1f}"
        self.txt_min.value    = f"Min: {self.data.min():.1f}"
        self.txt_max.value    = f"Max: {self.data.max():.1f}"
        self.txt_time.value   = f"Updated: {datetime.now():%H:%M:%S}"

        if self.series is not None:
            self.series.data_points = [
                ft.LineChartDataPoint(i, v)
                for i, v in enumerate(self.data.points)
            ]

        if self.current >= self.crit:
            color, status, border_w = ACCENT_RED,    "Critical", 2
        elif self.current >= self.warn:
            color, status, border_w = ACCENT_YELLOW, "Warning",  2
        else:
            color, status, border_w = ACCENT_GREEN,  "Online",   1

        self.dot.bgcolor        = color
        self.txt_status.value   = status
        self.container.border   = b_all(border_w, color if border_w == 2 else BORDER_COLOR)

# ---------------------------------------------------------------------------
# Enhanced Alarm Panel
# ---------------------------------------------------------------------------
class AlarmPanel:
    def __init__(self):
        self.alarm_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=150)
        self.no_alarms = ft.Text("No active alarms", size=12,
                                  color=ft.colors.GREY_600, italic=True)
        self._items: list = []
        self._acknowledged = set()

        # Controls
        self.ack_all_btn = ft.TextButton(
            content="Acknowledge All",
            icon=safe_icon("CHECK"),
            on_click=self.acknowledge_all,
            visible=False
        )

        self.container = ft.Container(
            bgcolor=CARD_COLOR, padding=20,
            border_radius=12, border=b_all(1, BORDER_COLOR),
            expand=True,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("ACTIVE ALARMS", size=11,
                                     color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
                            self.ack_all_btn,
                        ]
                    ),
                    self.no_alarms,
                ]
            )
        )

    def add_alarm(self, title: str, value: float):
        alarm_id = f"{title}_{datetime.now().timestamp()}"
        
        item = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon=safe_icon("WARNING"), color=ACCENT_RED, size=16),
                ft.Text(f"{title}: {value:.1f}", size=12, color=ft.colors.WHITE, expand=True),
                ft.Text(datetime.now().strftime("%H:%M:%S"), size=9, color=ft.colors.GREY_500),
                ft.IconButton(
                    icon=safe_icon("CHECK"),
                    icon_size=14,
                    icon_color=ft.colors.GREEN_400,
                    tooltip="Acknowledge",
                    on_click=lambda _, i=alarm_id: self.acknowledge_alarm(i)
                )
            ]),
            bgcolor="#2D1517", padding=8, border_radius=6,
            data=alarm_id
        )
        
        self._items.append(item)
        self._items = self._items[-10:]  # Keep last 10
        self.alarm_col.controls = list(self._items)

        col: ft.Column = self.container.content
        if self.no_alarms in col.controls:
            col.controls.remove(self.no_alarms)
        if self.alarm_col not in col.controls:
            col.controls.append(self.alarm_col)
        
        self.ack_all_btn.visible = len(self._items) > 0
        self.update()

    def acknowledge_alarm(self, alarm_id):
        self._acknowledged.add(alarm_id)
        self._items = [i for i in self._items if i.data not in self._acknowledged]
        self.alarm_col.controls = self._items
        
        if not self._items:
            col: ft.Column = self.container.content
            if self.alarm_col in col.controls:
                col.controls.remove(self.alarm_col)
            if self.no_alarms not in col.controls:
                col.controls.append(self.no_alarms)
            self.ack_all_btn.visible = False
        
        self.update()

    def acknowledge_all(self, e=None):
        for item in self._items:
            self._acknowledged.add(item.data)
        self._items.clear()
        self.alarm_col.controls.clear()
        
        col: ft.Column = self.container.content
        if self.alarm_col in col.controls:
            col.controls.remove(self.alarm_col)
        if self.no_alarms not in col.controls:
            col.controls.append(self.no_alarms)
        
        self.ack_all_btn.visible = False
        self.update()

# ---------------------------------------------------------------------------
# Pages / Views
# ---------------------------------------------------------------------------
class DashboardPage:
    def __init__(self, sensors, alarm_panel, system_health):
        self.sensors = sensors
        self.alarm_panel = alarm_panel
        self.system_health = system_health
        
        # Header
        self.header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Real-time Analytics Dashboard",
                         size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                ft.Row(spacing=10, controls=[
                    ft.Container(
                        bgcolor="#1A1E24", border_radius=20,
                        padding=p_only(left=12, right=12, top=4, bottom=4),
                        content=ft.Row(spacing=6, controls=[
                            ft.Icon(icon=safe_icon("FIBER_MANUAL_RECORD"),
                                     color=ACCENT_GREEN, size=10),
                            ft.Text("Live", size=12, color=ft.colors.GREY_400),
                        ]),
                    ),
                    ft.IconButton(
                        icon=safe_icon("REFRESH"),
                        icon_color=ft.colors.GREY_400,
                        icon_size=18,
                        tooltip="Refresh",
                        on_click=self.refresh_data
                    )
                ])
            ]
        )
        
        # Quick KPI Row
        self.kpi_production = ft.Text("0.0", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        self.kpi_alarms = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ACCENT_GREEN)
        self.kpi_health = ft.Text("Good", size=24, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
        
        self.quick_kpis = ft.Row(
            spacing=16,
            controls=[
                self._build_kpi_card("Total Production", self.kpi_production, "factory"),
                self._build_kpi_card("Active Alarms", self.kpi_alarms, "warning"),
                self._build_kpi_card("System Status", self.kpi_health, "favorite"),
            ]
        )

        scrollable_content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True,
            controls=[
                self.quick_kpis,
                ft.Row(spacing=16, controls=[
                    sensors['prod'].container,
                    sensors['temp'].container,
                ]),
                ft.Row(spacing=16, controls=[
                    sensors['pressure'].container,
                    sensors['vibration'].container,
                ]),
                ft.Row(spacing=16, controls=[
                    sensors['flow'].container,
                    sensors['level'].container,
                ]),
                ft.Row(spacing=16, controls=[
                    alarm_panel.container,
                    system_health.container,
                ]),
            ]
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(self.header, padding=p_only(top=30, left=30, right=30, bottom=20)),
                ft.Container(scrollable_content, padding=p_only(left=30, right=30, bottom=30), expand=True)
            ]
        )

    def _build_kpi_card(self, title, control, icon):
        return ft.Container(
            expand=True,
            bgcolor=CARD_COLOR,
            padding=20,
            border_radius=12,
            border=b_all(1, BORDER_COLOR),
            content=ft.Row(
                spacing=15,
                controls=[
                    ft.Container(
                        padding=12,
                        bgcolor="#1C2128",
                        border_radius=8,
                        content=ft.Icon(safe_icon(icon), size=28, color=ACCENT_BLUE)
                    ),
                    ft.Column([
                        ft.Text(title.upper(), size=12, color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
                        control
                    ], spacing=2)
                ]
            )
        )

    def update_kpis(self):
        # Update Production
        self.kpi_production.value = f"{self.sensors['prod'].current:.1f} kg/h"
        
        # Update Alarms
        alarm_count = len(self.alarm_panel._items)
        self.kpi_alarms.value = str(alarm_count)
        if alarm_count > 0:
            self.kpi_alarms.color = ACCENT_RED
            self.kpi_health.value = "Warning"
            self.kpi_health.color = ACCENT_YELLOW
        else:
            self.kpi_alarms.color = ACCENT_GREEN
            self.kpi_health.value = "Optimal"
            self.kpi_health.color = ACCENT_BLUE
    
    def refresh_data(self, e=None):
        # Force update all sensors
        for sensor in self.sensors.values():
            sensor.update_value(sensor.current + random.uniform(-2, 2))

class AnalyticsPage:
    def __init__(self, sensors):
        self.sensors = sensors

        # Header
        self.header = ft.Text("Analytics & Trends", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        
        scrollable_content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True,
            controls=[
                ft.Text("Overview", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                self._build_overview(),
                ft.Text("Trends", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                self._build_trends(),
                ft.Text("Statistics", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                self._build_statistics(),
            ]
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(self.header, padding=p_only(top=30, left=30, right=30, bottom=20)),
                ft.Container(scrollable_content, padding=p_only(left=30, right=30, bottom=30), expand=True)
            ]
        )
    
    def _build_overview(self):
        # Create mini charts for all sensors
        charts = []
        for name, sensor in self.sensors.items():
            if HAS_LINE_CHART:
                chart = ft.LineChart(
                    data_series=[
                        ft.LineChartData(
                            data_points=[ft.LineChartDataPoint(i, v) for i, v in enumerate(sensor.data.points[-50:])],
                            stroke_width=2,
                            color=CHART_COLOR,
                        )
                    ],
                    width=300,
                    height=150,
                )
                charts.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(name.upper(), size=12, color=ft.colors.GREY_400),
                            chart,
                        ]),
                        bgcolor=CARD_COLOR,
                        padding=15,
                        border_radius=12,
                        border=b_all(1, BORDER_COLOR),
                    )
                )
        
        return ft.GridView(
            controls=charts,
            runs_count=2,
            spacing=10,
            run_spacing=10,
            padding=10,
        )
    
    def _build_trends(self):
        # Time range selector
        time_range = ft.Dropdown(
            options=[
                ft.dropdown.Option("1h", "Last Hour"),
                ft.dropdown.Option("24h", "Last 24 Hours"),
                ft.dropdown.Option("7d", "Last 7 Days"),
                ft.dropdown.Option("30d", "Last 30 Days"),
            ],
            value="24h",
            width=200,
        )
        
        sensor_selector = ft.Dropdown(
            options=[
                ft.dropdown.Option("prod", "Production Line"),
                ft.dropdown.Option("temp", "Boiler Temperature"),
                ft.dropdown.Option("pressure", "Pressure"),
                ft.dropdown.Option("vibration", "Vibration"),
                ft.dropdown.Option("flow", "Flow Rate"),
                ft.dropdown.Option("level", "Tank Level"),
            ],
            value="prod",
            width=200,
        )
        
        return ft.Column([
            ft.Row([time_range, sensor_selector], spacing=10),
            ft.Container(
                content=ft.Text("Trend chart will appear here", color=ft.colors.GREY_400),
                bgcolor=CARD_COLOR,
                padding=20,
                border_radius=12,
                border=b_all(1, BORDER_COLOR),
                height=400,
                alignment=ft.Alignment(0, 0),
            )
        ])
    
    def _build_statistics(self):
        stats_cards = []
        for name, sensor in self.sensors.items():
            card = ft.Container(
                content=ft.Column([
                    ft.Text(name.upper(), size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1, color=BORDER_COLOR),
                    ft.Text(f"Current: {sensor.current:.1f} {sensor.unit}", size=12),
                    ft.Text(f"Average: {sensor.data.avg():.1f} {sensor.unit}", size=12),
                    ft.Text(f"Minimum: {sensor.data.min():.1f} {sensor.unit}", size=12),
                    ft.Text(f"Maximum: {sensor.data.max():.1f} {sensor.unit}", size=12),
                    ft.ProgressBar(value=sensor.current/sensor.max_v, color=ACCENT_BLUE),
                ], spacing=8),
                bgcolor=CARD_COLOR,
                padding=15,
                border_radius=12,
                border=b_all(1, BORDER_COLOR),
                width=200,
            )
            stats_cards.append(card)
        
        return ft.ResponsiveRow(
            controls=stats_cards,
            spacing=10,
            run_spacing=10,
        )

class SettingsPage:
    def __init__(self, settings: UserSettings):
        self.settings = settings
        
        # Create settings controls
        self.theme_switch = ft.Switch(
            label="Dark Mode",
            value=settings.theme == "dark",
            on_change=self.toggle_theme
        )
        
        self.refresh_slider = ft.Slider(
            min=0.1,
            max=2.0,
            value=settings.refresh_rate,
            label="{value}s",
            divisions=19,
            on_change=self.update_refresh_rate
        )
        
        self.alarm_switch = ft.Switch(
            label="Alarm Sound",
            value=settings.alarm_sound,
            on_change=self.toggle_alarm_sound
        )
        
        self.temp_unit = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="C", label="Celsius"),
                ft.Radio(value="F", label="Fahrenheit"),
            ]),
            value=settings.temperature_unit,
            on_change=self.change_temp_unit
        )
        
        self.notification_switch = ft.Switch(
            label="Show Notifications",
            value=settings.show_notifications,
            on_change=self.toggle_notifications
        )
        
        self.header = ft.Text("Settings", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        
        scrollable_content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True,
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Text("Appearance", size=16, color=ft.colors.GREY_300),
                        self.theme_switch,
                        ft.Divider(height=1, color=BORDER_COLOR),
                        
                        ft.Text("Performance", size=16, color=ft.colors.GREY_300),
                        ft.Text("Refresh Rate (seconds)", size=12, color=ft.colors.GREY_400),
                        self.refresh_slider,
                        ft.Divider(height=1, color=BORDER_COLOR),
                        
                        ft.Text("Alarms", size=16, color=ft.colors.GREY_300),
                        self.alarm_switch,
                        ft.Divider(height=1, color=BORDER_COLOR),
                        
                        ft.Text("Units", size=16, color=ft.colors.GREY_300),
                        self.temp_unit,
                        ft.Divider(height=1, color=BORDER_COLOR),
                        
                        ft.Text("Notifications", size=16, color=ft.colors.GREY_300),
                        self.notification_switch,
                    ], spacing=15),
                    bgcolor=CARD_COLOR,
                    padding=20,
                    border_radius=12,
                    border=b_all(1, BORDER_COLOR),
                    width=500,
                ),
                
                ft.Row([
                    ft.ElevatedButton(
                        "Save Settings",
                        icon=safe_icon("SAVE"),
                        on_click=self.save_settings
                    ),
                    ft.OutlinedButton(
                        "Reset to Defaults",
                        icon=safe_icon("REFRESH"),
                        on_click=self.reset_settings
                    ),
                ]),
            ]
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(self.header, padding=p_only(top=30, left=30, right=30, bottom=20)),
                ft.Container(scrollable_content, padding=p_only(left=30, right=30, bottom=30), expand=True)
            ]
        )
    
    def toggle_theme(self, e):
        self.settings.theme = "dark" if e.control.value else "light"
    
    def update_refresh_rate(self, e):
        self.settings.refresh_rate = e.control.value
    
    def toggle_alarm_sound(self, e):
        self.settings.alarm_sound = e.control.value
    
    def change_temp_unit(self, e):
        self.settings.temperature_unit = e.control.value
    
    def toggle_notifications(self, e):
        self.settings.show_notifications = e.control.value
    
    def save_settings(self, e):
        # In a real app, save to file/database
        print("Settings saved:", vars(self.settings))
    
    def reset_settings(self, e):
        self.settings = UserSettings()
        # Update UI controls
        self.theme_switch.value = self.settings.theme == "dark"
        self.refresh_slider.value = self.settings.refresh_rate
        self.alarm_switch.value = self.settings.alarm_sound
        self.temp_unit.value = self.settings.temperature_unit
        self.notification_switch.value = self.settings.show_notifications
        self.update()

class AlarmsPage:
    def __init__(self, alarm_panel):
        self.alarm_panel = alarm_panel
        
        # Alarm history
        self.history_list = ft.ListView(spacing=5, height=400)
        
        self.header = ft.Text("Alarm Management", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        
        scrollable_content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True,
            controls=[
                ft.Text("Active Alarms", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                ft.Container(content=self.alarm_panel.container, padding=10),
                ft.Text("Alarm History", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                ft.Container(content=self.history_list, padding=10),
                ft.Text("Alarm Configuration", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300),
                self._build_config(),
            ]
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(self.header, padding=p_only(top=30, left=30, right=30, bottom=20)),
                ft.Container(scrollable_content, padding=p_only(left=30, right=30, bottom=30), expand=True)
            ]
        )
        
        # Add some sample history
        self._add_sample_history()
    
    def _build_config(self):
        return ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("Temperature High", size=14, weight=ft.FontWeight.BOLD),
                    ft.Slider(min=50, max=150, value=90, divisions=20, label="{value}°C"),
                    ft.Switch(label="Enable", value=True),
                ], spacing=10),
                bgcolor=CARD_COLOR,
                padding=15,
                border_radius=12,
                border=b_all(1, BORDER_COLOR),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Pressure High", size=14, weight=ft.FontWeight.BOLD),
                    ft.Slider(min=100, max=250, value=160, divisions=15, label="{value} psi"),
                    ft.Switch(label="Enable", value=True),
                ], spacing=10),
                bgcolor=CARD_COLOR,
                padding=15,
                border_radius=12,
                border=b_all(1, BORDER_COLOR),
            ),
        ], spacing=10)
    
    def _add_sample_history(self):
        for i in range(20):
            self.history_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), size=11),
                        ft.Text(f"Temperature High: {85 + i}°C", size=11),
                        ft.Text("Acknowledged", size=11, color=ft.colors.GREEN_400),
                    ]),
                    padding=8,
                    bgcolor=CARD_COLOR if i % 2 == 0 else "#1E2329",
                )
            )

class SystemHealth:
    def __init__(self):
        # System metrics
        self.cpu_bar = ft.ProgressBar(value=0.75, color=ACCENT_GREEN, bgcolor="#2D2D2D")
        self.mem_bar = ft.ProgressBar(value=0.45, color=ACCENT_BLUE, bgcolor="#2D2D2D")
        self.disk_bar = ft.ProgressBar(value=0.32, color=ACCENT_YELLOW, bgcolor="#2D2D2D")
        self.network_bar = ft.ProgressBar(value=0.15, color=ACCENT_PURPLE, bgcolor="#2D2D2D")
        
        self.cpu_text = ft.Text("CPU: 75%", size=10, color=ft.colors.GREY_400)
        self.mem_text = ft.Text("Memory: 45%", size=10, color=ft.colors.GREY_400)
        self.disk_text = ft.Text("Disk: 32%", size=10, color=ft.colors.GREY_400)
        self.network_text = ft.Text("Network: 15%", size=10, color=ft.colors.GREY_400)
        
        self.uptime_text = ft.Text("Uptime: 14d 7h 23m", size=10, color=ft.colors.GREY_400)
        
        self.container = ft.Container(
            bgcolor=CARD_COLOR, padding=20,
            border_radius=12, border=b_all(1, BORDER_COLOR),
            expand=True,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("SYSTEM HEALTH", size=11,
                             color=ft.colors.GREY_500, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Icon(icon="memory", size=14, color=ft.colors.GREY_400),
                        ft.Text("CPU", size=10, color=ft.colors.GREY_400, expand=True),
                        self.cpu_text,
                    ]),
                    self.cpu_bar,
                    ft.Row([
                        ft.Icon(icon="storage", size=14, color=ft.colors.GREY_400),
                        ft.Text("Memory", size=10, color=ft.colors.GREY_400, expand=True),
                        self.mem_text,
                    ]),
                    self.mem_bar,
                    ft.Row([
                        ft.Icon(icon="hard_drive", size=14, color=ft.colors.GREY_400),
                        ft.Text("Disk", size=10, color=ft.colors.GREY_400, expand=True),
                        self.disk_text,
                    ]),
                    self.disk_bar,
                    ft.Row([
                        ft.Icon(icon="wifi", size=14, color=ft.colors.GREY_400),
                        ft.Text("Network", size=10, color=ft.colors.GREY_400, expand=True),
                        self.network_text,
                    ]),
                    self.network_bar,
                    ft.Divider(height=1, color=BORDER_COLOR),
                    ft.Row([
                        ft.Icon(icon="schedule", size=14, color=ft.colors.GREY_400),
                        self.uptime_text,
                    ]),
                ]
            )
        )
    
    def update_metrics(self):
        # Simulate changing metrics
        self.cpu_bar.value = random.uniform(0.3, 0.9)
        self.mem_bar.value = random.uniform(0.3, 0.7)
        self.disk_bar.value = random.uniform(0.2, 0.5)
        self.network_bar.value = random.uniform(0.1, 0.4)
        
        self.cpu_text.value = f"CPU: {self.cpu_bar.value*100:.0f}%"
        self.mem_text.value = f"Memory: {self.mem_bar.value*100:.0f}%"
        self.disk_text.value = f"Disk: {self.disk_bar.value*100:.0f}%"
        self.network_text.value = f"Network: {self.network_bar.value*100:.0f}%"
        self.update()

# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    page.title       = "Industrial HMI Dashboard Pro"
    page.bgcolor     = BG_COLOR
    page.padding     = 0
    page.theme_mode  = ft.ThemeMode.DARK
    page.scroll      = ft.ScrollMode.HIDDEN

    # Window size
    try:
        page.window.width  = 1400
        page.window.height = 900
    except Exception:
        try:
            page.window_width  = 1400
            page.window_height = 900
        except Exception:
            pass

    # Initialize settings
    settings = UserSettings()

    # ---- Create sensors ----
    sensors = {
        'prod': SensorCard("Production Line",  "kg/h",  0,   150, 120, 135, "factory"),
        'temp': SensorCard("Boiler Temp",      "°C",    20,  120,  90, 105, "thermostat"),
        'pressure': SensorCard("Pressure Vessel",  "psi",   0,   200, 160, 180, "compress"),
        'vibration': SensorCard("Vibration",        "mm/s",  0,    50,  35,  45, "vibration"),
        'flow': SensorCard("Flow Rate",        "L/min", 0,   100,  80,  95, "water_drop"),
        'level': SensorCard("Tank Level",       "%",     0,   100,  85,  95, "opacity"),
    }

    # ---- Create panels ----
    alarm_panel = AlarmPanel()
    system_health = SystemHealth()

    # ---- Create pages ----
    dashboard = DashboardPage(sensors, alarm_panel, system_health)
    analytics = AnalyticsPage(sensors)
    alarms_page = AlarmsPage(alarm_panel)
    settings_page = SettingsPage(settings)

    # ---- Navigation rail (enhanced sidebar) ----
    def navigate_to(page_index):
        content_area.content = pages[page_index].content
        for i, btn in enumerate(nav_buttons):
            btn.icon_color = ACCENT_BLUE if i == page_index else ft.colors.GREY_600
        page.update()

    nav_buttons = [
        ft.IconButton(
            icon=safe_icon("DASHBOARD"),
            icon_color=ACCENT_BLUE,
            icon_size=26,
            tooltip="Dashboard",
            on_click=lambda _: navigate_to(0)
        ),
        ft.IconButton(
            icon=safe_icon("ANALYTICS"),
            icon_color=ft.colors.GREY_600,
            icon_size=22,
            tooltip="Analytics",
            on_click=lambda _: navigate_to(1)
        ),
        ft.IconButton(
            icon=safe_icon("NOTIFICATIONS"),
            icon_color=ft.colors.GREY_600,
            icon_size=22,
            tooltip="Alarms",
            on_click=lambda _: navigate_to(2)
        ),
        ft.IconButton(
            icon=safe_icon("SETTINGS"),
            icon_color=ft.colors.GREY_600,
            icon_size=22,
            tooltip="Settings",
            on_click=lambda _: navigate_to(3)
        ),
    ]

    sidebar = ft.Container(
        width=70,
        bgcolor=SIDEBAR_COLOR,
        padding=p_only(top=20, bottom=20, left=8, right=8),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Icon(safe_icon("widgets"), size=32, color=ACCENT_BLUE),
                ft.Divider(height=1, color=BORDER_COLOR),
                *nav_buttons,
                ft.Container(expand=True),
                ft.CircleAvatar(
                    content=ft.Text("KS", size=12),
                    bgcolor=ft.colors.BLUE_GREY_800,
                    tooltip="User Profile"
                ),
            ]
        )
    )

    # Pages list
    pages = [dashboard, analytics, alarms_page, settings_page]

    # Main content area
    content_area = ft.Container(
        expand=True,
        bgcolor=BG_COLOR,
        content=pages[0].content,
    )

    # Add to page
    page.add(
        ft.Row(
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[sidebar, content_area],
        )
    )
    page.update()

    # ---- Background updater ----
    running = True
    t = 0.0

    def update_loop():
        nonlocal running, t
        while running:
            try:
                t += 0.1

                # Update sensor values
                prod_val      = 100 + 20 * math.sin(t)          + random.uniform(-5,  5)
                temp_val      =  85 + 10 * math.sin(t * 0.5)    + random.uniform(-3,  3)
                pressure_val  = 140 + 20 * math.sin(t * 0.3)    + random.uniform(-5,  5)
                vibration_val =  30 + 10 * math.sin(t * 2.0)    + random.uniform(-5,  5)
                flow_val      =  70 + 15 * math.sin(t * 0.8)    + random.uniform(-4,  4)
                level_val     =  65 + 10 * math.cos(t * 0.4)    + random.uniform(-2,  2)

                # Occasional spikes
                if random.random() > 0.95:
                    temp_val += random.uniform(10, 20)
                if random.random() > 0.97:
                    pressure_val += random.uniform(20, 30)

                # Update all sensors
                sensors['prod'].update_value(prod_val)
                sensors['temp'].update_value(temp_val)
                sensors['pressure'].update_value(pressure_val)
                sensors['vibration'].update_value(vibration_val)
                sensors['flow'].update_value(flow_val)
                sensors['level'].update_value(level_val)

                # Update system health metrics
                system_health.update_metrics()

                # Check for alarms
                if temp_val > sensors['temp'].crit:
                    alarm_panel.add_alarm("High Temperature", temp_val)
                if pressure_val > sensors['pressure'].crit:
                    alarm_panel.add_alarm("High Pressure", pressure_val)
                if flow_val > sensors['flow'].crit:
                    alarm_panel.add_alarm("High Flow Rate", flow_val)
                if level_val > sensors['level'].crit:
                    alarm_panel.add_alarm("High Tank Level", level_val)

                # Update KPIs on dashboard
                dashboard.update_kpis()

                page.update()
                time.sleep(settings.refresh_rate)

            except Exception as ex:
                print(f"Update error: {ex}")
                break

    threading.Thread(target=update_loop, daemon=True).start()

    def on_close(e=None):
        nonlocal running
        running = False

    page.on_close = on_close


if __name__ == "__main__":
    ft.run(main)
