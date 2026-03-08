"""Page builders for the HMI interface."""

import collections, random
from datetime import datetime
import flet as ft
import flet.canvas as cv

from models import (
    C, STATUS_COLOR, SENSORS, ALARMS, ALARM_HISTORY, ACTIVE_ALARMS,
    ALM_COL, DASH_HIST, HISTORY_LEN, _duration_text, _severity_label, alarm_history_row
)
from ui_components import (
    card, hdr, badge, divider, value_row,
    draw_spark, draw_line_chart, draw_arc, draw_ring_meter
)


def make_clickable_card(c: ft.Container, on_open_detail=None, detail_key: str = ""):
    if on_open_detail and detail_key:
        c.ink = True
        c.on_click = lambda e, k=detail_key: on_open_detail(k)
    return c


DETAIL_META = {
    "db_power": ("Power Output", "kW", C["teal"], "Fuel cell electrical output"),
    "db_h2": ("Hydrogen Consumption", "kg/h", C["amber"], "Hydrogen use and fuel autonomy"),
    "db_eff": ("System Efficiency", "%", C["green"], "Electrical and conversion efficiency"),
    "db_health": ("System Health", "score", C["blue"], "Operational health indicators"),
    "db_tanks": ("Hydrogen Tank Levels", "%", C["teal"], "Tank level and fuel availability"),
    "db_tr_power_kw": ("Power Trend", "kW", C["teal"], "Power trend over time"),
    "db_tr_h2_rate": ("Hydrogen Trend", "kg/h", C["amber"], "Hydrogen consumption trend"),
    "db_tr_efficiency": ("Efficiency Trend", "%", C["green"], "Efficiency trend over time"),
    "ana_stats": ("Sensor Statistics", "mixed", C["blue"], "Detailed sensor statistics"),
    "sys_health": ("System Health Overview", "score", C["green"], "System service health"),
    "sys_devices": ("Device Status", "count", C["teal"], "Device state and availability"),
    "sys_alarm": ("System Alarm Log", "events", C["amber"], "Recent alarm events"),
    "net_config": ("Network Configuration", "state", C["teal"], "Configured IoT link parameters"),
    "net_status": ("Network Link Status", "%", C["green"], "Connection and signal quality"),
    "net_plc": ("PLC Communication", "state", C["amber"], "Fieldbus and controller link diagnostics"),
}

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
    range_sel_ref = ft.Ref[ft.Dropdown]()

    refs["sd_sensor_key"] = sensor_key
    refs["sd_val"] = val_ref
    refs["sd_st_dot"] = st_dot_ref
    refs["sd_st_txt"] = st_txt_ref
    refs["sd_min"] = min_ref
    refs["sd_max"] = max_ref
    refs["sd_avg"] = avg_ref
    refs["sd_plot"] = plot_ref
    refs["sd_alarm_col"] = alarm_ref
    refs["sd_range_sel"] = range_sel_ref

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
            ft.Row([
                hdr("SHOW_CHART", "Historical Trend"),
                ft.Container(expand=True),
                ft.Dropdown(
                    ref=range_sel_ref,
                    value="Last Minute",
                    width=190,
                    dense=True,
                    options=[
                        ft.dropdown.Option("From Start"),
                        ft.dropdown.Option("Last Year"),
                        ft.dropdown.Option("Last Month"),
                        ft.dropdown.Option("Last Week"),
                        ft.dropdown.Option("Last Day"),
                        ft.dropdown.Option("Last Hour"),
                        ft.dropdown.Option("Last Minute"),
                    ],
                    border_color=C["border"],
                    bgcolor=C["card2"],
                    color=C["white"],
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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


def build_dashboard(refs: dict, on_open_detail=None):
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

    power_card = make_clickable_card(card(ft.Column([
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
    ]), expand=True), on_open_detail, "db_power")

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

    h2_card = make_clickable_card(card(ft.Column([
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
    ]), expand=True), on_open_detail, "db_h2")

    # Efficiency and performance
    elec_eff_ref = ft.Ref[ft.Text]()
    conv_eff_ref = ft.Ref[ft.Text]()
    pr_ref = ft.Ref[ft.Text]()
    eff_sp_ref = ft.Ref[ft.Row]()
    refs["db_fc_elec_eff"] = elec_eff_ref
    refs["db_fc_conv_eff"] = conv_eff_ref
    refs["db_fc_pr"] = pr_ref
    refs["db_fc_eff_sp"] = eff_sp_ref

    eff_card = make_clickable_card(card(ft.Column([
        hdr("AUTO_GRAPH", "System Efficiency"),
        ft.Container(height=8),
        value_row("Electrical Efficiency", elec_eff_ref, "%", color=C["green"], val_size=18),
        ft.Container(height=6),
        value_row("Conversion Efficiency", conv_eff_ref, "%", color=C["teal"], val_size=18),
        ft.Container(height=6),
        value_row("Performance Ratio", pr_ref, "%", color=C["blue"], val_size=18),
        ft.Container(height=8),
        ft.Row([draw_spark(DASH_HIST["efficiency"], w=220, h=44, color=C["green"])], ref=eff_sp_ref),
    ]), expand=True), on_open_detail, "db_eff")

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

    # Dual H2 tank rings
    t1_pct_ref = ft.Ref[ft.Text]()
    t1_ring_ref = ft.Ref[ft.Row]()
    t1_vol_ref = ft.Ref[ft.Text]()
    t2_pct_ref = ft.Ref[ft.Text]()
    t2_ring_ref = ft.Ref[ft.Row]()
    t2_vol_ref = ft.Ref[ft.Text]()
    refs["db_fc_t1_pct"] = t1_pct_ref
    refs["db_fc_t1_ring"] = t1_ring_ref
    refs["db_fc_t1_vol"] = t1_vol_ref
    refs["db_fc_t2_pct"] = t2_pct_ref
    refs["db_fc_t2_ring"] = t2_ring_ref
    refs["db_fc_t2_vol"] = t2_vol_ref

    def _alpha(col, a):
        return f"{col}{a}" if len(col) == 7 else col

    def tank_ring(label, pct_ref, ring_ref, vol_ref):
        ring_size = 116
        return ft.Column([
            ft.Stack([
                ft.Container(
                    width=ring_size + 12, height=ring_size + 12,
                    border_radius=(ring_size + 12) / 2,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, -1),
                        end=ft.Alignment(1, 1),
                        colors=[_alpha(C["teal"], "2"), _alpha(C["gray2"], "10")],
                    ),
                ),
                ft.Row([draw_ring_meter(1.0, size=ring_size, stroke=12, color=C["green"])],
                       ref=ring_ref,
                       width=ring_size, height=ring_size,
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(
                    width=ring_size, height=ring_size,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column([
                        ft.Text("100%", ref=pct_ref, color=C["white"], size=18,
                                weight=ft.FontWeight.BOLD),
                        ft.Text(label, color=C["gray"], size=10,
                                weight=ft.FontWeight.W_600),
                    ], spacing=1, alignment=ft.MainAxisAlignment.CENTER,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ),
            ], width=ring_size, height=ring_size),
            ft.Text("", ref=vol_ref, color=C["gray"], size=10),
        ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    tanks_card = make_clickable_card(card(ft.Column([
        hdr("PROPANE_TANK", "Hydrogen Tank Levels"),
        ft.Container(height=8),
        ft.Row([
            tank_ring("H2 Tank 1", t1_pct_ref, t1_ring_ref, t1_vol_ref),
            ft.Container(width=18),
            tank_ring("H2 Tank 2", t2_pct_ref, t2_ring_ref, t2_vol_ref),
        ], alignment=ft.MainAxisAlignment.CENTER),
    ]), expand=True), on_open_detail, "db_tanks")

    # Fuel-cell trend monitoring (split into dedicated metric cards)
    def trend_metric_card(key, title, unit, color, y_label):
        val_ref = ft.Ref[ft.Text]()
        plot_ref = ft.Ref[ft.Row]()
        refs[f"db_tr_{key}_val"] = val_ref
        refs[f"db_tr_{key}_plot"] = plot_ref
        return make_clickable_card(card(ft.Column([
            hdr("SHOW_CHART", title, f"last {HISTORY_LEN}s"),
            ft.Container(height=8),
            ft.Row([
                ft.Text("-", ref=val_ref, color=C["white"], size=24,
                        weight=ft.FontWeight.BOLD),
                ft.Text(unit, color=C["gray"], size=11),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
            ft.Container(height=6),
            ft.Row([
                ft.Text(f"Y: {y_label}", color=C["gray"], size=9),
                ft.Container(expand=True),
                ft.Text("X: time", color=C["gray"], size=9),
            ]),
            ft.Container(height=6),
            ft.Row([
                ft.Row([
                    draw_line_chart([(DASH_HIST[key], color)], w=280, h=170)
                ], ref=plot_ref, alignment=ft.MainAxisAlignment.CENTER),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ]), expand=True), on_open_detail, f"db_tr_{key}")

    trend_power_card = trend_metric_card("power_kw", "Power Output Trend", "kW", C["teal"], "kW")
    trend_h2_card = trend_metric_card("h2_rate", "Hydrogen Consumption Trend", "kg/h", C["amber"], "kg/h")
    trend_eff_card = trend_metric_card("efficiency", "Efficiency Trend", "%", C["green"], "%")

    return ft.Column([
        ft.Row([power_card, h2_card, eff_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([health_card, tanks_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([trend_power_card, trend_h2_card, trend_eff_card], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


# â”€â”€ PAGE 2: Sensors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_sensors(refs: dict):
    return build_sensor_panel(refs)


# â”€â”€ PAGE 3: Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_analytics(refs: dict, on_open_detail=None):
    """
    Simplified analytics page: Sensor Statistics only.
    """
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

    stats_card = make_clickable_card(card(ft.Column([
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
    ], spacing=6)), on_open_detail, "ana_stats")

    return ft.Column([
        ft.Row([stats_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


# â”€â”€ PAGE 4: System Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_system(refs: dict, on_open_detail=None, on_open_network=None, on_open_alarms=None):
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

    tiles = []
    for i, (lbl, ico, col, fn) in enumerate(health_keys):
        tile = health_tile(lbl, ico, col, fn, ht_refs[i])
        if lbl == "Network" and on_open_network:
            tile.ink = True
            tile.on_click = lambda e, cb=on_open_network: cb()
        tiles.append(tile)
    health_row = ft.Row(tiles, spacing=12)

    # Device status table
    devices = [
        ("Unit 1",      "ONLINE",  C["green"]),
        ("Unit 2",      "ONLINE",  C["green"]),
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

    device_card = make_clickable_card(card(ft.Column([
        hdr("DEVELOPER_BOARD", "Device Status"),
        ft.Container(height=8),
        ft.Column(dev_rows, spacing=8),
    ]), expand=True), on_open_detail, "sys_devices")

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
    if on_open_alarms:
        alarm_card.ink = True
        alarm_card.on_click = lambda e, cb=on_open_alarms: cb()

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


def build_card_detail(refs: dict, detail_key: str, on_back, on_open_sensor=None):
    overview_card_ref = ft.Ref[ft.Container]()
    title_ref = ft.Ref[ft.Text]()
    subtitle_ref = ft.Ref[ft.Text]()
    value_ref = ft.Ref[ft.Text]()
    unit_ref = ft.Ref[ft.Text]()
    min_ref = ft.Ref[ft.Text]()
    max_ref = ft.Ref[ft.Text]()
    avg_ref = ft.Ref[ft.Text]()
    status_dot_ref = ft.Ref[ft.Container]()
    status_txt_ref = ft.Ref[ft.Text]()
    plot_card_ref = ft.Ref[ft.Container]()
    plot_ref = ft.Ref[ft.Row]()
    diag_ref = ft.Ref[ft.Column]()
    events_ref = ft.Ref[ft.Column]()
    stats_card_ref = ft.Ref[ft.Container]()
    stats_rows_ref = ft.Ref[ft.Column]()
    devices_card_ref = ft.Ref[ft.Container]()
    devices_rows_ref = ft.Ref[ft.Column]()
    eff_plots_card_ref = ft.Ref[ft.Container]()
    eff_ele_row_ref = ft.Ref[ft.Row]()
    eff_conv_row_ref = ft.Ref[ft.Row]()
    eff_pr_row_ref = ft.Ref[ft.Row]()
    range_bar_ref = ft.Ref[ft.Container]()
    range_sel_ref = ft.Ref[ft.Dropdown]()

    refs["cd_key"] = detail_key
    refs["cd_overview_card"] = overview_card_ref
    refs["cd_title"] = title_ref
    refs["cd_subtitle"] = subtitle_ref
    refs["cd_value"] = value_ref
    refs["cd_unit"] = unit_ref
    refs["cd_min"] = min_ref
    refs["cd_max"] = max_ref
    refs["cd_avg"] = avg_ref
    refs["cd_status_dot"] = status_dot_ref
    refs["cd_status_txt"] = status_txt_ref
    refs["cd_plot_card"] = plot_card_ref
    refs["cd_plot"] = plot_ref
    refs["cd_diag_col"] = diag_ref
    refs["cd_events_col"] = events_ref
    refs["cd_stats_card"] = stats_card_ref
    refs["cd_stats_rows"] = stats_rows_ref
    refs["cd_devices_card"] = devices_card_ref
    refs["cd_devices_rows"] = devices_rows_ref
    refs["cd_eff_plots_card"] = eff_plots_card_ref
    refs["cd_eff_ele_row"] = eff_ele_row_ref
    refs["cd_eff_conv_row"] = eff_conv_row_ref
    refs["cd_eff_pr_row"] = eff_pr_row_ref
    refs["cd_range_bar"] = range_bar_ref
    refs["cd_range_sel"] = range_sel_ref
    refs["cd_open_sensor_cb"] = on_open_sensor

    meta = DETAIL_META.get(detail_key, ("Card Detail", "", C["teal"], "Detailed drill-down view"))
    no_overview_keys = {"ana_stats", "sys_devices", "net_config", "net_plc"}
    show_overview = detail_key not in no_overview_keys
    show_stats_card = detail_key == "ana_stats"
    show_devices_card = detail_key == "sys_devices"
    show_eff_plots = detail_key == "db_eff"
    show_plot_card = (detail_key not in no_overview_keys) and (detail_key != "db_eff")

    hist_seed_map = {
        "db_power": DASH_HIST["power_kw"],
        "db_h2": DASH_HIST["h2_rate"],
        "db_eff": DASH_HIST["efficiency"],
        "db_health": DASH_HIST["efficiency"],
        "db_tanks": collections.deque([70.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
        "db_tr_power_kw": DASH_HIST["power_kw"],
        "db_tr_h2_rate": DASH_HIST["h2_rate"],
        "db_tr_efficiency": DASH_HIST["efficiency"],
        "net_status": collections.deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
    }
    init_hist = hist_seed_map.get(detail_key, DASH_HIST["power_kw"])
    init_vals = list(init_hist)
    init_last = init_vals[-1] if init_vals else 0.0
    init_min = min(init_vals) if init_vals else 0.0
    init_max = max(init_vals) if init_vals else 0.0
    init_avg = (sum(init_vals) / len(init_vals)) if init_vals else 0.0

    def _sensor_name_link(label: str, sensor_k: str):
        if not on_open_sensor:
            return ft.Text(label, color=C["white"], size=12)

        bg_ref = ft.Ref[ft.Container]()
        txt_ref = ft.Ref[ft.Text]()

        def _hover(e):
            hovered = e.data == "true"
            if bg_ref.current:
                bg_ref.current.bgcolor = C["teal"] + ("24" if hovered else "00")
                bg_ref.current.update()
            if txt_ref.current:
                txt_ref.current.color = C["teal"] if hovered else C["white"]
                txt_ref.current.update()

        return ft.Container(
            ref=bg_ref,
            width=168,
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=6,
            bgcolor=C["teal"] + "00",
            alignment=ft.Alignment(-1, 0),
            ink=True,
            on_hover=_hover,
            on_click=lambda e, k=sensor_k: on_open_sensor(k),
            content=ft.Text(label, ref=txt_ref, color=C["white"], size=12),
        )

    stats_seed_rows = []
    for sensor_key, s in SENSORS.items():
        vals = list(s.history)
        avg = (sum(vals) / len(vals)) if vals else s.value
        name_ctl = _sensor_name_link(s.name, sensor_key)
        stats_seed_rows.append(ft.Row([
            ft.Container(content=name_ctl, width=170),
            ft.Text(s.fmt(), color=s.color, size=12, width=80, weight=ft.FontWeight.BOLD),
            ft.Text(f"{min(vals):.2f}" if vals else "-", color=C["gray"], size=12, width=80),
            ft.Text(f"{max(vals):.2f}" if vals else "-", color=C["gray"], size=12, width=80),
            ft.Text(f"{avg:.2f}", color=C["gray"], size=12, width=80),
            badge(s.status, STATUS_COLOR[s.status]),
        ], spacing=0))

    device_seed = [
        ("PLC Unit 1", "ONLINE", C["green"]),
        ("PLC Unit 2", "ONLINE", C["green"]),
        ("SCADA Server", "ONLINE", C["green"]),
        ("HMI Terminal 1", "ONLINE", C["green"]),
        ("HMI Terminal 2", "STANDBY", C["amber"]),
        ("Sensor Hub A", "ONLINE", C["green"]),
        ("Sensor Hub B", "FAULT", C["red"]),
        ("Data Logger", "ONLINE", C["green"]),
        ("OPC-UA Gateway", "ONLINE", C["green"]),
        ("Historian DB", "STANDBY", C["amber"]),
    ]
    device_seed_rows = []
    for name, status, col in device_seed:
        device_seed_rows.append(ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=col),
            ft.Container(width=8),
            ft.Text(name, color=C["white"], size=12, expand=True),
            badge(status, col),
        ], spacing=0))

    return ft.Column([
        ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=C["gray"], on_click=lambda e: on_back()),
            ft.Icon(ft.Icons.INSIGHTS, color=meta[2], size=18),
            ft.Text(meta[0], ref=title_ref, color=C["white"], size=16, weight=ft.FontWeight.W_700),
            ft.Text(meta[3], ref=subtitle_ref, color=C["gray"], size=11),
        ], spacing=8),
        ft.Container(height=10),
        ft.Container(
            ref=overview_card_ref,
            visible=show_overview,
            content=card(ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Current Value", color=C["gray"], size=11),
                        ft.Row([
                            ft.Text(f"{init_last:.2f}", ref=value_ref, color=meta[2], size=34, weight=ft.FontWeight.BOLD),
                            ft.Text(meta[1], ref=unit_ref, color=C["gray"], size=14),
                        ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=6),
                    ]),
                    ft.Container(expand=True),
                    ft.Column([
                        ft.Row([
                            ft.Container(width=9, height=9, border_radius=5, ref=status_dot_ref, bgcolor=C["green"]),
                            ft.Text("OK", ref=status_txt_ref, color=C["green"], size=12, weight=ft.FontWeight.W_700),
                        ], spacing=6),
                        ft.Container(height=8),
                        ft.Text("Minimum", color=C["gray"], size=10),
                        ft.Text(f"{init_min:.2f}", ref=min_ref, color=C["white"], size=12),
                        ft.Text("Maximum", color=C["gray"], size=10),
                        ft.Text(f"{init_max:.2f}", ref=max_ref, color=C["white"], size=12),
                        ft.Text("Average", color=C["gray"], size=10),
                        ft.Text(f"{init_avg:.2f}", ref=avg_ref, color=C["white"], size=12),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                ]),
            ]), expand=True),
        ),
        ft.Container(height=12),
        ft.Container(
            ref=range_bar_ref,
            visible=show_plot_card or show_eff_plots,
            content=card(ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE, color=C["teal"], size=14),
                    ft.Text("Plot Time Range", color=C["gray"], size=11),
                ], spacing=6),
                ft.Dropdown(
                    ref=range_sel_ref,
                    value="Last Minute",
                    width=190,
                    dense=True,
                    options=[
                        ft.dropdown.Option("From Start"),
                        ft.dropdown.Option("Last Year"),
                        ft.dropdown.Option("Last Month"),
                        ft.dropdown.Option("Last Week"),
                        ft.dropdown.Option("Last Day"),
                        ft.dropdown.Option("Last Hour"),
                        ft.dropdown.Option("Last Minute"),
                    ],
                    border_color=C["border"],
                    bgcolor=C["card2"],
                    color=C["white"],
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), expand=True),
        ),
        ft.Container(height=12),
        ft.Row([
            card(ft.Column([
                hdr("SETTINGS", "Diagnostics / Breakdown"),
                ft.Container(height=8),
                ft.Column([ft.Text("No diagnostics yet.", color=C["gray"], size=11)], ref=diag_ref, spacing=6),
            ]), expand=True),
            card(ft.Column([
                hdr("EVENT", "Related Events"),
                ft.Container(height=8),
                ft.Column([ft.Text("No related events.", color=C["gray"], size=11)], ref=events_ref, spacing=6),
            ]), expand=True),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Container(
            ref=stats_card_ref,
            visible=show_stats_card,
            content=card(ft.Column([
                hdr("TABLE_CHART", "Sensor Statistics (Expanded)"),
                ft.Container(height=8),
                ft.Row([
                    ft.Text("Sensor",  color=C["gray"], size=11, width=170),
                    ft.Text("Current", color=C["gray"], size=11, width=80),
                    ft.Text("Min",     color=C["gray"], size=11, width=80),
                    ft.Text("Max",     color=C["gray"], size=11, width=80),
                    ft.Text("Avg",     color=C["gray"], size=11, width=80),
                    ft.Text("Status",  color=C["gray"], size=11),
                ]),
                divider(),
                ft.Column(stats_seed_rows or [ft.Text("No statistics available.", color=C["gray"], size=11)],
                          ref=stats_rows_ref, spacing=6),
            ]), expand=True),
        ),
        ft.Container(height=12),
        ft.Container(
            ref=devices_card_ref,
            visible=show_devices_card,
            content=card(ft.Column([
                hdr("DEVELOPER_BOARD", "Device Status (Expanded)"),
                ft.Container(height=8),
                ft.Column(device_seed_rows or [ft.Text("No device data available.", color=C["gray"], size=11)],
                          ref=devices_rows_ref, spacing=8),
            ]), expand=True),
        ),
        ft.Container(height=12),
        ft.Container(
            ref=eff_plots_card_ref,
            visible=show_eff_plots,
            content=card(ft.Column([
                hdr("AUTO_GRAPH", "Efficiency Metrics Trends"),
                ft.Container(height=8),
                ft.Text("Electrical Efficiency", color=C["gray"], size=11),
                ft.Row([draw_line_chart([(DASH_HIST["efficiency"], C["green"])], w=940, h=110)],
                       ref=eff_ele_row_ref, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Text("Conversion Efficiency", color=C["gray"], size=11),
                ft.Row([draw_line_chart([(DASH_HIST["conv_eff"], C["teal"])], w=940, h=110)],
                       ref=eff_conv_row_ref, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=8),
                ft.Text("Performance Ratio", color=C["gray"], size=11),
                ft.Row([draw_line_chart([(DASH_HIST["perf_ratio"], C["blue"])], w=940, h=110)],
                       ref=eff_pr_row_ref, alignment=ft.MainAxisAlignment.CENTER),
            ]), expand=True),
        ),
        ft.Container(height=12),
        ft.Container(
            ref=plot_card_ref,
            content=card(ft.Column([
                hdr("SHOW_CHART", "Historical Trend"),
                ft.Container(height=8),
                ft.Row([draw_line_chart([(init_hist, meta[2])], w=940, h=280)],
                       ref=plot_ref, alignment=ft.MainAxisAlignment.CENTER),
            ]), expand=True),
            visible=show_plot_card,
        ),
        ft.Container(height=12),
        card(ft.Column([
            hdr("INFO", "Context"),
            ft.Container(height=8),
            ft.Text("This view is card-specific and updates live with system state.", color=C["gray"], size=11),
        ]), expand=True),
    ], spacing=0, expand=True)


def build_network_settings(refs: dict, actions: dict, on_open_detail=None):
    media_ref = ft.Ref[ft.Dropdown]()
    ssid_ref = ft.Ref[ft.TextField]()
    pass_ref = ft.Ref[ft.TextField]()
    dhcp_ref = ft.Ref[ft.Switch]()
    ip_ref = ft.Ref[ft.TextField]()
    subnet_ref = ft.Ref[ft.TextField]()
    gateway_ref = ft.Ref[ft.TextField]()
    dns_ref = ft.Ref[ft.TextField]()
    status_dot_ref = ft.Ref[ft.Container]()
    status_txt_ref = ft.Ref[ft.Text]()
    ip_txt_ref = ft.Ref[ft.Text]()
    sig_bar_ref = ft.Ref[ft.ProgressBar]()
    sig_txt_ref = ft.Ref[ft.Text]()

    mqtt_host_ref = ft.Ref[ft.TextField]()
    mqtt_port_ref = ft.Ref[ft.TextField]()
    mqtt_user_ref = ft.Ref[ft.TextField]()
    mqtt_pass_ref = ft.Ref[ft.TextField]()
    mqtt_topic_ref = ft.Ref[ft.TextField]()
    mqtt_dot_ref = ft.Ref[ft.Container]()
    mqtt_txt_ref = ft.Ref[ft.Text]()
    http_ep_ref = ft.Ref[ft.TextField]()
    ws_ref = ft.Ref[ft.TextField]()

    plc_proto_ref = ft.Ref[ft.Dropdown]()
    plc_ip_ref = ft.Ref[ft.TextField]()
    plc_port_ref = ft.Ref[ft.TextField]()
    plc_dot_ref = ft.Ref[ft.Container]()
    plc_txt_ref = ft.Ref[ft.Text]()

    data_freq_ref = ft.Ref[ft.Dropdown]()
    telem_ref = ft.Ref[ft.Dropdown]()
    log_ref = ft.Ref[ft.Dropdown]()
    remote_mon_ref = ft.Ref[ft.Switch]()

    tls_ref = ft.Ref[ft.Switch]()
    auth_ref = ft.Ref[ft.Switch]()
    api_key_ref = ft.Ref[ft.TextField]()
    access_ref = ft.Ref[ft.Dropdown]()
    sec_msg_ref = ft.Ref[ft.Text]()

    lat_ref = ft.Ref[ft.Text]()
    loss_ref = ft.Ref[ft.Text]()
    last_ref = ft.Ref[ft.Text]()
    ping_ref = ft.Ref[ft.Text]()
    conn_ref = ft.Ref[ft.Text]()

    apply_msg_ref = ft.Ref[ft.Text]()

    refs["net_media"] = media_ref
    refs["net_ssid"] = ssid_ref
    refs["net_pass"] = pass_ref
    refs["net_dhcp"] = dhcp_ref
    refs["net_static_ip"] = ip_ref
    refs["net_subnet"] = subnet_ref
    refs["net_gateway"] = gateway_ref
    refs["net_dns"] = dns_ref
    refs["net_status_dot"] = status_dot_ref
    refs["net_status_txt"] = status_txt_ref
    refs["net_ip_txt"] = ip_txt_ref
    refs["net_sig_bar"] = sig_bar_ref
    refs["net_sig_txt"] = sig_txt_ref
    refs["net_mqtt_host"] = mqtt_host_ref
    refs["net_mqtt_port"] = mqtt_port_ref
    refs["net_mqtt_user"] = mqtt_user_ref
    refs["net_mqtt_pass"] = mqtt_pass_ref
    refs["net_mqtt_topic"] = mqtt_topic_ref
    refs["net_mqtt_dot"] = mqtt_dot_ref
    refs["net_mqtt_txt"] = mqtt_txt_ref
    refs["net_http_ep"] = http_ep_ref
    refs["net_ws"] = ws_ref
    refs["net_plc_proto"] = plc_proto_ref
    refs["net_plc_ip"] = plc_ip_ref
    refs["net_plc_port"] = plc_port_ref
    refs["net_plc_dot"] = plc_dot_ref
    refs["net_plc_txt"] = plc_txt_ref
    refs["net_data_freq"] = data_freq_ref
    refs["net_telem"] = telem_ref
    refs["net_log_freq"] = log_ref
    refs["net_remote_mon"] = remote_mon_ref
    refs["net_tls"] = tls_ref
    refs["net_auth"] = auth_ref
    refs["net_api_key"] = api_key_ref
    refs["net_access_role"] = access_ref
    refs["net_sec_msg"] = sec_msg_ref
    refs["net_latency"] = lat_ref
    refs["net_packet_loss"] = loss_ref
    refs["net_last_attempt"] = last_ref
    refs["net_ping_result"] = ping_ref
    refs["net_conn_result"] = conn_ref
    refs["net_apply_msg"] = apply_msg_ref

    def on_dhcp_change(_):
        enabled = not bool(dhcp_ref.current.value) if dhcp_ref.current else False
        for rf in [ip_ref, subnet_ref, gateway_ref, dns_ref]:
            if rf.current:
                rf.current.disabled = not enabled
                rf.current.opacity = 1.0 if enabled else 0.55
                rf.current.update()

    interface_card = card(ft.Column([
        hdr("ROUTER", "1) Network Interface Configuration"),
        ft.Container(height=8),
        ft.Text("Interface", color=C["gray"], size=11),
        ft.Dropdown(
            ref=media_ref, value="Wi-Fi",
            options=[ft.dropdown.Option("Wi-Fi"), ft.dropdown.Option("Ethernet")],
            dense=True, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
        ),
        ft.Container(height=8),
        ft.TextField(
            ref=ssid_ref, label="SSID / Network Name", value="FuelCell-IoT",
            border_color=C["border"], bgcolor=C["card2"], color=C["white"],
            label_style=ft.TextStyle(color=C["gray"]),
        ),
        ft.Container(height=8),
        ft.TextField(
            ref=pass_ref, label="Password", password=True, can_reveal_password=True,
            border_color=C["border"], bgcolor=C["card2"], color=C["white"],
            label_style=ft.TextStyle(color=C["gray"]),
        ),
        ft.Container(height=8),
        ft.Row([
            ft.Container(width=10, height=10, border_radius=5, ref=status_dot_ref, bgcolor=C["gray"]),
            ft.Text("Disconnected", ref=status_txt_ref, color=C["gray"], size=13, weight=ft.FontWeight.W_700),
            ft.Container(expand=True),
            ft.Text("-", ref=ip_txt_ref, color=C["white"], size=12),
        ], spacing=8),
        ft.Container(height=6),
        ft.Row([
            ft.Text("Signal Strength", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Text("0%", ref=sig_txt_ref, color=C["gray"], size=11),
        ]),
        ft.ProgressBar(value=0.0, ref=sig_bar_ref, color=C["teal"], bgcolor=C["gray2"], height=7),
        ft.Container(height=8),
        ft.Row([
            ft.OutlinedButton("Reconnect", icon=ft.Icons.REFRESH, on_click=actions.get("reconnect")),
            ft.OutlinedButton("Disconnect", icon=ft.Icons.LINK_OFF, on_click=actions.get("disconnect")),
        ], spacing=8),
    ]), expand=True)

    ip_card = card(ft.Column([
        hdr("LAN", "2) IP Configuration"),
        ft.Container(height=8),
        ft.Row([
            ft.Text("DHCP (Dynamic IP)", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Switch(ref=dhcp_ref, value=True, active_color=C["teal"], on_change=on_dhcp_change),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.TextField(ref=ip_ref, label="Static IP Address", value="192.168.10.120",
                     disabled=True, opacity=0.55, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.TextField(ref=subnet_ref, label="Subnet Mask", value="255.255.255.0",
                     disabled=True, opacity=0.55, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.TextField(ref=gateway_ref, label="Gateway", value="192.168.10.1",
                     disabled=True, opacity=0.55, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.TextField(ref=dns_ref, label="DNS Server", value="8.8.8.8",
                     disabled=True, opacity=0.55, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
    ]), expand=True)

    iot_card = card(ft.Column([
        hdr("CLOUD", "3) IoT Communication Settings"),
        ft.Container(height=8),
        ft.Row([
            ft.Container(width=10, height=10, border_radius=5, ref=mqtt_dot_ref, bgcolor=C["gray"]),
            ft.Text("MQTT: Disconnected", ref=mqtt_txt_ref, color=C["gray"], size=11),
        ], spacing=8),
        ft.Container(height=6),
        ft.TextField(ref=mqtt_host_ref, label="MQTT Broker Address", value="broker.hmi.local",
                     border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.Row([
            ft.TextField(ref=mqtt_port_ref, label="Port", value="1883", width=130,
                         border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
            ft.Container(width=8),
            ft.TextField(ref=mqtt_topic_ref, label="Topic", value="fuelcell/telemetry", expand=True,
                         border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
        ]),
        ft.Container(height=6),
        ft.Row([
            ft.TextField(ref=mqtt_user_ref, label="Username", value="operator", expand=True,
                         border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
            ft.Container(width=8),
            ft.TextField(ref=mqtt_pass_ref, label="Password", password=True, can_reveal_password=True, value="",
                         expand=True, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
        ]),
        ft.Container(height=6),
        ft.TextField(ref=http_ep_ref, label="HTTP / REST API Endpoint", value="https://api.hmi.local/v1/data",
                     border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.TextField(ref=ws_ref, label="WebSocket URL (optional)", value="wss://api.hmi.local/ws",
                     border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
    ]), expand=True)

    plc_card = make_clickable_card(card(ft.Column([
        hdr("SETTINGS_INPUT_COMPONENT", "4) PLC / Field Communication"),
        ft.Container(height=8),
        ft.Row([
            ft.Container(width=10, height=10, border_radius=5, ref=plc_dot_ref, bgcolor=C["gray"]),
            ft.Text("PLC: Disconnected", ref=plc_txt_ref, color=C["gray"], size=11),
        ], spacing=8),
        ft.Container(height=6),
        ft.Dropdown(
            ref=plc_proto_ref, value="Modbus TCP",
            options=[ft.dropdown.Option("Modbus TCP"), ft.dropdown.Option("OPC UA"), ft.dropdown.Option("EtherNet/IP")],
            dense=True, border_color=C["border"], bgcolor=C["card2"], color=C["white"],
        ),
        ft.Container(height=6),
        ft.Row([
            ft.TextField(ref=plc_ip_ref, label="Device IP", value="192.168.10.20", expand=True,
                         border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
            ft.Container(width=8),
            ft.TextField(ref=plc_port_ref, label="Port", value="502", width=120,
                         border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                         label_style=ft.TextStyle(color=C["gray"])),
        ]),
    ]), expand=True), on_open_detail, "net_plc")

    tx_card = card(ft.Column([
        hdr("SYNC", "5) Data Transmission Settings"),
        ft.Container(height=8),
        ft.Dropdown(ref=data_freq_ref, label="Data Update Frequency",
                    value="1 s",
                    options=[ft.dropdown.Option("0.5 s"), ft.dropdown.Option("1 s"), ft.dropdown.Option("2 s"), ft.dropdown.Option("5 s")],
                    border_color=C["border"], bgcolor=C["card2"], color=C["white"]),
        ft.Container(height=6),
        ft.Dropdown(ref=telem_ref, label="Telemetry Transmission Interval",
                    value="5 s",
                    options=[ft.dropdown.Option("1 s"), ft.dropdown.Option("5 s"), ft.dropdown.Option("10 s"), ft.dropdown.Option("30 s")],
                    border_color=C["border"], bgcolor=C["card2"], color=C["white"]),
        ft.Container(height=6),
        ft.Dropdown(ref=log_ref, label="Logging Frequency",
                    value="1 s",
                    options=[ft.dropdown.Option("1 s"), ft.dropdown.Option("5 s"), ft.dropdown.Option("10 s"), ft.dropdown.Option("60 s")],
                    border_color=C["border"], bgcolor=C["card2"], color=C["white"]),
        ft.Container(height=6),
        ft.Row([
            ft.Text("Enable Remote Monitoring", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Switch(ref=remote_mon_ref, value=True, active_color=C["teal"]),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    ]), expand=True)

    sec_card = card(ft.Column([
        hdr("SECURITY", "6) Security Settings"),
        ft.Container(height=8),
        ft.Row([
            ft.Text("Enable TLS/SSL", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Switch(ref=tls_ref, value=True, active_color=C["teal"]),
        ]),
        ft.Container(height=6),
        ft.Row([
            ft.Text("Require Authentication", color=C["gray"], size=11),
            ft.Container(expand=True),
            ft.Switch(ref=auth_ref, value=True, active_color=C["teal"]),
        ]),
        ft.Container(height=6),
        ft.TextField(ref=api_key_ref, label="API Key", password=True, can_reveal_password=True, value="",
                     border_color=C["border"], bgcolor=C["card2"], color=C["white"],
                     label_style=ft.TextStyle(color=C["gray"])),
        ft.Container(height=6),
        ft.Dropdown(ref=access_ref, label="Remote Access Role", value="Operator",
                    options=[ft.dropdown.Option("Viewer"), ft.dropdown.Option("Operator"), ft.dropdown.Option("Admin")],
                    border_color=C["border"], bgcolor=C["card2"], color=C["white"]),
        ft.Container(height=6),
        ft.Text("", ref=sec_msg_ref, color=C["gray"], size=11),
    ]), expand=True)

    diag_card = card(ft.Column([
        hdr("NETWORK_CHECK", "7) System Connectivity Diagnostics"),
        ft.Container(height=8),
        ft.Row([
            ft.OutlinedButton("Ping Test", icon=ft.Icons.SPEED, on_click=actions.get("ping")),
            ft.OutlinedButton("Connection Test", icon=ft.Icons.PLAY_CIRCLE, on_click=actions.get("test")),
        ], spacing=8),
        ft.Container(height=8),
        ft.Row([ft.Text("Latency", color=C["gray"], width=170), ft.Text("-", ref=lat_ref, color=C["white"], size=12)], spacing=8),
        ft.Row([ft.Text("Packet Loss", color=C["gray"], width=170), ft.Text("-", ref=loss_ref, color=C["white"], size=12)], spacing=8),
        ft.Row([ft.Text("Last Connection Attempt", color=C["gray"], width=170), ft.Text("-", ref=last_ref, color=C["white"], size=12)], spacing=8),
        ft.Row([ft.Text("Ping Result", color=C["gray"], width=170), ft.Text("-", ref=ping_ref, color=C["white"], size=12)], spacing=8),
        ft.Row([ft.Text("Connection Test", color=C["gray"], width=170), ft.Text("-", ref=conn_ref, color=C["white"], size=12)], spacing=8),
    ]), expand=True)

    action_card = card(ft.Column([
        hdr("SAVE", "8) Save / Apply Configuration"),
        ft.Container(height=8),
        ft.Row([
            ft.ElevatedButton("Save Settings", icon=ft.Icons.SAVE, on_click=actions.get("save"),
                              style=ft.ButtonStyle(bgcolor=C["blue"], color=C["white"])),
            ft.ElevatedButton("Apply Changes", icon=ft.Icons.DONE_ALL, on_click=actions.get("apply"),
                              style=ft.ButtonStyle(bgcolor=C["teal"], color=C["bg"])),
            ft.OutlinedButton("Reset Network", icon=ft.Icons.RESTART_ALT, on_click=actions.get("reset")),
            ft.OutlinedButton("Restore Defaults", icon=ft.Icons.RESTORE, on_click=actions.get("defaults")),
        ], wrap=True, spacing=8),
        ft.Container(height=8),
        ft.Text("", ref=apply_msg_ref, color=C["gray"], size=11),
    ]), expand=True)

    return ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.SETTINGS_ETHERNET, color=C["teal"], size=18),
            ft.Text("Network Settings", color=C["white"], size=15, weight=ft.FontWeight.W_700),
            ft.Text("Industrial IoT Connectivity Management", color=C["gray"], size=11),
        ], spacing=8),
        ft.Container(height=10),
        ft.Row([interface_card, ip_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([iot_card, plc_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([tx_card, sec_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([diag_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([action_card], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  MAIN APPLICATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

