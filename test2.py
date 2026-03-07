"""
HMI Production Dashboard — Flet 0.80+ compatible
Run: python hmi_dashboard.py
"""

import flet as ft
import flet.canvas as cv
import random
import time
import threading
import math
from datetime import datetime

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK   = "#0f1318"
BG_CARD   = "#181d24"
BG_CARD2  = "#1c2229"
TEAL      = "#00e5c8"
RED       = "#ff4444"
WHITE     = "#ffffff"
GRAY      = "#7a8799"
DIM       = "#2e3848"
BORDER    = "#232b36"
HEADER_BG = "#12171e"


# ── Helpers ───────────────────────────────────────────────────────────────────
def card(content, padding=14, expand=False):
    return ft.Container(
        content=content,
        bgcolor=BG_CARD,
        border_radius=10,
        padding=padding,
        border=ft.Border(
            left=ft.BorderSide(1, BORDER),
            right=ft.BorderSide(1, BORDER),
            top=ft.BorderSide(1, BORDER),
            bottom=ft.BorderSide(1, BORDER),
        ),
        expand=expand,
    )


def section_header(icon_name, title):
    return ft.Row([
        ft.Icon(icon_name, color=TEAL, size=15),
        ft.Text(title, color=WHITE, size=13, weight=ft.FontWeight.W_600),
    ], spacing=6)


def divider():
    return ft.Container(height=1, bgcolor=BORDER)


