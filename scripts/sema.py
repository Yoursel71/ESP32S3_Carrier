"""Tasarim verisinden .kicad_sch uretir. Her pinin ucuna etiket / guc sembolu / NC bayragi konur."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import uuid
import copy
from sexpr import parse, dumps, find, findall, Sym, QStr
import kutuphane as K
import tasarim as T

PROJ = K.PROJ
SCH = os.path.join(PROJ, T.PROJE + ".kicad_sch")
UUIDS = os.path.join(PROJ, "scripts", "uuid_tablosu.json")
POWER_NETS = {"GND": "power:GND", "+5V": "power:+5V", "+5V_MOD": "Tasiyici:+5V_MOD", "+3V3_MOD": "Tasiyici:+3V3_MOD"}


def U():
    return QStr(str(uuid.uuid4()))


def g(v):
    return round(v / 1.27) * 1.27


_libcache = {}


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    if lib == "Tasiyici":
        if "Tasiyici" not in _libcache:
            t = parse(open(K.SYMLIB, encoding="utf8").read())
            _libcache["Tasiyici"] = {str(s[1]): s for s in findall(t, "symbol")}
        s = copy.deepcopy(_libcache["Tasiyici"][name])
    else:
        s = K.flatten(lib, name)
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
    # pin yonu -> pinin disari baktigi yon (sema koordinatinda, y asagi)
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[rot]


def eff(size=1.27, hide=False, justify=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


class Sema:
    def __init__(self):
        self.root = str(uuid.uuid4())
        self.items = []
        self.libs = {}
        self.pwr_n = 0
        self.flg_n = 0
        self.sym_uuid = {}

    def use(self, lib_id):
        if lib_id not in self.libs:
            self.libs[lib_id] = lib_symbol(lib_id)
        return self.libs[lib_id]

    def place(self, lib_id, ref, value, x, y, rot=0, footprint="", hide_ref=False, hide_val=False, sym_uuid=None):
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
            px, py, pa = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0
            # sembol donusu (yalniz 0/90/180/270)
            import math
            r = math.radians(rot)
            qx = px * math.cos(r) - py * math.sin(r)
            qy = px * math.sin(r) + py * math.cos(r)
            val = {"Reference": ref, "Value": value, "Footprint": footprint}.get(name, str(p[2]))
            e = copy.deepcopy(find(p, "effects"))
            hidden = find(e, "hide") is not None
            if name == "Reference" and hide_ref and not hidden:
                e.append([Sym("hide"), Sym("yes")])
            if name == "Value" and hide_val and not hidden:
                e.append([Sym("hide"), Sym("yes")])
            inst.append([Sym("property"), QStr(name), QStr(val), [Sym("at"), x + qx, y - qy, pa], e])
        for num, *_ in sym_pins(s):
            inst.append([Sym("pin"), QStr(num), [Sym("uuid"), U()]])
        inst.append([Sym("instances"), [Sym("project"), QStr(T.PROJE),
                                        [Sym("path"), QStr("/" + self.root), [Sym("reference"), QStr(ref)], [Sym("unit"), 1]]]])
        self.items.append(inst)
        return su

    def pin_points(self, lib_id, x, y):
        s = self.use(lib_id)
        out = {}
        for num, px, py, prot in sym_pins(s):
            out.setdefault(num, (x + px, y - py, prot))
        return out

    def label(self, net, x, y, rot):
        d = outward(rot)
        ang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[d]
        just = "right bottom" if ang in (180, 270) else "left bottom"
        self.items.append([Sym("label"), QStr(net), [Sym("at"), x, y, ang], eff(1.27, justify=just), [Sym("uuid"), U()]])

    def power(self, net, x, y, rot):
        d = outward(rot)
        lib_id = POWER_NETS[net]
        if net == "GND":
            prot = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}[d]
        else:
            prot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        self.pwr_n += 1
        self.place(lib_id, "#PWR%03d" % self.pwr_n, net, x, y, prot, hide_ref=True)

    def noconnect(self, x, y):
        self.items.append([Sym("no_connect"), [Sym("at"), x, y], [Sym("uuid"), U()]])

    def flag(self, net, x, y):
        lib_id = POWER_NETS[net]
        self.pwr_n += 1
        self.place(lib_id, "#PWR%03d" % self.pwr_n, net, x, y, 0 if net != "GND" else 0, hide_ref=True)
        self.flg_n += 1
        self.place("power:PWR_FLAG", "#FLG%02d" % self.flg_n, "PWR_FLAG", x, y, 0 if net != "GND" else 180, hide_ref=True)

    def text(self, txt, x, y, size=1.5):
        self.items.append([Sym("text"), QStr(txt), [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
                           eff(size, justify="left top"), [Sym("uuid"), U()]])

    def write(self, path):
        tb = [Sym("title_block"), [Sym("title"), QStr("ESP32-S3 Tasiyici Kart")], [Sym("date"), QStr(T.TARIH)],
              [Sym("rev"), QStr(T.REV)], [Sym("company"), QStr("github.com/Yoursel71")],
              [Sym("comment"), 1, QStr("ESP32-S3-DevKitC-1 N16R8 + CC1101 + 2x NRF24 + PN532 + RDM6300 + microSD + OLED")]]
        libs = [Sym("lib_symbols")] + list(self.libs.values())
        doc = [Sym("kicad_sch"), [Sym("version"), 20250114], [Sym("generator"), QStr("eeschema")],
               [Sym("generator_version"), QStr("9.0")], [Sym("uuid"), QStr(self.root)], [Sym("paper"), QStr("A2")], tb, libs]
        doc += self.items
        doc += [[Sym("sheet_instances"), [Sym("path"), QStr("/"), [Sym("page"), QStr("1")]]], [Sym("embedded_fonts"), Sym("no")]]
        with open(path, "w", encoding="utf8") as f:
            f.write(dumps(doc) + "\n")


NOTLAR = """NOTLAR
1) Tum moduller disi header (2.54 mm) soketlere takilir. Pin isimleri karttaki serigrafide yazilidir.
2) Guc: ESP32 kartinin 5V pini -> +5V. SW7 (surgulu) Q3 P-MOSFET'i acar: +5V -> +5V_MOD.
   +5V_MOD -> microSD, RDM6300, IR LED, buzzer ve U2 (AMS1117-3.3) -> +3V3_MOD (tum 3.3V moduller).
   Anahtar KAPALI: ESP32 calisir, tum moduller kapali. ESP32'nin kendi 3V3 pini kullanilmaz (asiri yuk/brownout olmasin).
