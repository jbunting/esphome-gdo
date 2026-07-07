# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
"""Generate the wiring schematic SVGs (docs/schematic.svg and
docs/schematic-no-obstruction.svg).

Representative drawing of the canonical ratgdo/gdolib Security+ interface (an
inverting N-MOSFET half-duplex single-wire front end). Exact component
values/placement are per https://github.com/Kaldek/rat-ratgdo. The TX and RX
level-shifters are drawn as self-contained sub-blocks so wiring stays clean.
"""
import os

W, H = 960, 560


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wire(*pts):
    return f'<polyline class="w" points="{" ".join(f"{x},{y}" for x, y in pts)}"/>'


def dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="3.6" fill="#111"/>'


def text(x, y, s, cls="lbl", anchor="start"):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{esc(s)}</text>'


def res(x1, y1, x2, y2, label):
    body = 44
    if y1 == y2:
        cx = (x1 + x2) / 2
        return "".join([wire((x1, y1), (cx - body / 2, y1)), wire((cx + body / 2, y1), (x2, y2)),
                        f'<rect class="c" x="{cx-body/2}" y="{y1-8}" width="{body}" height="16"/>',
                        text(cx, y1 + 21, label, "val", "middle")])  # label below to clear titles
    cy = (y1 + y2) / 2
    return "".join([wire((x1, y1), (x1, cy - body / 2)), wire((x1, cy + body / 2), (x2, y2)),
                    f'<rect class="c" x="{x1-8}" y="{cy-body/2}" width="16" height="{body}"/>',
                    text(x1 + 13, cy + 4, label, "val", "start")])


def nmos(cx, cy, gate):
    ct, cb = cy - 20, cy + 20
    gbx = cx - 10 if gate == "L" else cx + 10
    glead = gbx - 26 if gate == "L" else gbx + 26
    sx = cx + 22 if gate == "L" else cx - 22
    p = [f'<line class="w" x1="{cx}" y1="{ct}" x2="{cx}" y2="{cb}"/>',
         f'<line class="w" x1="{gbx}" y1="{ct}" x2="{gbx}" y2="{cb}"/>',
         wire((gbx, cy), (glead, cy)),
         wire((cx, ct), (sx, ct), (sx, ct - 16)),
         wire((cx, cb), (sx, cb), (sx, cb + 16))]
    return "".join(p), {"G": (glead, cy), "D": (sx, ct - 16), "S": (sx, cb + 16)}


def gnd(x, y):
    return "".join([wire((x, y), (x, y + 9)),
                    f'<line class="w" x1="{x-10}" y1="{y+9}" x2="{x+10}" y2="{y+9}"/>',
                    f'<line class="w" x1="{x-6}" y1="{y+13}" x2="{x+6}" y2="{y+13}"/>',
                    f'<line class="w" x1="{x-2.5}" y1="{y+17}" x2="{x+2.5}" y2="{y+17}"/>'])


def supply(x, y, label):
    return "".join([wire((x, y), (x, y - 11)),
                    f'<line class="w" x1="{x-10}" y1="{y-11}" x2="{x+10}" y2="{y-11}"/>',
                    text(x, y - 16, label, "val", "middle")])


def terminal(x, y, label, color, ldy=4):
    return (f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" stroke="#111" stroke-width="1.5"/>'
            + text(x + 13, y + ldy, label, "lbl", "start"))


