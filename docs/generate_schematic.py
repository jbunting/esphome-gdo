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


outdir = os.path.dirname(os.path.abspath(__file__))
for name, o in [("schematic.svg", True), ("schematic-no-obstruction.svg", False)]:
    with open(os.path.join(outdir, name), "w") as f:
        f.write(build(o))
    print("wrote", name)
