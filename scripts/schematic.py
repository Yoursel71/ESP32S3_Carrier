"""Generates the .kicad_sch from design.py. Every pin end gets a net label, a power symbol or a no-connect flag."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import math
import uuid
import copy
from sexpr import parse, dumps, find, findall, Sym, QStr
import library as L
import design as D

PROJ = L.PROJ
SCH = os.path.join(PROJ, D.PROJECT + ".kicad_sch")
UUIDS = os.path.join(PROJ, "scripts", "uuid_table.json")
POWER_NETS = {"GND": "power:GND", "+5V": "power:+5V", "+5V_MOD": "Carrier:+5V_MOD", "+3V3_MOD": "Carrier:+3V3_MOD"}


def U():
    return QStr(str(uuid.uuid4()))


_libcache = {}


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    if lib == "Carrier":
        if "Carrier" not in _libcache:
            t = parse(open(L.SYMLIB, encoding="utf8").read())
            _libcache["Carrier"] = {str(s[1]): s for s in findall(t, "symbol")}
        s = copy.deepcopy(_libcache["Carrier"][name])
    else:
        s = L.flatten(lib, name)
    s[1] = QStr(lib_id)
    return s


def sym_pins(sym):
    pins = []

    def walk(n):
        for x in n:
            if isinstance(x, list):
                if x and x[0] == "pin":
                    at = find(x, "at")
                    pins.append((str(find(x, "number")[1]), float(at[1]), float(at[2]), int(float(at[3]))))
                else:
                    walk(x)
    walk(sym)
    return pins


def outward(rot):
    # pin orientation -> direction the pin end points away from the body (schematic coords, y down)
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[rot]


def eff(size=1.27, hide=False, justify=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


class Schematic:
    def __init__(self):
        self.root = str(uuid.uuid4())
        self.items = []
        self.libs = {}
        self.pwr_n = 0
        self.flg_n = 0

    def use(self, lib_id):
        if lib_id not in self.libs:
            self.libs[lib_id] = lib_symbol(lib_id)
        return self.libs[lib_id]

    def place(self, lib_id, ref, value, x, y, rot=0, footprint="", hide_ref=False, sym_uuid=None):
        s = self.use(lib_id)
        su = sym_uuid or str(uuid.uuid4())
        in_bom = find(s, "in_bom")
        on_board = find(s, "on_board")
        inst = [Sym("symbol"), [Sym("lib_id"), QStr(lib_id)], [Sym("at"), x, y, rot], [Sym("unit"), 1],
                [Sym("exclude_from_sim"), Sym("no")],
                [Sym("in_bom"), Sym("no") if ref.startswith("#") else (in_bom[1] if in_bom else Sym("yes"))],
                [Sym("on_board"), Sym("no") if ref.startswith("#") else (on_board[1] if on_board else Sym("yes"))],
                [Sym("dnp"), Sym("no")], [Sym("uuid"), QStr(su)]]
        for p in findall(s, "property"):
            name = str(p[1])
            if name.startswith("ki_"):
                continue
            at = find(p, "at")
            px, py = float(at[1]), float(at[2])
            pa = float(at[3]) if len(at) > 3 else 0
            r = math.radians(rot)
            qx = px * math.cos(r) - py * math.sin(r)
            qy = px * math.sin(r) + py * math.cos(r)
            val = {"Reference": ref, "Value": value, "Footprint": footprint}.get(name, str(p[2]))
            e = copy.deepcopy(find(p, "effects"))
            if name == "Reference" and hide_ref and find(e, "hide") is None:
                e.append([Sym("hide"), Sym("yes")])
            inst.append([Sym("property"), QStr(name), QStr(val), [Sym("at"), x + qx, y - qy, pa], e])
        for num, *_ in sym_pins(s):
            inst.append([Sym("pin"), QStr(num), [Sym("uuid"), U()]])
        inst.append([Sym("instances"), [Sym("project"), QStr(D.PROJECT),
                                        [Sym("path"), QStr("/" + self.root), [Sym("reference"), QStr(ref)], [Sym("unit"), 1]]]])
        self.items.append(inst)
        return su

    def pin_points(self, lib_id, x, y):
        out = {}
        for num, px, py, prot in sym_pins(self.use(lib_id)):
            out.setdefault(num, (x + px, y - py, prot))
        return out

    def label(self, net, x, y, rot):
        d = outward(rot)
        ang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[d]
        just = "right bottom" if ang in (180, 270) else "left bottom"
        self.items.append([Sym("label"), QStr(net), [Sym("at"), x, y, ang], eff(1.27, justify=just), [Sym("uuid"), U()]])

    def power(self, net, x, y, rot):
        d = outward(rot)
        if net == "GND":
            prot = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}[d]
        else:
            prot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        self.pwr_n += 1
        self.place(POWER_NETS[net], "#PWR%03d" % self.pwr_n, net, x, y, prot, hide_ref=True)

    def noconnect(self, x, y):
        self.items.append([Sym("no_connect"), [Sym("at"), x, y], [Sym("uuid"), U()]])

    def flag(self, net, x, y):
        self.pwr_n += 1
        self.place(POWER_NETS[net], "#PWR%03d" % self.pwr_n, net, x, y, 0, hide_ref=True)
        self.flg_n += 1
        self.place("power:PWR_FLAG", "#FLG%02d" % self.flg_n, "PWR_FLAG", x, y, 180 if net == "GND" else 0, hide_ref=True)

    def text(self, txt, x, y, size=1.5):
        self.items.append([Sym("text"), QStr(txt), [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
                           eff(size, justify="left top"), [Sym("uuid"), U()]])

    def write(self, path):
        tb = [Sym("title_block"), [Sym("title"), QStr("ESP32-S3 Carrier Board")], [Sym("date"), QStr(D.DATE)],
              [Sym("rev"), QStr(D.REV)], [Sym("company"), QStr("github.com/Yoursel71")],
              [Sym("comment"), 1, QStr("ESP32-S3-DevKitC-1 N16R8 + CC1101 + 2x NRF24 + PN532 + RDM6300 + Si5351 + microSD + OLED")]]
        doc = [Sym("kicad_sch"), [Sym("version"), 20250114], [Sym("generator"), QStr("eeschema")],
               [Sym("generator_version"), QStr("9.0")], [Sym("uuid"), QStr(self.root)], [Sym("paper"), QStr("A2")], tb,
               [Sym("lib_symbols")] + list(self.libs.values())]
        doc += self.items
        doc += [[Sym("sheet_instances"), [Sym("path"), QStr("/"), [Sym("page"), QStr("1")]]], [Sym("embedded_fonts"), Sym("no")]]
        with open(path, "w", encoding="utf8") as f:
            f.write(dumps(doc) + "\n")


NOTES = """NOTES
1) Every module plugs into 2.54 mm female header sockets. Pin names are printed next to each socket on the silkscreen.
2) Power: DevKit 5V pin -> +5V. SW7 (slide) drives Q3 (P-MOSFET) with a soft-start (R16 100k + C16 100nF, ~20 ms ramp): +5V -> +5V_MOD.
   +5V_MOD -> microSD, RDM6300, IR LEDs, buzzer and U2 (AMS1117-3.3) -> +3V3_MOD (all 3.3 V modules).
   SW7 OFF: the ESP32 keeps running, every module is unpowered. The ESP32's own 3V3 pin is not used (no overload / brown-out).