def opto(cx, cy, led):
    """Optocoupler straddling the isolation barrier at x=cx. led='L' puts the
    LED (input) on the left/ESP side, 'R' puts it on the right/opener side.
    Returns (svg, pins) with pins A/K (LED anode/cathode) and C/E (transistor
    collector/emitter)."""
    x0, y0, w, h = cx - 66, cy - 42, 132, 84
    p = [f'<rect class="c" x="{x0}" y="{y0}" width="{w}" height="{h}" rx="4" fill="#fafafa"/>',
         f'<line x1="{cx}" y1="{y0}" x2="{cx}" y2="{y0+h}" stroke="#c53030" stroke-width="1.3" stroke-dasharray="4 3"/>']
    lx = cx - 38  # LED column
    tx = cx + 38  # transistor column
    if led == "R":
        lx, tx = tx, lx
    # LED (diode triangle + bar), vertical between top/bottom pins
    top, bot = cy - 20, cy + 20
    lpx = x0 if led == "L" else x0 + w
    p += [wire((lpx, top), (lx, top), (lx, cy - 9)),
          f'<polygon class="c" points="{lx-11},{cy-9} {lx+11},{cy-9} {lx},{cy+7}"/>',
          f'<line class="w" x1="{lx-11}" y1="{cy+7}" x2="{lx+11}" y2="{cy+7}"/>',
          wire((lx, cy + 7), (lx, bot), (lpx, bot))]
    # emission arrows toward transistor
    ax = 1 if led == "L" else -1
    p += [f'<line class="w" x1="{lx+ax*13}" y1="{cy-4}" x2="{lx+ax*24}" y2="{cy-4}"/>',
          f'<line class="w" x1="{lx+ax*13}" y1="{cy+4}" x2="{lx+ax*24}" y2="{cy+4}"/>']
    # phototransistor: circle with collector (top) / emitter (bottom)
    tpx = x0 + w if led == "L" else x0
    p += [f'<circle class="c" cx="{tx}" cy="{cy}" r="15" fill="#fff"/>',
          wire((tpx, top), (tx + (-15 if led == "L" else 15), top), (tx, cy - 14)),
          wire((tpx, bot), (tx + (-15 if led == "L" else 15), bot), (tx, cy + 14)),
          f'<line class="w" x1="{tx-6}" y1="{cy-11}" x2="{tx-6}" y2="{cy+11}"/>']
    A = (lpx, top)
    K = (lpx, bot)
    C = (tpx, top)
    E = (tpx, bot)
    return "".join(p), {"A": A, "K": K, "C": C, "E": E}


def block(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fafafa" '
            f'stroke="#999" stroke-width="1.5" stroke-dasharray="4 3"/>'
            + text(x + 10, y + 18, title, "val"))


def build(obst):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         'font-family="Helvetica,Arial,sans-serif">',
         '<style>.w{stroke:#111;stroke-width:2;fill:none}.c{stroke:#111;stroke-width:2;fill:#fff}'
         '.lbl{font-size:13px;fill:#111}.val{font-size:12px;fill:#444}'
         '.big{font-size:18px;font-weight:bold;fill:#111}</style>',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         text(24, 34, "Security+ interface: ESP32 to opener" + ("" if obst else "  (data only, no obstruction)"), "big")]

    # ESP32
    s.append('<rect x="30" y="110" width="160" height="360" rx="6" fill="#eaf2ff" stroke="#2b6cb0" stroke-width="2"/>')
    s.append(text(110, 138, "ESP32", "big", "middle"))
    s.append(text(110, 156, "secplus_gdo hub", "val", "middle"))
    stub = 240
    py = {"3V3": 160, "tx_pin": 230, "obstruction_pin": 340, "rx_pin": 424, "GND": 452}
    for name, y in py.items():
        if name == "obstruction_pin" and not obst:
            continue
        s.append(text(182, y + 4, name, "val", "end"))
        s.append(wire((190, y), (stub, y)))
        s.append(dot(stub, y))

    busx = 640

    # TX driver block
    s.append(block(270, 195, 290, 120, "TX driver (inverting)"))
    q1, q1p = nmos(420, 258, "L")
    s.append(res(stub, 230, q1p["G"][0], 230, "10k"))
    s.append(wire((q1p["G"][0], 230), q1p["G"]))
    s.append(q1)
    s.append(wire(q1p["D"], (q1p["D"][0], 225), (busx, 225)))
    s.append(gnd(*q1p["S"]))

    # RX sense block
    s.append(block(270, 365, 290, 175, "RX sense (inverting)"))
    q2, q2p = nmos(420, 460, "R")
    s.append(res(q2p["G"][0], 460, busx, 460, "10k"))
    s.append(wire(q2p["G"], (q2p["G"][0], 460)))
    s.append(q2)
    dn = q2p["D"]  # (398, 424)
    s.append(res(dn[0], dn[1], dn[0], 378, "10k"))       # pull-up
    s.append(supply(dn[0], 378, "+3.3 V"))
    s.append(wire(dn, (stub, dn[1])))                    # drain -> rx_pin
    s.append(dot(*dn))                                   # drain junction (pull-up + rx)
    s.append(dot(stub, dn[1]))
    s.append(gnd(*q2p["S"]))

    # DATA single-wire bus
    s.append(wire((busx, 225), (busx, 460)))
    s.append(dot(busx, 225))
    s.append(dot(busx, 460))
    s.append(text(632, 210, "DATA (~12 V idle)", "val", "end"))

    # Opener
    oh = 380 if obst else 200
    s.append(f'<rect x="700" y="150" width="230" height="{oh}" rx="6" fill="#fff5f5" '
             'stroke="#c53030" stroke-width="2" stroke-dasharray="7 5"/>')
    s.append(text(712, 174, "Opener wall control", "lbl"))
    # RED <- DATA
    s.append(wire((busx, 225), (700, 225)))
    s.append(terminal(700, 225, "RED (control / data)", "#e53e3e", ldy=24))
    # internal ~12V idle pull-up (kept far right to clear the opener title)
    s.append(wire((700, 225), (900, 225)))
    s.append(dot(900, 225))
    s.append(res(900, 225, 900, 175, "~12 V"))
    s.append(supply(900, 175, "+12 V"))
    # WHITE -> GND
    wy = 500 if obst else 300
    s.append(terminal(700, wy, "WHITE (ground)", "#eeeeee"))
    s.append(wire((655, wy), (700, wy)))
    s.append(gnd(655, wy))
    # BLACK obstruction
    if obst:
        s.append(res(stub, 340, 700, 340, "10k"))
        s.append(terminal(700, 340, "BLACK (obstruction)", "#333333"))

    s.append('</svg>')
    return "\n".join(s)