3) SPI ortak: MOSI=IO11 SCK=IO12 MISO=IO13. CS: CC1101=IO10, SD=IO14, NRF1 CSN=IO5, NRF2 CSN=IO7. CE: NRF1=IO4, NRF2=IO6. GDO0=IO9.
4) I2C: SDA=IO8 SCL=IO18, 4.7k pull-up +3V3_MOD'a (R1,R2). PN532 V3: SW1=ON SW2=OFF (I2C).
5) RDM6300 TX 5V seviyesinde -> R8/R9 boluculu (~3.4V) -> IO17 (pin haritasinda bostu, eklendi). Bobin J8'e takilir.
6) IR alici IO1, IR LED IO2 (Q1 + 220R baz, 47R LED akim siniri, ~70mA). Buzzer IO47 (Q2 surucu + 1N4148).
7) Butonlar GND'ye ceker (ic pull-up kullanin): UP=IO15 DOWN=IO16 LEFT=IO38 RIGHT=IO39 OK=IO40 BACK=IO41.
   Not: DevKitC-1 v1.1'de IO38 kartin RGB LED'ine de bagli.
8) JP1: normalde kapali lehim koprusu. Eski Catalex modulleri MISO'yu birakmaz; SPI cakisirsa JP1'i kesip moduldeki
   74LVC125'in MISO OE ucunu CS'ye baglayin (ya da bu hatta tampon ekleyin).
9) Kullanilmayan GPIO: 0, 3, 19, 20, 21, 35-37, 42, 45, 46, 48, TX/RX, RST. CC1101 GDO2 ve NRF IRQ bagli degil."""


def build():
    S = Sema()
    old = {}
    if os.path.exists(UUIDS):
        old = json.load(open(UUIDS, encoding="utf8"))
        S.root = old.get("__root__", S.root)
    table = {"__root__": S.root}
    for c in T.BILESENLER:
        x, y = c["sch"]
        su = old.get(c["ref"])
        su = S.place(c["sym"], c["ref"], c["val"], x, y, 0, footprint=c["fp"], sym_uuid=su)
        table[c["ref"]] = su
        pts = S.pin_points(c["sym"], x, y)
        for num, (px, py, prot) in pts.items():
            net = c["pins"].get(num)
            if net is None:
                S.noconnect(px, py)
            elif net in POWER_NETS:
                S.power(net, px, py, prot)
            else:
                S.label(net, px, py, prot)
    # PWR_FLAG'ler
    fx, fy = 480.06, 290.83
    for i, net in enumerate(T.PWR_FLAG_NETLER):
        S.flag(net, fx + i * 15.24, fy)
    S.text("ESP32-S3 TASIYICI KART  -  rev %s  -  %s" % (T.REV, T.TARIH), 20.32, 15.24, 3.0)
    S.text(NOTLAR, 20.32, 330.2, 1.5)
    S.text("GUC: ERC icin PWR_FLAG", 474.98, 279.4, 1.27)
    S.write(SCH)
    json.dump(table, open(UUIDS, "w", encoding="utf8"), indent=1)
    return table


if __name__ == "__main__":
    build()
    print("sema tamam:", SCH)
