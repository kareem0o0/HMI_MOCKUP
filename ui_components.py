"""Reusable UI components and chart primitives."""

import math, collections
import flet as ft
import flet.canvas as cv

from models import C, STATUS_COLOR, HISTORY_LEN

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


def draw_ring_meter(value: float, size=116, stroke=12, color=C["green"]):
    start = math.pi * 0.75
    sweep_f = math.pi * 1.5
    sweep_v = sweep_f * max(0.0, min(1.0, value))
    pad = stroke + 2
    d = size - pad * 2

    def alpha(col, a):
        return f"{col}{a}" if len(col) == 7 else col

    shapes = [
        cv.Arc(
            x=pad, y=pad, width=d, height=d,
            start_angle=start, sweep_angle=sweep_f,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=C["gray2"],
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )
    ]
    if sweep_v > 0.01:
        shapes.append(cv.Arc(
            x=pad, y=pad, width=d, height=d,
            start_angle=start, sweep_angle=sweep_v,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=stroke, color=color,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ))
        shapes.append(cv.Arc(
            x=pad, y=pad, width=d, height=d,
            start_angle=start, sweep_angle=sweep_v,
            paint=ft.Paint(
                style=ft.PaintingStyle.STROKE,
                stroke_width=max(2, int(stroke * 0.35)),
                color=alpha(color, "88"),
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        ))
    return cv.Canvas(shapes=shapes, width=size, height=size)


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


def draw_line_chart_canvas(histories: list[tuple, str], w=500, h=160):
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


def axis_ticks_from_values(values: list[float]) -> tuple[str, str, str]:
    if not values:
        return "-", "-", "-"
    lo = min(values)
    hi = max(values)
    mid = (lo + hi) / 2.0
    return format_axis_value(hi), format_axis_value(mid), format_axis_value(lo)


def draw_line_chart(histories: list[tuple, str], w=500, h=160, show_y_axis=True):
    """histories = [(deque_of_values, color), ...]"""
    if not show_y_axis:
        return draw_line_chart_canvas(histories, w=w, h=h)

    y_axis_w = 40
    gap = 8
    chart_w = max(60, w - y_axis_w - gap)
    all_vals = []
    for history, _ in histories:
        all_vals.extend(list(history))
    top, mid, bot = axis_ticks_from_values(all_vals)

    return ft.Row([
        ft.Column([
            ft.Text(top, color=C["gray"], size=9, text_align=ft.TextAlign.RIGHT),
            ft.Container(expand=True),
            ft.Text(mid, color=C["gray"], size=9, text_align=ft.TextAlign.RIGHT),
            ft.Container(expand=True),
            ft.Text(bot, color=C["gray"], size=9, text_align=ft.TextAlign.RIGHT),
        ], width=y_axis_w, height=h,
           horizontal_alignment=ft.CrossAxisAlignment.END,
           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(width=gap),
        draw_line_chart_canvas(histories, w=chart_w, h=h),
    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER,
       vertical_alignment=ft.CrossAxisAlignment.START)


def format_axis_value(v: float) -> str:
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def axis_ticks_from_history(history) -> tuple[str, str, str]:
    return axis_ticks_from_values(list(history))


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

