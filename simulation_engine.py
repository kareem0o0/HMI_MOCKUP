"""Live simulation/data-update engine."""

import asyncio, random, math, collections
from datetime import datetime
import flet as ft

from models import (
    C, STATUS_COLOR, SENSORS, ALARMS, ALARM_HISTORY, ACTIVE_ALARMS, DASH_HIST,
    HISTORY_LEN, dashboard_metrics, _raise_or_update_alarm, _resolve_alarm, alarm_history_row,
)
from ui_components import draw_spark, draw_line_chart, draw_arc, badge, draw_ring_meter

def start_simulation(page, refs, current_page, emergency_state, network_state, dash_state, clock_ref, alarm_badge, uptime_start, selected_card):
    detail_hist = {
        "h2_remaining_pct": collections.deque([70.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
        "sys_alarm_events": collections.deque([len(ALARMS)] * HISTORY_LEN, maxlen=HISTORY_LEN),
        "net_signal": collections.deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
        "device_online": collections.deque([8.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
        "stats_reliability": collections.deque([100.0] * HISTORY_LEN, maxlen=HISTORY_LEN),
    }

    def _stats(vals):
        arr = list(vals)
        if not arr:
            return 0.0, 0.0, 0.0
        return min(arr), max(arr), (sum(arr) / len(arr))

    def _status_from_value(key: str, v: float):
        if key in {"db_power", "db_tr_power_kw"}:
            return ("FAULT", C["red"]) if v < 8 else ("WARN", C["amber"]) if v < 20 else ("OK", C["green"])
        if key in {"db_eff", "db_tr_efficiency"}:
            return ("FAULT", C["red"]) if v < 40 else ("WARN", C["amber"]) if v < 48 else ("OK", C["green"])
        if key in {"db_h2", "db_tanks", "db_tr_h2_rate"}:
            return ("FAULT", C["red"]) if v < 15 else ("WARN", C["amber"]) if v < 30 else ("OK", C["green"])
        if key == "net_plc":
            return ("OK", C["green"]) if network_state.get("plc_status") == "Online" else ("WARN", C["amber"]) if network_state.get("plc_status") == "Connecting" else ("FAULT", C["red"])
        if key in {"ana_stats", "sys_devices", "net_config"}:
            return ("INFO", C["blue"])
        if key.startswith("net_"):
            return ("OK", C["green"]) if network_state["status"] == "Connected" else ("WARN", C["amber"]) if network_state["status"] == "Connecting" else ("FAULT", C["red"])
        return ("OK", C["green"]) if emergency_state["active"] is False else ("WARN", C["amber"])

    def _detail_payload(detail_key: str, power_kw: float, h2_rate_kg_h: float, h2_remaining_pct: float):
        if detail_key == "db_power":
            return {
                "title": "Power Output", "unit": "kW", "value": power_kw, "history": DASH_HIST["power_kw"], "color": C["teal"],
                "show_plot": True,
                "diag": [("Energy Generated", f"{dash_state['energy_kwh']:.2f} kWh"), ("Performance Ratio", f"{dash_state['perf_ratio']:.1f}%")],
                "events": [f"Voltage output is dynamically regulated.", f"Current follows active load profile."],
            }
        if detail_key == "db_h2":
            return {
                "title": "Hydrogen Consumption", "unit": "kg/h", "value": h2_rate_kg_h, "history": DASH_HIST["h2_rate"], "color": C["amber"],
                "show_plot": True,
                "diag": [("Remaining Fuel", f"{dash_state['h2_remaining_kg']:.2f} kg"), ("Runtime Estimate", f"{dash_state['h2_remaining_kg'] / max(h2_rate_kg_h, 0.05):.2f} h")],
                "events": [f"Consumption tied to stack load.", f"Monitoring for low-fuel threshold alerts."],
            }
        if detail_key == "db_eff":
            return {
                "title": "System Efficiency", "unit": "%", "value": dash_state["elec_eff"], "history": DASH_HIST["efficiency"], "color": C["green"],
                "show_plot": True,
                "diag": [("Conversion Efficiency", f"{dash_state['conv_eff']:.1f}%"), ("Performance Ratio", f"{dash_state['perf_ratio']:.1f}%")],
                "events": [f"Efficiency can degrade under alarm/fault conditions."],
            }
        if detail_key == "db_health":
            health_score = max(0.0, 100.0 - abs(SENSORS['temp_1'].value - SENSORS['temp_2'].value) * 1.3)
            return {
                "title": "System Health", "unit": "score", "value": health_score, "history": DASH_HIST["efficiency"], "color": C["blue"],
                "show_plot": False,
                "diag": [("Active Alarms", str(len(ACTIVE_ALARMS))), ("E-STOP State", "ACTIVE" if emergency_state["active"] else "NORMAL")],
                "events": [a["msg"] for a in list(ALARMS)[:3]] or ["No recent health-related events."],
            }
        if detail_key == "db_tanks":
            return {
                "title": "Hydrogen Tank Levels", "unit": "%", "value": h2_remaining_pct, "history": detail_hist["h2_remaining_pct"], "color": C["teal"],
                "show_plot": True,
                "diag": [("Tank 1", f"{dash_state['h2_t1_remaining_kg']:.2f}/{dash_state['h2_t1_capacity_kg']:.0f} kg"),
                         ("Tank 2", f"{dash_state['h2_t2_remaining_kg']:.2f}/{dash_state['h2_t2_capacity_kg']:.0f} kg")],
                "events": [f"Usage history reflects fuel draw over runtime."],
            }
        if detail_key in {"db_tr_power_kw", "db_tr_h2_rate", "db_tr_efficiency"}:
            hist_map = {
                "db_tr_power_kw": ("Power Trend", "kW", power_kw, DASH_HIST["power_kw"], C["teal"]),
                "db_tr_h2_rate": ("Hydrogen Trend", "kg/h", h2_rate_kg_h, DASH_HIST["h2_rate"], C["amber"]),
                "db_tr_efficiency": ("Efficiency Trend", "%", dash_state["elec_eff"], DASH_HIST["efficiency"], C["green"]),
            }
            t, u, v, h, c = hist_map[detail_key]
            return {"title": t, "unit": u, "value": v, "history": h, "color": c, "show_plot": True, "diag": [("Window", f"{HISTORY_LEN} samples")], "events": ["Trend-focused drill-down view."]}
        if detail_key == "ana_stats":
            norm = sorted([s.pct * 100.0 for s in SENSORS.values()])
            n = len(norm)
            q = lambda p: norm[min(n - 1, max(0, int((n - 1) * p)))] if n else 0.0
            q1, med, q3 = q(0.25), q(0.50), q(0.75)
            outliers = sum(1 for s in SENSORS.values() if s.status != "OK")
            reliability = max(0.0, 100.0 - (outliers / max(len(SENSORS), 1)) * 100.0)

            stability_pairs = []
            for s in SENSORS.values():
                hv = list(s.history)
                mean = (sum(hv) / len(hv)) if hv else s.value
                var = (sum((x - mean) ** 2 for x in hv) / len(hv)) if hv else 0.0
                std = math.sqrt(var)
                span = max(abs(s.high - s.low), 1e-6)
                stability = max(0.0, 100.0 - (std / span) * 220.0)
                stability_pairs.append((stability, s.name))
            avg_stability = (sum(x for x, _ in stability_pairs) / len(stability_pairs)) if stability_pairs else 0.0
            most_unstable = sorted(stability_pairs, key=lambda x: x[0])[:3]
            unstable_txt = ", ".join(f"{name} ({score:.0f}%)" for score, name in most_unstable) if most_unstable else "None"

            return {
                "title": "Sensor Statistics", "unit": "%", "value": reliability, "history": detail_hist["stats_reliability"], "color": C["blue"], "show_plot": False,
                "diag": [
                    ("Distribution (Q1/Median/Q3)", f"{q1:.1f}% / {med:.1f}% / {q3:.1f}%"),
                    ("Outlier Sensors", f"{outliers} / {len(SENSORS)}"),
                    ("Average Stability Index", f"{avg_stability:.1f}%"),
                    ("Reliability Indicator", f"{reliability:.1f}%"),
                ],
                "events": [
                    f"Most unstable sensors: {unstable_txt}",
                    "Statistical card focuses on diagnostics instead of trend chart.",
                ],
            }
        if detail_key == "sys_health":
            return {"title": "System Health", "unit": "score", "value": 100.0 - min(len(ACTIVE_ALARMS) * 8.0, 60.0), "history": detail_hist["sys_alarm_events"], "color": C["green"], "show_plot": False,
                    "diag": [("Active Alarms", str(len(ACTIVE_ALARMS))), ("Alarm History Events", str(len(ALARM_HISTORY)))],
                    "events": [a["msg"] for a in list(ALARMS)[:4]] or ["No system health events."]}
        if detail_key == "sys_devices":
            return {"title": "Device Availability", "unit": "online", "value": detail_hist["device_online"][-1], "history": detail_hist["device_online"], "color": C["teal"], "show_plot": False,
                    "diag": [("Online Devices (mock)", f"{detail_hist['device_online'][-1]:.1f}"), ("Tracked Services", "10")],
                    "events": ["Device status card focuses on diagnostics and service states."]}
        if detail_key == "sys_alarm":
            return {"title": "System Alarms", "unit": "events", "value": float(len(ALARMS)), "history": detail_hist["sys_alarm_events"], "color": C["amber"], "show_plot": False,
                    "diag": [("Active", str(len(ACTIVE_ALARMS))), ("History Records", str(len(ALARM_HISTORY)))],
                    "events": [a["msg"] for a in list(ALARMS)[:5]] or ["No recent alarms."]}
        if detail_key == "net_config":
            mode = 1.0 if network_state["dhcp"] else 0.0
            return {"title": "Network Configuration", "unit": "mode", "value": mode, "history": detail_hist["net_signal"], "color": C["teal"], "show_plot": False,
                    "diag": [
                        ("Media", network_state["media"]),
                        ("DHCP", "ON" if network_state["dhcp"] else "OFF"),
                        ("Static IP", network_state["static_ip"]),
                        ("Subnet / Gateway", f"{network_state['subnet']} / {network_state['gateway']}"),
                        ("MQTT Broker", f"{network_state['mqtt_host']}:{network_state['mqtt_port']}"),
                        ("Telemetry Interval", network_state["telem_interval"]),
                    ],
                    "events": [network_state["apply_msg"] or "Configuration ready for apply."]}
        if detail_key == "net_plc":
            return {
                "title": "PLC / Field Communication", "unit": "state", "value": 1.0 if network_state["plc_status"] == "Online" else 0.0,
                "history": detail_hist["device_online"], "color": C["amber"], "show_plot": False,
                "diag": [
                    ("Protocol", network_state["plc_proto"]),
                    ("PLC Endpoint", f"{network_state['plc_ip']}:{network_state['plc_port']}"),
                    ("Connection Status", network_state["plc_status"]),
                    ("Communication Health", "Good" if network_state["plc_status"] == "Online" else "Check link"),
                ],
                "events": ["PLC communication diagnostics are shown without trend chart."],
            }
        if detail_key == "net_status":
            sig_pct = max(0.0, min(1.0, float(network_state["signal"]))) * 100.0
            return {"title": "Network Link Status", "unit": "%", "value": sig_pct, "history": detail_hist["net_signal"], "color": C["green"], "show_plot": True,
                    "diag": [("Status", network_state["status"]), ("IP", network_state["ip"])],
                    "events": [network_state["apply_msg"] or "Monitoring live link quality."]}
        return {"title": "Card Detail", "unit": "", "value": 0.0, "history": DASH_HIST["power_kw"], "color": C["teal"], "show_plot": False, "diag": [], "events": ["No mapped detail payload"]}

    async def simulate():
        while True:
            try:
                now = datetime.now()
                if not emergency_state["active"]:
                    # Tick all sensors
                    for s in SENSORS.values():
                        s.tick()

                    # Alarm lifecycle management (active + resolved + history)
                    for key, s in SENSORS.items():
                        if s.status == "OK":
                            _resolve_alarm(key, s, now)
                        else:
                            _raise_or_update_alarm(key, s, now)

                    fault_count = sum(
                        1 for s in SENSORS.values() if s.status != "OK"
                    )
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
                    split = random.uniform(0.45, 0.55)
                    use_t1_target = h2_used * split
                    use_t2_target = h2_used - use_t1_target
                    take_t1 = min(dash_state["h2_t1_remaining_kg"], use_t1_target)
                    leftover = h2_used - take_t1
                    take_t2 = min(dash_state["h2_t2_remaining_kg"], use_t2_target + leftover)
                    dash_state["h2_t1_remaining_kg"] = max(0.0, dash_state["h2_t1_remaining_kg"] - take_t1)
                    dash_state["h2_t2_remaining_kg"] = max(0.0, dash_state["h2_t2_remaining_kg"] - take_t2)
                    dash_state["h2_remaining_kg"] = (
                        dash_state["h2_t1_remaining_kg"] + dash_state["h2_t2_remaining_kg"]
                    )
                    h2_remaining_pct = (dash_state["h2_remaining_kg"] / dash_state["h2_capacity_kg"]) * 100.0
                    runtime_h = dash_state["h2_remaining_kg"] / max(h2_rate_kg_h, 0.05)

                    DASH_HIST["power_kw"].append(power_kw)
                    DASH_HIST["h2_rate"].append(h2_rate_kg_h)
                    DASH_HIST["efficiency"].append(dash_state["elec_eff"])
                    DASH_HIST["conv_eff"].append(dash_state["conv_eff"])
                    DASH_HIST["perf_ratio"].append(dash_state["perf_ratio"])
                else:
                    fault_count = sum(1 for s in SENSORS.values() if s.status != "OK")
                    dm = dashboard_metrics()
                    DASH_HIST["avg_temp"].append(dm["avg_temp"])
                    DASH_HIST["avg_pressure"].append(dm["avg_pressure"])
                    DASH_HIST["total_flow"].append(dm["total_flow"])
                    DASH_HIST["h2"].append(dm["h2"])
                    DASH_HIST["o2"].append(dm["o2"])

                    power_kw = 0.0
                    h2_rate_kg_h = 0.0
                    voltage_v = 0.0
                    current_a = 0.0
                    dash_state["elec_eff"] = 0.0
                    dash_state["conv_eff"] = 0.0
                    dash_state["perf_ratio"] = 0.0
                    h2_remaining_pct = (dash_state["h2_remaining_kg"] / dash_state["h2_capacity_kg"]) * 100.0
                    runtime_h = 0.0

                    DASH_HIST["power_kw"].append(0.0)
                    DASH_HIST["h2_rate"].append(0.0)
                    DASH_HIST["efficiency"].append(0.0)
                    DASH_HIST["conv_eff"].append(0.0)
                    DASH_HIST["perf_ratio"].append(0.0)

                active_alarm_count = len(ACTIVE_ALARMS)

                # Network connectivity simulation
                if network_state["status"] == "Connecting":
                    network_state["connect_ticks"] = max(0, int(network_state["connect_ticks"]) - 1)
                    network_state["signal"] = max(0.1, min(1.0, float(network_state["signal"]) + random.uniform(0.05, 0.15)))
                    network_state["mqtt_status"] = "Connecting"
                    network_state["plc_status"] = "Connecting"
                    network_state["latency_ms"] = "-"
                    network_state["packet_loss"] = "-"
                    if network_state["connect_ticks"] <= 0:
                        if random.random() < 0.88:
                            network_state["status"] = "Connected"
                            network_state["signal"] = max(0.35, min(1.0, float(network_state["signal"]) + random.uniform(0.1, 0.25)))
                            if network_state["dhcp"]:
                                network_state["ip"] = f"192.168.10.{random.randint(20, 230)}"
                            else:
                                network_state["ip"] = network_state["static_ip"] or "192.168.10.120"
                            network_state["mqtt_status"] = "Connected" if random.random() < 0.92 else "Degraded"
                            network_state["plc_status"] = "Online" if random.random() < 0.9 else "Fault"
                            network_state["latency_ms"] = f"{random.randint(18, 95)} ms"
                            network_state["packet_loss"] = f"{random.uniform(0.0, 1.8):.1f}%"
                            network_state["conn_result"] = "Passed"
                            network_state["apply_msg"] = f"{network_state['media']} connected"
                        else:
                            network_state["status"] = "Disconnected"
                            network_state["signal"] = 0.0
                            network_state["ip"] = "-"
                            network_state["mqtt_status"] = "Disconnected"
                            network_state["plc_status"] = "Disconnected"
                            network_state["conn_result"] = "Failed"
                            network_state["apply_msg"] = "Connection failed"
                elif network_state["status"] == "Connected":
                    network_state["signal"] = max(0.3, min(1.0, float(network_state["signal"]) + random.uniform(-0.07, 0.08)))
                    network_state["latency_ms"] = f"{random.randint(18, 95)} ms"
                    network_state["packet_loss"] = f"{random.uniform(0.0, 2.5):.1f}%"
                    if random.random() < 0.03:
                        network_state["mqtt_status"] = "Degraded"
                    else:
                        network_state["mqtt_status"] = "Connected"
                    if random.random() < 0.03:
                        network_state["plc_status"] = "Fault"
                    else:
                        network_state["plc_status"] = "Online"
                    if random.random() < 0.01:
                        network_state["status"] = "Disconnected"
                        network_state["signal"] = 0.0
                        network_state["ip"] = "-"
                        network_state["mqtt_status"] = "Disconnected"
                        network_state["plc_status"] = "Disconnected"
                        network_state["conn_result"] = "Failed"
                        network_state["apply_msg"] = "Link dropped"
                else:
                    network_state["signal"] = max(0.0, float(network_state["signal"]) - 0.08)
                    network_state["mqtt_status"] = "Disconnected"
                    network_state["plc_status"] = "Disconnected"
                    network_state["latency_ms"] = "-"
                    network_state["packet_loss"] = "-"

                detail_hist["h2_remaining_pct"].append(h2_remaining_pct)
                detail_hist["sys_alarm_events"].append(float(len(ALARMS)))
                detail_hist["net_signal"].append(max(0.0, min(1.0, float(network_state["signal"]))) * 100.0)
                detail_hist["device_online"].append(8.0 + random.uniform(-0.3, 0.3))
                stats_reliability = max(0.0, 100.0 - (sum(1 for s in SENSORS.values() if s.status != "OK") / max(len(SENSORS), 1)) * 100.0)
                detail_hist["stats_reliability"].append(stats_reliability)

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
                        if emergency_state["active"]:
                            h2rt_ref.current.value = "Estimated Runtime Remaining: Paused (E-STOP)"
                        else:
                            h2rt_ref.current.value = f"Estimated Runtime Remaining: {runtime_h:.1f} h"
                    if h2b_ref and h2b_ref.current:
                        h2b_ref.current.value = max(0.0, min(1.0, h2_remaining_pct / 100.0))

                    # Tank ring indicators
                    t1_pct = (dash_state["h2_t1_remaining_kg"] / dash_state["h2_t1_capacity_kg"]) * 100.0
                    t2_pct = (dash_state["h2_t2_remaining_kg"] / dash_state["h2_t2_capacity_kg"]) * 100.0

                    # Keep both tanks visually identical (same color scheme)
                    def tank_col(pct):
                        return C["teal"]

                    t1p_ref = refs.get("db_fc_t1_pct")
                    t1r_ref = refs.get("db_fc_t1_ring")
                    t1v_ref = refs.get("db_fc_t1_vol")
                    t2p_ref = refs.get("db_fc_t2_pct")
                    t2r_ref = refs.get("db_fc_t2_ring")
                    t2v_ref = refs.get("db_fc_t2_vol")

                    if t1p_ref and t1p_ref.current:
                        t1p_ref.current.value = f"{t1_pct:.0f}%"
                    if t1r_ref and t1r_ref.current:
                        t1r_ref.current.controls = [
                            draw_ring_meter(
                                max(0.0, min(1.0, t1_pct / 100.0)),
                                size=116, stroke=12, color=tank_col(t1_pct)
                            )
                        ]
                    if t1v_ref and t1v_ref.current:
                        t1v_ref.current.value = f"{dash_state['h2_t1_remaining_kg']:.1f} / {dash_state['h2_t1_capacity_kg']:.0f} kg"

                    if t2p_ref and t2p_ref.current:
                        t2p_ref.current.value = f"{t2_pct:.0f}%"
                    if t2r_ref and t2r_ref.current:
                        t2r_ref.current.controls = [
                            draw_ring_meter(
                                max(0.0, min(1.0, t2_pct / 100.0)),
                                size=116, stroke=12, color=tank_col(t2_pct)
                            )
                        ]
                    if t2v_ref and t2v_ref.current:
                        t2v_ref.current.value = f"{dash_state['h2_t2_remaining_kg']:.1f} / {dash_state['h2_t2_capacity_kg']:.0f} kg"

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

                    # Fuel-cell trend monitoring (separate metric cards)
                    tr_p_val_ref = refs.get("db_tr_power_kw_val")
                    tr_p_plot_ref = refs.get("db_tr_power_kw_plot")
                    tr_h2_val_ref = refs.get("db_tr_h2_rate_val")
                    tr_h2_plot_ref = refs.get("db_tr_h2_rate_plot")
                    tr_e_val_ref = refs.get("db_tr_efficiency_val")
                    tr_e_plot_ref = refs.get("db_tr_efficiency_plot")

                    if tr_p_val_ref and tr_p_val_ref.current:
                        tr_p_val_ref.current.value = f"{power_kw:.1f}"
                    if tr_p_plot_ref and tr_p_plot_ref.current:
                        tr_p_plot_ref.current.controls = [
                            draw_line_chart([(DASH_HIST["power_kw"], C["teal"])], w=280, h=170)
                        ]

                    if tr_h2_val_ref and tr_h2_val_ref.current:
                        tr_h2_val_ref.current.value = f"{h2_rate_kg_h:.2f}"
                    if tr_h2_plot_ref and tr_h2_plot_ref.current:
                        tr_h2_plot_ref.current.controls = [
                            draw_line_chart([(DASH_HIST["h2_rate"], C["amber"])], w=280, h=170)
                        ]

                    if tr_e_val_ref and tr_e_val_ref.current:
                        tr_e_val_ref.current.value = f"{dash_state['elec_eff']:.1f}"
                    if tr_e_plot_ref and tr_e_plot_ref.current:
                        tr_e_plot_ref.current.controls = [
                            draw_line_chart([(DASH_HIST["efficiency"], C["green"])], w=280, h=170)
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
                    pass

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

                # —— PAGE 5: Network Settings —————————————————————
                elif idx == 5:
                    stat_dot_ref = refs.get("net_status_dot")
                    stat_txt_ref = refs.get("net_status_txt")
                    ip_ref = refs.get("net_ip_txt")
                    sig_bar_ref = refs.get("net_sig_bar")
                    sig_txt_ref = refs.get("net_sig_txt")
                    mqtt_dot_ref = refs.get("net_mqtt_dot")
                    mqtt_txt_ref = refs.get("net_mqtt_txt")
                    plc_dot_ref = refs.get("net_plc_dot")
                    plc_txt_ref = refs.get("net_plc_txt")
                    lat_ref = refs.get("net_latency")
                    loss_ref = refs.get("net_packet_loss")
                    last_ref = refs.get("net_last_attempt")
                    ping_ref = refs.get("net_ping_result")
                    conn_ref = refs.get("net_conn_result")
                    sec_ref = refs.get("net_sec_msg")
                    apply_msg_ref = refs.get("net_apply_msg")

                    status_color = C["green"] if network_state["status"] == "Connected" else (
                        C["amber"] if network_state["status"] == "Connecting" else C["red"]
                    )
                    mqtt_color = C["green"] if network_state["mqtt_status"] == "Connected" else (
                        C["amber"] if network_state["mqtt_status"] in {"Connecting", "Degraded"} else C["red"]
                    )
                    plc_color = C["green"] if network_state["plc_status"] == "Online" else (
                        C["amber"] if network_state["plc_status"] == "Connecting" else C["red"]
                    )

                    if stat_dot_ref and stat_dot_ref.current:
                        stat_dot_ref.current.bgcolor = status_color
                    if stat_txt_ref and stat_txt_ref.current:
                        stat_txt_ref.current.value = network_state["status"]
                        stat_txt_ref.current.color = status_color
                    if ip_ref and ip_ref.current:
                        ip_ref.current.value = f"Current Assigned IP: {network_state['ip']}"
                    if sig_bar_ref and sig_bar_ref.current:
                        sig_bar_ref.current.value = max(0.0, min(1.0, float(network_state["signal"])))
                        sig_bar_ref.current.color = status_color
                    if sig_txt_ref and sig_txt_ref.current:
                        sig_txt_ref.current.value = f"{int(max(0.0, min(1.0, float(network_state['signal']))) * 100)}%"
                        sig_txt_ref.current.color = status_color
                    if mqtt_dot_ref and mqtt_dot_ref.current:
                        mqtt_dot_ref.current.bgcolor = mqtt_color
                    if mqtt_txt_ref and mqtt_txt_ref.current:
                        mqtt_txt_ref.current.value = f"MQTT: {network_state['mqtt_status']}"
                        mqtt_txt_ref.current.color = mqtt_color
                    if plc_dot_ref and plc_dot_ref.current:
                        plc_dot_ref.current.bgcolor = plc_color
                    if plc_txt_ref and plc_txt_ref.current:
                        plc_txt_ref.current.value = f"PLC: {network_state['plc_status']}"
                        plc_txt_ref.current.color = plc_color
                    if lat_ref and lat_ref.current:
                        lat_ref.current.value = network_state.get("latency_ms", "-")
                    if loss_ref and loss_ref.current:
                        loss_ref.current.value = network_state.get("packet_loss", "-")
                    if last_ref and last_ref.current:
                        last_ref.current.value = network_state.get("last_attempt", "-")
                    if ping_ref and ping_ref.current:
                        ping_ref.current.value = network_state.get("ping_result", "-")
                    if conn_ref and conn_ref.current:
                        conn_ref.current.value = network_state.get("conn_result", "-")
                    if sec_ref and sec_ref.current:
                        if network_state.get("tls") and network_state.get("auth"):
                            sec_ref.current.value = "Security posture: TLS + Authentication enabled."
                            sec_ref.current.color = C["green"]
                        elif network_state.get("tls") or network_state.get("auth"):
                            sec_ref.current.value = "Security posture: Partially enabled."
                            sec_ref.current.color = C["amber"]
                        else:
                            sec_ref.current.value = "Security posture: Insecure (TLS/Auth disabled)."
                            sec_ref.current.color = C["red"]
                    if apply_msg_ref and apply_msg_ref.current:
                        apply_msg_ref.current.value = network_state["apply_msg"]

                # —— PAGE 6: Card Detail Drill-down ————————————————
                elif idx == 6:
                    key = selected_card.get("key") or "db_power"
                    payload = _detail_payload(
                        key, power_kw, h2_rate_kg_h, h2_remaining_pct
                    )
                    title = payload["title"]
                    unit = payload["unit"]
                    value = payload["value"]
                    history = payload["history"]
                    color = payload["color"]
                    show_plot = payload.get("show_plot", True)
                    diag_items = payload.get("diag", [])
                    event_items = payload.get("events", [])
                    min_v, max_v, avg_v = _stats(history)
                    status_txt, status_col = _status_from_value(key, value)

                    t_ref = refs.get("cd_title")
                    s_ref = refs.get("cd_subtitle")
                    ov_ref = refs.get("cd_overview_card")
                    v_ref = refs.get("cd_value")
                    u_ref = refs.get("cd_unit")
                    min_ref = refs.get("cd_min")
                    max_ref = refs.get("cd_max")
                    avg_ref = refs.get("cd_avg")
                    sd_ref = refs.get("cd_status_dot")
                    st_ref = refs.get("cd_status_txt")
                    pc_ref = refs.get("cd_plot_card")
                    p_ref = refs.get("cd_plot")
                    d_ref = refs.get("cd_diag_col")
                    e_ref = refs.get("cd_events_col")
                    sc_ref = refs.get("cd_stats_card")
                    sr_ref = refs.get("cd_stats_rows")
                    dc_ref = refs.get("cd_devices_card")
                    dr_ref = refs.get("cd_devices_rows")
                    epc_ref = refs.get("cd_eff_plots_card")
                    ee_ref = refs.get("cd_eff_ele_row")
                    ec_ref = refs.get("cd_eff_conv_row")
                    epr_ref = refs.get("cd_eff_pr_row")

                    if t_ref and t_ref.current:
                        t_ref.current.value = title
                    if s_ref and s_ref.current:
                        s_ref.current.value = f"Drill-down detail • key: {key}"
                    if ov_ref and ov_ref.current:
                        ov_ref.current.visible = key not in {"ana_stats", "sys_devices", "net_config", "net_plc"}
                    if v_ref and v_ref.current:
                        v_ref.current.value = f"{value:.2f}"
                        v_ref.current.color = color
                    if u_ref and u_ref.current:
                        u_ref.current.value = unit
                    if min_ref and min_ref.current:
                        min_ref.current.value = f"{min_v:.2f}"
                    if max_ref and max_ref.current:
                        max_ref.current.value = f"{max_v:.2f}"
                    if avg_ref and avg_ref.current:
                        avg_ref.current.value = f"{avg_v:.2f}"
                    if sd_ref and sd_ref.current:
                        sd_ref.current.bgcolor = status_col
                    if st_ref and st_ref.current:
                        st_ref.current.value = status_txt
                        st_ref.current.color = status_col
                    if pc_ref and pc_ref.current:
                        pc_ref.current.visible = show_plot and key != "db_eff"
                    if sc_ref and sc_ref.current:
                        sc_ref.current.visible = (key == "ana_stats")
                    if dc_ref and dc_ref.current:
                        dc_ref.current.visible = (key == "sys_devices")
                    if epc_ref and epc_ref.current:
                        epc_ref.current.visible = (key == "db_eff")
                    if p_ref and p_ref.current:
                        p_ref.current.controls = [
                            draw_line_chart([(history, color)], w=940, h=280)
                        ]
                    if key == "db_eff":
                        if ee_ref and ee_ref.current:
                            ee_ref.current.controls = [
                                draw_line_chart([(DASH_HIST["efficiency"], C["green"])], w=940, h=110)
                            ]
                        if ec_ref and ec_ref.current:
                            ec_ref.current.controls = [
                                draw_line_chart([(DASH_HIST["conv_eff"], C["teal"])], w=940, h=110)
                            ]
                        if epr_ref and epr_ref.current:
                            epr_ref.current.controls = [
                                draw_line_chart([(DASH_HIST["perf_ratio"], C["blue"])], w=940, h=110)
                            ]
                    if d_ref and d_ref.current:
                        d_ref.current.controls = [
                            ft.Row([
                                ft.Text(lbl, color=C["gray"], size=11, width=180),
                                ft.Text(val, color=C["white"], size=11, weight=ft.FontWeight.W_600),
                            ], spacing=8)
                            for lbl, val in diag_items
                        ] or [ft.Text("No diagnostics available.", color=C["gray"], size=11)]
                    if e_ref and e_ref.current:
                        e_ref.current.controls = [
                            ft.Text(f"• {line}", color=C["gray"], size=11)
                            for line in event_items
                        ] or [ft.Text("No related events.", color=C["gray"], size=11)]
                    if key == "ana_stats" and sr_ref and sr_ref.current:
                        stat_rows = []
                        for s in SENSORS.values():
                            vals = list(s.history)
                            avg = (sum(vals) / len(vals)) if vals else s.value
                            stat_rows.append(ft.Row([
                                ft.Text(s.name, color=C["white"], size=12, width=170),
                                ft.Text(s.fmt(), color=s.color, size=12, width=80, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{min(vals):.2f}" if vals else "-", color=C["gray"], size=12, width=80),
                                ft.Text(f"{max(vals):.2f}" if vals else "-", color=C["gray"], size=12, width=80),
                                ft.Text(f"{avg:.2f}", color=C["gray"], size=12, width=80),
                                badge(s.status, STATUS_COLOR[s.status]),
                            ], spacing=0))
                        sr_ref.current.controls = stat_rows or [ft.Text("No statistics available.", color=C["gray"], size=11)]
                    if key == "sys_devices" and dr_ref and dr_ref.current:
                        devices = [
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
                        dev_rows = []
                        for name, status, col in devices:
                            dev_rows.append(ft.Row([
                                ft.Container(width=8, height=8, border_radius=4, bgcolor=col),
                                ft.Container(width=8),
                                ft.Text(name, color=C["white"], size=12, expand=True),
                                badge(status, col),
                            ], spacing=0))
                        dr_ref.current.controls = dev_rows or [ft.Text("No device data available.", color=C["gray"], size=11)]

                page.update()

            except Exception as ex:
                print(f"[SIM] {ex}")
                continue
            await asyncio.sleep(1.5)

    page.run_task(simulate)