def build_isolated():
    """Illustrative galvanic-isolation of one opener channel with the opener-side
    MOSFET front end inlined. ESP and opener domains are bridged only by
    optocouplers (signals) — never by a shared ground. Representative, not a
    verified netlist."""
    IW, IH, bar = 1090, 650, 420
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {IW} {IH}" '
         'font-family="Helvetica,Arial,sans-serif">',
         '<style>.w{stroke:#111;stroke-width:2;fill:none}.c{stroke:#111;stroke-width:2;fill:#fff}'
         '.lbl{font-size:13px;fill:#111}.val{font-size:12px;fill:#444}'
         '.big{font-size:18px;font-weight:bold;fill:#111}</style>',
         f'<rect width="{IW}" height="{IH}" fill="#fff"/>',
         text(24, 34, "Isolated opener channel (repeat this per opener)", "big")]

    s.append(f'<line x1="{bar}" y1="95" x2="{bar}" y2="590" stroke="#c53030" stroke-width="1.5" stroke-dasharray="6 5"/>')
    s.append(text(bar, 88, "galvanic isolation", "val", "middle"))
    s.append(text(bar, 612, "ESP GND (left) and opener GND (right) are separate — no ground crosses the barrier", "val", "middle"))
    s.append(text(215, 128, "ESP domain (shared)", "val", "middle"))
    s.append(text(800, 128, "opener domain (floating, one per opener)", "val", "middle"))

    # ESP domain
    s.append('<rect x="30" y="175" width="150" height="255" rx="6" fill="#eaf2ff" stroke="#2b6cb0" stroke-width="2"/>')
    s.append(text(105, 203, "ESP32", "big", "middle"))
    stub = 200
    for name, y in {"3V3": 210, "tx_pin": 270, "rx_pin": 390, "GND": 415}.items():
        s.append(text(192, y + 4, name, "val", "end"))
        s.append(wire((180, y), (stub, y)))
        s.append(dot(stub, y))
    s.append(wire((stub, 415), (255, 415)))
    s.append(gnd(255, 415))
    s.append(text(275, 428, "ESP GND", "val"))

    # TX opto (LED on ESP side)
    u1, u1p = opto(bar, 290, "L")   # A=(354,270) K=(354,310) C=(486,270) E=(486,310)
    s.append(res(stub, 270, u1p["A"][0], 270, "10k"))
    s.append(u1)
    s.append(text(bar, 236, "opto (TX)", "val", "middle"))
    s.append(wire(u1p["K"], (u1p["K"][0], 340)))
    s.append(gnd(u1p["K"][0], 340))

    # RX opto (LED on opener side)
    u2, u2p = opto(bar, 410, "R")   # A=(486,390) K=(486,430) C=(354,390) E=(354,430)
    s.append(u2)
    s.append(text(bar, 470, "opto (RX)", "val", "middle"))
    s.append(wire(u2p["C"], (stub, 390)))
    s.append(dot(250, 390))
    s.append(res(250, 390, 250, 250, "10k"))
    s.append(wire((250, 250), (250, 210), (stub, 210)))
    s.append(wire(u2p["E"], (u2p["E"][0], 460)))
    s.append(gnd(u2p["E"][0], 460))

    # --- opener-side front end (inlined) ---
    vcc_y, busx = 172, 770
    # opener Vcc rail, sourced by a regulator that taps the RED / ~12 V line
    # (referenced to opener GND) — the only power available on the opener side.
    s.append(wire((u1p["C"][0], 270), (u1p["C"][0], vcc_y)))     # U1 collector up to rail
    s.append(wire((u1p["C"][0], vcc_y), (588, vcc_y)))           # Vcc rail -> regulator OUT
    s.append(dot(u1p["C"][0], vcc_y))
    s.append(text(u1p["C"][0] + 6, vcc_y - 7, "opener Vcc", "val"))
    # Voltage regulator (solid box = a real component): RED/~12 V in, Vcc out,
    # referenced to opener GND. This is what makes the opener-side supply.
    rx0, rw, rh = 588, 134, 58
    ry0 = vcc_y - 29
    s.append(f'<rect class="c" x="{rx0}" y="{ry0}" width="{rw}" height="{rh}"/>')
    s.append(text(rx0 + rw / 2, vcc_y - 3, "3.3 V regulator", "lbl", "middle"))
    s.append(text(rx0 + rw / 2, vcc_y + 15, "(LDO or buck)", "val", "middle"))
    s.append(text(rx0 + 6, ry0 + 14, "OUT", "val", "start"))
    s.append(text(rx0 + rw - 6, ry0 + 14, "IN", "val", "end"))
    s.append(wire((rx0 + rw, vcc_y), (busx, vcc_y), (busx, 255)))  # IN taps RED / ~12 V
    s.append(text(rx0 + rw + 24, vcc_y + 16, "from RED / ~12 V", "val", "start"))
    s.append(wire((rx0 + rw / 2, ry0 + rh), (rx0 + rw / 2, ry0 + rh + 15)))  # GND lead
    s.append(gnd(rx0 + rw / 2, ry0 + rh + 15))
    s.append(text(rx0 + rw / 2 + 12, ry0 + rh + 12, "GND", "val", "start"))

    # TX MOSFET Q1: gate <- TX opto emitter (+ pulldown); drain -> DATA; source -> GND
    q1, q1p = nmos(620, 310, "L")   # G=(584,310) D=(642,274) S=(642,346)
    s.append(q1)
    s.append(text(620, 300, "Q1", "val", "middle"))
    s.append(wire(u1p["E"], (540, 310), q1p["G"]))
    s.append(dot(540, 310))
    s.append(res(540, 310, 540, 372, "10k"))
    s.append(gnd(540, 372))
    s.append(wire(q1p["D"], (q1p["D"][0], 255), (busx, 255)))
    s.append(gnd(*q1p["S"]))

    # RX MOSFET Q2: gate <- DATA; drain -> RX opto LED cathode; LED anode <- R <- Vcc
    q2, q2p = nmos(620, 430, "R")   # G=(656,430) D=(598,394) S=(598,466)
    s.append(q2)
    s.append(text(620, 420, "Q2", "val", "middle"))
    s.append(res(q2p["G"][0], 430, busx, 430, "10k"))
    s.append(wire(q2p["D"], (q2p["D"][0], 430), u2p["K"]))       # drain -> LED cathode
    s.append(res(u2p["A"][0], 390, 560, 390, "10k"))            # LED anode <- R <- Vcc
    s.append(wire((560, 390), (560, vcc_y)))
    s.append(dot(560, vcc_y))
    s.append(gnd(*q2p["S"]))

    # DATA bus -> RED, with opener internal ~12 V idle pull-up
    s.append(wire((busx, 255), (busx, 430)))
    s.append(dot(busx, 255))
    s.append(dot(busx, 430))
    s.append(text(busx - 6, 300, "DATA (~12 V idle)", "val", "end"))

    # Opener box
    s.append('<rect x="820" y="220" width="200" height="300" rx="6" fill="#fff5f5" '
             'stroke="#c53030" stroke-width="2" stroke-dasharray="7 5"/>')
    s.append(text(832, 244, "Opener", "lbl"))
    s.append(wire((busx, 255), (820, 255)))
    s.append(terminal(820, 255, "RED (data)", "#e53e3e", ldy=20))
    s.append(wire((820, 255), (935, 255)))
    s.append(dot(935, 255))
    s.append(res(935, 255, 935, 210, "~12 V"))
    s.append(supply(935, 210, "+12 V (internal)"))
    s.append(terminal(820, 470, "WHITE (gnd)", "#eeeeee", ldy=-12))
    s.append(wire((820, 470), (795, 470)))
    s.append(gnd(795, 470))
    s.append(text(700, 500, "opener GND (every ground right of the barrier)", "val"))
    s.append('</svg>')
    return "\n".join(s)


outdir = os.path.dirname(os.path.abspath(__file__))
jobs = [("schematic.svg", lambda: build(True)),
        ("schematic-no-obstruction.svg", lambda: build(False)),
        ("schematic-isolated.svg", build_isolated)]
for name, fn in jobs:
    with open(os.path.join(outdir, name), "w") as f:
        f.write(fn())
    print("wrote", name)
