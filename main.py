"""Application entry point, navigation, and live simulation loop."""

import asyncio, random, collections
from datetime import datetime
import flet as ft

from models import (
    C, SENSORS, _activate_system_alarm, _resolve_system_alarm,
)
from ui_components import nav_btn
from ui_pages import (
    build_dashboard, build_sensor_panel, build_sensor_detail,
    build_analytics, build_system, build_alarm_history, build_network_settings, build_card_detail,
)
from simulation_engine import start_simulation

def main(page: ft.Page):
    page.title         = "Industrial HMI Dashboard"
    page.bgcolor       = C["bg"]
    page.window.width  = 1200
    page.window.height = 780
    page.padding       = 0

    refs: dict = {}          # live-update reference store
    current_page = {"idx": 0}
    selected_sensor = {"key": None}
    selected_card = {"key": None, "from_idx": 0}
    emergency_state = {"active": False}
    network_defaults = {
        "media": "Wi-Fi",
        "ssid": "FuelCell-IoT",
        "password": "",
        "dhcp": True,
        "static_ip": "192.168.10.120",
        "subnet": "255.255.255.0",
        "gateway": "192.168.10.1",
        "dns": "8.8.8.8",
        "ip": "-",
        "status": "Disconnected",
        "signal": 0.0,
        "connect_ticks": 0,
        "mqtt_host": "broker.hmi.local",
        "mqtt_port": "1883",
        "mqtt_user": "operator",
        "mqtt_pass": "",
        "mqtt_topic": "fuelcell/telemetry",
        "mqtt_status": "Disconnected",
        "http_ep": "https://api.hmi.local/v1/data",
        "ws": "wss://api.hmi.local/ws",
        "plc_proto": "Modbus TCP",
        "plc_ip": "192.168.10.20",
        "plc_port": "502",
        "plc_status": "Disconnected",
        "data_freq": "1 s",
        "telem_interval": "5 s",
        "log_freq": "1 s",
        "remote_mon": True,
        "tls": True,
        "auth": True,
        "api_key": "",
        "access_role": "Operator",
        "latency_ms": "-",
        "packet_loss": "-",
        "last_attempt": "-",
        "ping_result": "-",
        "conn_result": "-",
        "apply_msg": "",
    }
    network_state = dict(network_defaults)

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

    def open_card_detail(detail_key: str):
        selected_card["key"] = detail_key
        selected_card["from_idx"] = current_page["idx"]
        current_page["idx"] = 6
        pages_cache.clear()
        refs.clear()
        nav_col_ref.current.controls = make_nav(selected_card["from_idx"])
        content_ref.current.controls = [get_page(6)]
        page.update()

    def close_card_detail():
        back_idx = selected_card["from_idx"]
        selected_card["key"] = None
        current_page["idx"] = back_idx
        pages_cache.clear()
        refs.clear()
        nav_col_ref.current.controls = make_nav(back_idx)
        content_ref.current.controls = [get_page(back_idx)]
        page.update()

    def _ref_text(key: str, fallback: str = ""):
        r = refs.get(key)
        if r and r.current and hasattr(r.current, "value"):
            v = r.current.value
            return (v.strip() if isinstance(v, str) else v) if v is not None else fallback
        return fallback

    def _pull_network_form():
        network_state["media"] = _ref_text("net_media", network_state["media"])
        network_state["ssid"] = _ref_text("net_ssid", network_state["ssid"])
        network_state["password"] = _ref_text("net_pass", network_state["password"])
        dhcp_ref = refs.get("net_dhcp")
        network_state["dhcp"] = bool(dhcp_ref.current.value) if dhcp_ref and dhcp_ref.current else network_state["dhcp"]
        network_state["static_ip"] = _ref_text("net_static_ip", network_state["static_ip"])
        network_state["subnet"] = _ref_text("net_subnet", network_state["subnet"])
        network_state["gateway"] = _ref_text("net_gateway", network_state["gateway"])
        network_state["dns"] = _ref_text("net_dns", network_state["dns"])
        network_state["mqtt_host"] = _ref_text("net_mqtt_host", network_state["mqtt_host"])
        network_state["mqtt_port"] = _ref_text("net_mqtt_port", network_state["mqtt_port"])
        network_state["mqtt_user"] = _ref_text("net_mqtt_user", network_state["mqtt_user"])
        network_state["mqtt_pass"] = _ref_text("net_mqtt_pass", network_state["mqtt_pass"])
        network_state["mqtt_topic"] = _ref_text("net_mqtt_topic", network_state["mqtt_topic"])
        network_state["http_ep"] = _ref_text("net_http_ep", network_state["http_ep"])
        network_state["ws"] = _ref_text("net_ws", network_state["ws"])
        network_state["plc_proto"] = _ref_text("net_plc_proto", network_state["plc_proto"])
        network_state["plc_ip"] = _ref_text("net_plc_ip", network_state["plc_ip"])
        network_state["plc_port"] = _ref_text("net_plc_port", network_state["plc_port"])
        network_state["data_freq"] = _ref_text("net_data_freq", network_state["data_freq"])
        network_state["telem_interval"] = _ref_text("net_telem", network_state["telem_interval"])
        network_state["log_freq"] = _ref_text("net_log_freq", network_state["log_freq"])
        remote_ref = refs.get("net_remote_mon")
        tls_ref = refs.get("net_tls")
        auth_ref = refs.get("net_auth")
        network_state["remote_mon"] = bool(remote_ref.current.value) if remote_ref and remote_ref.current else network_state["remote_mon"]
        network_state["tls"] = bool(tls_ref.current.value) if tls_ref and tls_ref.current else network_state["tls"]
        network_state["auth"] = bool(auth_ref.current.value) if auth_ref and auth_ref.current else network_state["auth"]
        network_state["api_key"] = _ref_text("net_api_key", network_state["api_key"])
        network_state["access_role"] = _ref_text("net_access_role", network_state["access_role"])

    def _apply_network_to_controls():
        mapping = {
            "net_media": "media",
            "net_ssid": "ssid",
            "net_pass": "password",
            "net_static_ip": "static_ip",
            "net_subnet": "subnet",
            "net_gateway": "gateway",
            "net_dns": "dns",
            "net_mqtt_host": "mqtt_host",
            "net_mqtt_port": "mqtt_port",
            "net_mqtt_user": "mqtt_user",
            "net_mqtt_pass": "mqtt_pass",
            "net_mqtt_topic": "mqtt_topic",
            "net_http_ep": "http_ep",
            "net_ws": "ws",
            "net_plc_proto": "plc_proto",
            "net_plc_ip": "plc_ip",
            "net_plc_port": "plc_port",
            "net_data_freq": "data_freq",
            "net_telem": "telem_interval",
            "net_log_freq": "log_freq",
            "net_api_key": "api_key",
            "net_access_role": "access_role",
        }
        for ref_key, state_key in mapping.items():
            r = refs.get(ref_key)
            if r and r.current and hasattr(r.current, "value"):
                r.current.value = network_state[state_key]
        for sw_key, st_key in [("net_dhcp", "dhcp"), ("net_remote_mon", "remote_mon"), ("net_tls", "tls"), ("net_auth", "auth")]:
            r = refs.get(sw_key)
            if r and r.current:
                r.current.value = bool(network_state[st_key])

        dhcp_ref = refs.get("net_dhcp")
        enabled = not bool(dhcp_ref.current.value) if dhcp_ref and dhcp_ref.current else False
        for rfk in ["net_static_ip", "net_subnet", "net_gateway", "net_dns"]:
            rf = refs.get(rfk)
            if rf and rf.current:
                rf.current.disabled = not enabled
                rf.current.opacity = 1.0 if enabled else 0.55
        page.update()

    def _set_msg(msg: str):
        network_state["apply_msg"] = msg
        apply_msg_ref = refs.get("net_apply_msg")
        if apply_msg_ref and apply_msg_ref.current:
            apply_msg_ref.current.value = msg
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True, bgcolor=C["card2"])

    def apply_network_settings(mode: str = "apply"):
        _pull_network_form()
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        network_state["last_attempt"] = now_s

        if mode == "save":
            _set_msg("Network settings saved (mock).")
            page.update()
            return

        if mode == "disconnect":
            network_state["status"] = "Disconnected"
            network_state["connect_ticks"] = 0
            network_state["signal"] = 0.0
            network_state["ip"] = "-"
            network_state["mqtt_status"] = "Disconnected"
            network_state["plc_status"] = "Disconnected"
            _set_msg("Disconnected from network.")
            page.update()
            return

        if network_state["media"] == "Wi-Fi" and not network_state["ssid"]:
            network_state["status"] = "Disconnected"
            network_state["connect_ticks"] = 0
            network_state["signal"] = 0.0
            network_state["ip"] = "-"
            _set_msg("SSID required for Wi-Fi.")
            page.update()
            return

        network_state["status"] = "Connecting"
        network_state["connect_ticks"] = random.randint(2, 4)
        network_state["signal"] = random.uniform(0.2, 0.45)
        network_state["ip"] = "-"
        network_state["mqtt_status"] = "Connecting"
        network_state["plc_status"] = "Connecting"
        network_state["conn_result"] = "Running..."
        _set_msg(f"Applying {network_state['media']} settings...")
        page.update()

    def on_save(_):
        apply_network_settings("save")

    def on_apply(_):
        apply_network_settings("apply")

    def on_reconnect(_):
        apply_network_settings("reconnect")

    def on_disconnect(_):
        apply_network_settings("disconnect")

    def on_reset(_):
        network_state["status"] = "Disconnected"
        network_state["connect_ticks"] = 0
        network_state["signal"] = 0.0
        network_state["ip"] = "-"
        network_state["mqtt_status"] = "Disconnected"
        network_state["plc_status"] = "Disconnected"
        network_state["latency_ms"] = "-"
        network_state["packet_loss"] = "-"
        network_state["ping_result"] = "-"
        network_state["conn_result"] = "-"
        network_state["last_attempt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _set_msg("Network runtime state reset.")
        page.update()

    def on_defaults(_):
        network_state.clear()
        network_state.update(network_defaults)
        _apply_network_to_controls()
        _set_msg("Defaults restored.")
        page.update()

    def on_ping(_):
        network_state["latency_ms"] = f"{random.randint(18, 140)} ms"
        network_state["packet_loss"] = f"{random.uniform(0.0, 3.5):.1f}%"
        network_state["ping_result"] = "Success" if random.random() < 0.9 else "Timeout"
        network_state["last_attempt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _set_msg(f"Ping test: {network_state['ping_result']}")
        page.update()

    def on_conn_test(_):
        apply_network_settings("test")

    def build_network_page(local_refs: dict):
        actions = {
            "save": on_save,
            "apply": on_apply,
            "reset": on_reset,
            "defaults": on_defaults,
            "reconnect": on_reconnect,
            "disconnect": on_disconnect,
            "ping": on_ping,
            "test": on_conn_test,
        }
        return build_network_settings(local_refs, actions, on_open_detail=open_card_detail)

    def build_card_detail_page(local_refs: dict):
        return build_card_detail(local_refs, selected_card["key"] or "db_power", close_card_detail)

    def get_page(idx):
        if idx not in pages_cache:
            builders = [build_dashboard, build_sensors_page,
                        build_analytics, build_system, build_alarm_history, build_network_page, build_card_detail_page]
            if idx == 0:
                pages_cache[idx] = builders[idx](refs, on_open_detail=open_card_detail)
            elif idx == 2:
                pages_cache[idx] = builders[idx](refs, on_open_detail=open_card_detail)
            elif idx == 3:
                pages_cache[idx] = builders[idx](
                    refs,
                    on_open_detail=open_card_detail,
                    on_open_network=lambda: switch_page(5),
                    on_open_alarms=lambda: switch_page(4),
                )
            else:
                pages_cache[idx] = builders[idx](refs)
        return pages_cache[idx]

    # â”€â”€ Top bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    clock_ref   = ft.Ref[ft.Text]()
    alarm_badge = ft.Ref[ft.Text]()
    live_dot_ref = ft.Ref[ft.Icon]()
    live_txt_ref = ft.Ref[ft.Text]()
    estop_txt_ref = ft.Ref[ft.Text]()
    status_dot_ref = ft.Ref[ft.Icon]()
    status_msg_ref = ft.Ref[ft.Text]()
    mode_msg_ref = ft.Ref[ft.Text]()

    def refresh_operation_ui():
        estop = emergency_state["active"]
        if live_dot_ref.current:
            live_dot_ref.current.color = C["red"] if estop else C["green"]
        if status_dot_ref.current:
            status_dot_ref.current.color = C["red"] if estop else C["green"]
        if live_txt_ref.current:
            live_txt_ref.current.value = "STOPPED" if estop else "LIVE"
            live_txt_ref.current.color = C["red"] if estop else C["green"]
        if estop_txt_ref.current:
            estop_txt_ref.current.value = "RESET" if estop else "E-STOP"
        if status_msg_ref.current:
            status_msg_ref.current.value = (
                "Emergency stop active - operations halted"
                if estop else "All systems nominal"
            )
            status_msg_ref.current.color = C["red"] if estop else C["gray"]
        if mode_msg_ref.current:
            mode_msg_ref.current.value = (
                "Simulation paused  •  Emergency stop engaged"
                if estop else "Simulation mode  •  Mock data only"
            )

    def set_emergency_stop(active: bool):
        now = datetime.now()
        if active and not emergency_state["active"]:
            emergency_state["active"] = True
            _activate_system_alarm(
                "system_estop",
                "Emergency Stop Activated",
                "CRITICAL",
                "Emergency stop pressed - all operations halted",
                now,
            )
        elif (not active) and emergency_state["active"]:
            emergency_state["active"] = False
            _resolve_system_alarm(
                "system_estop",
                "Emergency stop cleared - operations resumed",
                now,
            )
        refresh_operation_ui()
        page.update()

    def on_estop_click(_):
        set_emergency_stop(not emergency_state["active"])

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
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER, color=C["white"], size=14),
                        ft.Text("E-STOP", ref=estop_txt_ref, color=C["white"], size=10,
                                weight=ft.FontWeight.W_700),
                    ], spacing=4),
                    bgcolor=C["red"],
                    border_radius=6,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    ink=True,
                    on_click=on_estop_click,
                ),
                ft.Container(width=12),
                ft.Icon(ft.Icons.CIRCLE, ref=live_dot_ref, color=C["green"], size=8),
                ft.Text("LIVE", ref=live_txt_ref, color=C["green"], size=11,
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
        ("Network",   "SETTINGS_ETHERNET", 5),
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
        selected_card["key"] = None
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
            ft.Icon(ft.Icons.CIRCLE, ref=status_dot_ref, color=C["green"], size=7),
            ft.Text("All systems nominal", ref=status_msg_ref, color=C["gray"], size=10),
            ft.Container(expand=True),
            ft.Text("Simulation mode  â€¢  Mock data only", ref=mode_msg_ref,
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
    refresh_operation_ui()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  SIMULATION + LIVE-UPDATE THREAD
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    uptime_start = datetime.now()
    dash_state = {
        "energy_kwh": 0.0,
        "h2_capacity_kg": 120.0,
        "h2_remaining_kg": 84.0,
        "h2_t1_capacity_kg": 70.0,
        "h2_t1_remaining_kg": 42.0,
        "h2_t2_capacity_kg": 50.0,
        "h2_t2_remaining_kg": 42.0,
        "h2_consumed_kg": 0.0,
        "elec_eff_target": 52.0,
        "elec_eff": 52.0,
        "conv_eff": 57.0,
        "perf_ratio": 88.0,
    }

    start_simulation(page, refs, current_page, emergency_state, network_state, dash_state,
                    clock_ref, alarm_badge, uptime_start, selected_card)



if __name__ == "__main__":
    ft.run(main)