# ── Arc gauge ─────────────────────────────────────────────────────────────────
def build_arc_gauge(value: float, size: float = 190, stroke: float = 13,
                    label: str = "99", unit: str = "%", label_size: float = 42):
    start   = math.pi * 0.75
    sweep_f = math.pi * 1.5
    sweep_v = sweep_f * max(0.0, min(1.0, value))
    pad     = stroke + 2

    shapes = [
        cv.Arc(
            x=pad, y=pad,
            width=size - pad * 2, height=size - pad * 2,
            start_angle=start, sweep_angle=sweep_f,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=DIM,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ),
    ]
    if sweep_v > 0.01:
        shapes.append(cv.Arc(
            x=pad, y=pad,
            width=size - pad * 2, height=size - pad * 2,
            start_angle=start, sweep_angle=sweep_v,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=TEAL,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ))

    canvas  = cv.Canvas(shapes=shapes, width=size, height=size)
    overlay = ft.Container(
        width=size, height=size,
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            [
                ft.Text(label, color=WHITE, size=label_size,
                        weight=ft.FontWeight.BOLD),
                ft.Text(unit, color=GRAY, size=int(label_size * 0.38)),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
    )
    return ft.Stack(controls=[canvas, overlay], width=size, height=size)


# ── Semi-arc gauge ────────────────────────────────────────────────────────────
def build_semi_gauge(value: float, w: float = 180, h: float = 95, stroke: float = 11):
    start   = math.pi
    sweep_f = math.pi
    sweep_v = sweep_f * max(0.0, min(1.0, value))
    pad     = stroke + 2

    shapes = [
        cv.Arc(
            x=pad, y=pad,
            width=w - pad * 2, height=(h - pad) * 2,
            start_angle=start, sweep_angle=sweep_f,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=DIM,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ),
    ]
    if sweep_v > 0.01:
        shapes.append(cv.Arc(
            x=pad, y=pad,
            width=w - pad * 2, height=(h - pad) * 2,
            start_angle=start, sweep_angle=sweep_v,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=TEAL,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ))

    return cv.Canvas(shapes=shapes, width=w, height=h)


# ── Bar chart ─────────────────────────────────────────────────────────────────
def build_bar_chart(values, w: float = 175, h: float = 75):
    n     = len(values)
    gap   = 5
    bar_w = (w - gap * (n - 1)) / n
    shapes = []
    for i, v in enumerate(values):
        bh = max(4.0, h * v)
        x  = i * (bar_w + gap)
        y  = h - bh
        shapes.append(cv.Rect(
            x=x, y=y, width=bar_w, height=bh,
            border_radius=3,
            paint=ft.Paint(color=TEAL),
        ))
    return cv.Canvas(shapes=shapes, width=w, height=h)


# ── Toggle ────────────────────────────────────────────────────────────────────
def build_toggle(initial: bool):
    state = {"on": initial}
    thumb = ft.Container(
        width=14, height=14, border_radius=7, bgcolor=WHITE,
        margin=ft.Margin.only(left=21 if initial else 3, top=3),
    )
    track = ft.Container(
        width=38, height=20, border_radius=10,
        bgcolor=TEAL if initial else DIM,
        content=thumb,
    )

    def toggle(e):
        state["on"] = not state["on"]
        track.bgcolor = TEAL if state["on"] else DIM
        thumb.margin  = ft.Margin.only(left=21 if state["on"] else 3, top=3)
        track.update()

    track.on_click = toggle
    return track


# ── Playback button ───────────────────────────────────────────────────────────
def ctrl_btn(icon):
    return ft.Container(
        content=ft.Icon(icon, color=GRAY, size=18),
        width=38, height=38, border_radius=19,
        bgcolor=BG_CARD2,
        border=ft.Border(
            left=ft.BorderSide(1, BORDER),
            right=ft.BorderSide(1, BORDER),
            top=ft.BorderSide(1, BORDER),
            bottom=ft.BorderSide(1, BORDER),
        ),
        alignment=ft.Alignment(0, 0),
        ink=True,
    )


# ── Safe icon lookup ──────────────────────────────────────────────────────────
def icon(name: str):
    """Return ft.Icons.NAME falling back gracefully if not found."""
    return getattr(ft.Icons, name, ft.Icons.CIRCLE)


# ── Main ──────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title         = "HMI Production Dashboard"
    page.bgcolor       = BG_DARK
    page.window.width  = 1120
    page.window.height = 720
    page.padding       = 0

    S = {
        "items_good":     40000,
        "items_rejected": 40,
        "speed_ppm":      23,
        "speed_pct":      0.80,
        "prod_pct":       0.99,
        "bars": [0.50, 0.65, 0.40, 0.80, 0.55, 0.90, 0.70],
    }

    # ── Refs ──────────────────────────────────────────────────────────────
    r_clock    = ft.Ref[ft.Text]()
    r_good     = ft.Ref[ft.Text]()
    r_rej      = ft.Ref[ft.Text]()
    r_spd_num  = ft.Ref[ft.Text]()
    r_spd_pct  = ft.Ref[ft.Text]()
    r_semi_row = ft.Ref[ft.Row]()
    r_prod_row = ft.Ref[ft.Row]()
    r_bar_row  = ft.Ref[ft.Row]()

    # ── Top bar ───────────────────────────────────────────────────────────
    topbar = ft.Container(
        bgcolor=HEADER_BG,
        padding=ft.Padding.symmetric(horizontal=20, vertical=11),
        border=ft.Border(
            bottom=ft.BorderSide(1, BORDER),
        ),
        content=ft.Row([
            ft.Row([
                ft.Icon(icon("MENU"), color=GRAY, size=18),
                ft.Container(width=10),
                ft.Text("Production / Execute", color=WHITE,
                        size=15, weight=ft.FontWeight.W_600),
            ]),
            ft.Row([
                ft.Text(
                    datetime.now().strftime("%H:%M  %d %b"),
                    ref=r_clock, color=GRAY, size=12,
                ),
                ft.Container(width=14),
                ft.Icon(icon("NOTIFICATIONS_NONE"),       color=GRAY, size=20),
                ft.Icon(icon("CHAT_BUBBLE_OUTLINE"),      color=GRAY, size=20),
                ft.Icon(icon("ACCOUNT_CIRCLE_OUTLINED"),  color=GRAY, size=20),
                ft.Icon(icon("APPS"),                     color=GRAY, size=20),
            ], spacing=12),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    )

    # ── Items Overview ────────────────────────────────────────────────────
    items_card = card(
        ft.Column([
            section_header(icon("SHOW_CHART"), "Items Overview"),
            ft.Container(height=14),
            ft.Text("Items Good", color=GRAY, size=11),
            ft.Row([
                ft.Text(f"{S['items_good']:,}", ref=r_good,
                        color=WHITE, size=28, weight=ft.FontWeight.BOLD),
                ft.Text("PCS", color=GRAY, size=12),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=5),
            ft.Container(height=12),
            ft.Text("Items Rejected", color=GRAY, size=11),
            ft.Row([
                ft.Text(str(S["items_rejected"]), ref=r_rej,
                        color=RED, size=22, weight=ft.FontWeight.BOLD),
                ft.Text("PCS", color=GRAY, size=12),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=5),
        ], spacing=2),
        expand=True,
    )

    # ── Current Speed ─────────────────────────────────────────────────────
    speed_card = card(
        ft.Column([
            section_header(icon("SPEED"), "Current Speed"),
            ft.Container(height=8),
            ft.Text("Current Speed", color=GRAY, size=11),
            ft.Row([
                ft.Text(str(S["speed_ppm"]), ref=r_spd_num,
                        color=WHITE, size=26, weight=ft.FontWeight.BOLD),
                ft.Text("PPM", color=GRAY, size=12),
            ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=5),
            ft.Container(height=6),
            ft.Row(
                [build_semi_gauge(S["speed_pct"])],
                ref=r_semi_row,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row([
                ft.Text(f"{int(S['speed_pct']*100)}%", ref=r_spd_pct,
                        color=TEAL, size=18, weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=2),
        expand=True,
    )

    # ── Production Overview ───────────────────────────────────────────────
    prod_card = card(
        ft.Column([
            section_header(icon("FACTORY"), "Production Overview"),
            ft.Container(height=14),
            ft.Row(
                [build_arc_gauge(S["prod_pct"])],
                ref=r_prod_row,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        expand=True,
    )

    # ── Controls ──────────────────────────────────────────────────────────
    def ctrl_row(label, toggle):
        return ft.Row([
            ft.Text(label, color=GRAY, size=12, expand=True),
            toggle,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
           vertical_alignment=ft.CrossAxisAlignment.CENTER)

    controls_card = card(
        ft.Column([
            section_header(icon("TUNE"), "Controls"),
            ft.Container(height=10),
            ctrl_row("Paper Check", build_toggle(True)),
            divider(),
            ctrl_row("Empty Out",   build_toggle(False)),
            divider(),
            ctrl_row("Reject All",  build_toggle(True)),
        ], spacing=8),
        expand=True,
    )

    # ── Levels ────────────────────────────────────────────────────────────
    levels_card = card(
        ft.Column([
            section_header(icon("BAR_CHART"), "Levels"),
            ft.Container(height=6),
            ft.Row([
                ft.Container(width=9, height=9, bgcolor=TEAL, border_radius=2),
                ft.Text("Volume",  color=GRAY, size=11),
                ft.Container(width=6),
                ft.Container(width=9, height=9, bgcolor=DIM,  border_radius=2),
                ft.Text("Service", color=GRAY, size=11),
            ], spacing=4),
            ft.Container(height=10),
            ft.Row(
                [build_bar_chart(S["bars"])],
                ref=r_bar_row,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ], spacing=0),
        expand=True,
    )

    # ── Playback bar ──────────────────────────────────────────────────────
    playback = ft.Container(
        content=ft.Row([
            ctrl_btn(icon("STOP")),
            ctrl_btn(icon("PLAY_ARROW")),
            ctrl_btn(icon("PAUSE")),
            ctrl_btn(icon("REFRESH")),
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(vertical=10),
        border=ft.Border(top=ft.BorderSide(1, BORDER)),
    )

    # ── Layout ────────────────────────────────────────────────────────────
    right_top = ft.Row(
        [items_card, speed_card], spacing=12, expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    right_bot = ft.Row(
        [controls_card, levels_card], spacing=12, expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    right_col = ft.Column([right_top, right_bot], spacing=12, expand=True)
    main_row  = ft.Row(
        [prod_card, right_col], spacing=12, expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    body = ft.Container(
        content=ft.Column([main_row, playback], spacing=0, expand=True),
        padding=16, expand=True,
    )

    page.add(ft.Column([topbar, body], spacing=0, expand=True))

    # ── Simulation ────────────────────────────────────────────────────────
    def simulate():
        while True:
            time.sleep(1.5)
            try:
                S["items_good"]     += random.randint(0, 6)
                S["items_rejected"]  = max(0, S["items_rejected"] + random.randint(-1, 2))
                S["speed_ppm"]       = max(5,  min(60,  S["speed_ppm"]  + random.randint(-2, 3)))
                S["speed_pct"]       = max(0.1, min(1.0, S["speed_pct"] + random.uniform(-0.05, 0.05)))
                S["prod_pct"]        = max(0.80, min(1.0, S["prod_pct"] + random.uniform(-0.005, 0.005)))
                S["bars"] = [
                    max(0.08, min(1.0, v + random.uniform(-0.12, 0.12)))
                    for v in S["bars"]
                ]

                r_clock.current.value   = datetime.now().strftime("%H:%M  %d %b")
                r_good.current.value    = f"{S['items_good']:,}"
                r_rej.current.value     = str(S["items_rejected"])
                r_spd_num.current.value = str(S["speed_ppm"])
                r_spd_pct.current.value = f"{int(S['speed_pct']*100)}%"

                r_semi_row.current.controls[0] = build_semi_gauge(S["speed_pct"])
                r_prod_row.current.controls[0] = build_arc_gauge(
                    S["prod_pct"], label=str(int(S["prod_pct"] * 100))
                )
                r_bar_row.current.controls[0] = build_bar_chart(S["bars"])

                page.update()
            except Exception as ex:
                print("Sim stopped:", ex)
                break

    threading.Thread(target=simulate, daemon=True).start()


ft.run(main)