3) Shared SPI: MOSI=IO11 SCK=IO12 MISO=IO13. CS: CC1101=IO10, SD=IO14, NRF1 CSN=IO5, NRF2 CSN=IO7 (10k pull-ups R12-R15).
   CE: NRF1=IO4, NRF2=IO6. CC1101 GDO0=IO9, GDO2=IO42. NRF IRQ: NRF1=IO21, NRF2=IO48 (optional, can be ignored by firmware).
4) Shared I2C: SDA=IO8 SCL=IO18, 4.7k pull-ups to +3V3_MOD (R1, R2). Devices: OLED SH1106 (0x3C), PN532 (0x24), Si5351 (0x60).
   PN532 V3 DIP switch: SW1=ON SW2=OFF for I2C.
5) RDM6300 TX is 5 V logic -> R8/R9 divider (~3.4 V) -> IO17. The 125 kHz coil plugs into J8.
6) IR receiver VS1838B on IO1 (R11/C11 supply filter, lens faces the top edge). IR transmitter on IO2: Q1 + 220R base,
   three IR LEDs, each with its own 47R resistor (~67 mA each), C15 local reservoir. Drive IO2 only with the 38 kHz carrier,
   never hold it high. Buzzer on IO47 (Q2 + 1N4148).
7) Buttons pull to GND (enable internal pull-ups): UP=IO15 DOWN=IO16 LEFT=IO38 RIGHT=IO39 OK=IO40 BACK=IO41.
   Note: on DevKitC-1 v1.1 IO38 also drives the on-board RGB LED.
8) JP1: normally-closed solder bridge. Old Catalex modules never release MISO; if SPI devices clash, cut JP1 and tie the
   module's 74LVC125 MISO OE pin to CS (or add a tri-state buffer here).
9) Unused GPIO: 0, 3, 19, 20, 35-37, 45, 46, TX/RX, RST."""


def build():
    S = Schematic()
    old = {}
    if os.path.exists(UUIDS):
        old = json.load(open(UUIDS, encoding="utf8"))
        S.root = old.get("__root__", S.root)
    table = {"__root__": S.root}
    for c in D.COMPONENTS:
        x, y = c["sch"]
        su = S.place(c["sym"], c["ref"], c["val"], x, y, 0, footprint=c["fp"], sym_uuid=old.get(c["ref"]))
        table[c["ref"]] = su
        for num, (px, py, prot) in S.pin_points(c["sym"], x, y).items():
            net = c["pins"].get(num)
            if net is None:
                S.noconnect(px, py)
            elif net in POWER_NETS:
                S.power(net, px, py, prot)
            else:
                S.label(net, px, py, prot)
    fx, fy = 480.06, 290.83
    for i, net in enumerate(D.PWR_FLAG_NETS):
        S.flag(net, fx + i * 15.24, fy)
    S.text("ESP32-S3 CARRIER BOARD  -  rev %s  -  %s" % (D.REV, D.DATE), 20.32, 15.24, 3.0)
    S.text(NOTES, 20.32, 320.04, 1.5)
    S.text("POWER: PWR_FLAGs for ERC", 474.98, 279.4, 1.27)
    S.write(SCH)
    json.dump(table, open(UUIDS, "w", encoding="utf8"), indent=1)
    return table


if __name__ == "__main__":
    build()
    print("schematic done:", SCH)
