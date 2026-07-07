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
    """Illustrative galvanic-isolation of one opener channel: the ESP domain and
    the opener domain are bridged only by optocouplers (signals) — never by a
    shared ground. Representative, not a verified netlist."""
    IW, IH, bar = 1020, 560, 470
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {IW} {IH}" '
         'font-family="Helvetica,Arial,sans-serif">',
         '<style>.w{stroke:#111;stroke-width:2;fill:none}.c{stroke:#111;stroke-width:2;fill:#fff}'
         '.lbl{font-size:13px;fill:#111}.val{font-size:12px;fill:#444}'
         '.big{font-size:18px;font-weight:bold;fill:#111}</style>',
         f'<rect width="{IW}" height="{IH}" fill="#fff"/>',
         text(24, 34, "Isolated opener channel (repeat this per opener)", "big")]

    # isolation barrier (behind everything)
    s.append(f'<line x1="{bar}" y1="95" x2="{bar}" y2="500" stroke="#c53030" stroke-width="1.5" stroke-dasharray="6 5"/>')
    s.append(text(bar, 88, "galvanic isolation", "val", "middle"))
    s.append(text(bar, 522, "ESP GND and opener GND are NOT connected", "val", "middle"))
    s.append(text(250, 118, "ESP domain (shared)", "val", "middle"))
    s.append(text(700, 118, "opener domain (floating, one per opener)", "val", "middle"))

    # ESP domain
    s.append('<rect x="30" y="140" width="150" height="255" rx="6" fill="#eaf2ff" stroke="#2b6cb0" stroke-width="2"/>')
    s.append(text(105, 168, "ESP32", "big", "middle"))
    stub = 230
    for name, y in {"3V3": 175, "tx_pin": 235, "rx_pin": 320, "GND": 375}.items():
        s.append(text(172, y + 4, name, "val", "end"))
        s.append(wire((180, y), (stub, y)))
        s.append(dot(stub, y))
    s.append(wire((stub, 375), (285, 375)))
    s.append(gnd(285, 375))
    s.append(text(305, 388, "ESP GND", "val"))

    # TX opto: LED on ESP side, aligned so anode == tx_pin height
    u1, u1p = opto(bar, 255, "L")            # A=(404,235) K=(404,275) C=(536,235) E=(536,275)
    s.append(res(stub, 235, u1p["A"][0], 235, "10k"))
    s.append(u1)
    s.append(text(bar, 200, "opto (TX)", "val", "middle"))
    s.append(wire(u1p["K"], (u1p["K"][0], 300)))
    s.append(gnd(u1p["K"][0], 300))

    # RX opto: transistor on ESP side, collector == rx_pin height
    u2, u2p = opto(bar, 340, "R")            # A=(536,320) K=(536,360) C=(404,320) E=(404,360)
    s.append(u2)
    s.append(text(bar, 405, "opto (RX)", "val", "middle"))
    s.append(wire(u2p["C"], (stub, 320)))    # collector -> rx_pin
    s.append(dot(270, 320))
    s.append(res(270, 320, 270, 215, "10k")) # pull-up to 3V3 (own lane; crosses TX wire, no dot)
    s.append(wire((270, 215), (270, 175), (stub, 175)))
    s.append(wire(u2p["E"], (u2p["E"][0], 385)))
    s.append(gnd(u2p["E"][0], 385))

    # Opener-side interface block
    bx, by, bw, bh = 590, 185, 195, 245
    s.append(block(bx, by, bw, bh, "Opener-side interface"))
    for i, t in enumerate(["MOSFET TX / RX", "front end,", "12 V -> Vcc", "(see schematic above)"]):
        s.append(text(bx + bw / 2, by + 110 + i * 18, t, "val", "middle"))
    s.append(wire(u1p["E"], (bx, u1p["E"][1])))          # TX in
    s.append(text(bx + 6, u1p["E"][1] + 4, "TX", "val"))
    s.append(res(bx, u2p["A"][1], u2p["A"][0], u2p["A"][1], "10k"))  # RX out -> opto LED
    s.append(text(bx + 6, u2p["A"][1] + 4, "RX", "val"))
    # opener Vcc rail (from 12 V, inside opener domain)
    s.append(wire((bx + 95, by), (bx + 95, 150), (u1p["C"][0], 150), u1p["C"]))
    s.append(dot(bx + 95, 150))
    s.append(text(bx + 105, 146, "opener Vcc (from 12 V)", "val"))

    # Opener box (drawn before the wires/grounds/terminals that sit on it)
    s.append('<rect x="820" y="195" width="180" height="230" rx="6" fill="#fff5f5" '
             'stroke="#c53030" stroke-width="2" stroke-dasharray="7 5"/>')
    s.append(text(832, 219, "Opener", "lbl"))

    # DATA -> RED, GND -> WHITE
    s.append(wire((bx + bw, 235), (820, 235)))
    s.append(wire((bx + bw, 380), (820, 380)))
    # opener-side grounds (common opener GND; not tied to ESP GND)
    s.append(wire((820, 380), (820, 410)))
    s.append(gnd(820, 410))
    s.append(text(840, 423, "opener GND", "val"))
    s.append(wire(u2p["K"], (u2p["K"][0], 430)))
    s.append(gnd(u2p["K"][0], 430))

    s.append(terminal(820, 235, "RED (data)", "#e53e3e", ldy=20))
    s.append(terminal(820, 380, "WHITE (gnd)", "#eeeeee", ldy=-12))
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
