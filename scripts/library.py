"""Project library generator: Carrier.kicad_sym and Carrier.pretty/."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uuid
import copy
from sexpr import parse, dumps, find, findall, Sym, QStr

KICAD_SYM = r"D:\KiCad\share\kicad\symbols"
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMLIB = os.path.join(PROJ, "Carrier.kicad_sym")
FPLIB = os.path.join(PROJ, "Carrier.pretty")
M3D = "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/"


def U():
    return QStr(str(uuid.uuid4()))


def eff(size=1.27, hide=False, justify=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


def prop(name, value, x=0.0, y=0.0, hide=False, size=1.27, justify=None):
    return [Sym("property"), QStr(name), QStr(value), [Sym("at"), x, y, 0], eff(size, hide, justify)]


# ------------------------------------------------------------------ symbols
def box_symbol(name, ref, value, footprint, desc, left, right=(), half_w=7.62, pin_len=2.54):
    """left/right: [(number, name, type)]; pins top to bottom on a 2.54 mm pitch."""
    n = max(len(left), len(right))
    top = round(((n - 1) * 2.54 / 2.0) / 1.27) * 1.27
    h_top = top + 2.54
    h_bot = top - (n - 1) * 2.54 - 2.54
    s = [Sym("symbol"), QStr(name),
         [Sym("pin_names"), [Sym("offset"), 1.016]],
         [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
         prop("Reference", ref, -half_w, h_top + 1.27, justify="left"),
         prop("Value", value, -half_w, h_bot - 1.27, justify="left"),
         prop("Footprint", footprint, 0, 0, hide=True),
         prop("Datasheet", "", 0, 0, hide=True),
         prop("Description", desc, 0, 0, hide=True)]
    body = [Sym("symbol"), QStr(name + "_0_1"),
            [Sym("rectangle"), [Sym("start"), -half_w, h_top], [Sym("end"), half_w, h_bot],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]]]
    pins = [Sym("symbol"), QStr(name + "_1_1")]
    for side, lst in (("L", left), ("R", right)):
        for i, (num, pname, ptype) in enumerate(lst):
            y = top - i * 2.54
            at = [Sym("at"), -(half_w + pin_len), y, 0] if side == "L" else [Sym("at"), half_w + pin_len, y, 180]
            pins.append([Sym("pin"), Sym(ptype), Sym("line"), at, [Sym("length"), pin_len],
                         [Sym("name"), QStr(pname), eff()], [Sym("number"), QStr(num), eff()]])
    s += [body, pins, [Sym("embedded_fonts"), Sym("no")]]
    return s


def load_lib(lib):
    tree = parse(open(os.path.join(KICAD_SYM, lib + ".kicad_sym"), encoding="utf8").read())
    return {str(s[1]): s for s in findall(tree, "symbol")}


def rename_units(sym, old, new):
    for x in sym:
        if isinstance(x, list) and x and x[0] == "symbol" and isinstance(x[1], str) and x[1].startswith(old + "_"):
            x[1] = QStr(new + x[1][len(old):])


def flatten(lib, name, newname=None):
    """Resolve an (extends ...) chain into a single stand-alone symbol."""
    syms = load_lib(lib)
    child = copy.deepcopy(syms[name])
    ext = find(child, "extends")
    if not ext:
        out = child
    else:
        parent = flatten(lib, str(ext[1]))
        pname = str(parent[1])
        out = [Sym("symbol"), QStr(name)]
        child_props = {str(p[1]): p for p in findall(child, "property")}
        for x in parent[2:]:
            if isinstance(x, list) and x and x[0] == "property":
                pn = str(x[1])
                out.append(child_props.pop(pn) if pn in child_props else x)
            elif isinstance(x, list) and x and x[0] == "embedded_fonts":
                continue
            else:
                out.append(copy.deepcopy(x))
        for p in child_props.values():
            out.append(p)
        rename_units(out, pname, name)
        out.append([Sym("embedded_fonts"), Sym("no")])
    if newname:
        rename_units(out, name, newname)
        out[1] = QStr(newname)
    return out


def power_symbol(newname):
    s = copy.deepcopy(load_lib("power")["+5V"])
    rename_units(s, "+5V", newname)
    s[1] = QStr(newname)
    for p in findall(s, "property"):
        if p[1] == "Value":
            p[2] = QStr(newname)
        if p[1] == "Description":
            p[2] = QStr('Power symbol creates a global net "%s"' % newname)
    return s


def devkit_symbol():
    from design import DEVKIT_J1, DEVKIT_J3
    left = [(str(i + 1), n, "passive") for i, n in enumerate(DEVKIT_J1)]
    right = [(str(i + 23), n, "passive") for i, n in enumerate(DEVKIT_J3)]
    return box_symbol("ESP32-S3-DevKitC-1", "U", "ESP32-S3-DevKitC-1", "Carrier:ESP32-S3-DevKitC-1_Socket",
                      "ESP32-S3-DevKitC-1 dev board on 2x 1x22 female headers (J1 left, J3 right)",
                      left, right, half_w=12.7)


def P(*names):
    return [(str(i + 1), n, "passive") for i, n in enumerate(names)]


def write_symlib():
    syms = [
        devkit_symbol(),
        box_symbol("CC1101_SMA_2x4", "J", "CC1101", "Carrier:CC1101_SMA_2x4_Socket", "CC1101 433MHz module with SMA, 2x4 header",
                   P("GND", "VCC", "GDO0", "CSN", "SCK", "MOSI", "MISO", "GDO2")),
        box_symbol("NRF24L01_PA_LNA", "J", "NRF24L01+PA+LNA", "Carrier:NRF24L01_PA_LNA_Socket",
                   "nRF24L01+PA+LNA module with SMA, 2x4 header", P("GND", "VCC", "CE", "CSN", "SCK", "MOSI", "MISO", "IRQ")),
        box_symbol("PN532_I2C", "J", "PN532", "Carrier:PN532_V3_I2C_Socket", "PN532 NFC V3, I2C header", P("GND", "VCC", "SDA", "SCL")),
        box_symbol("OLED_SH1106_I2C", "J", "OLED 1.3in", "Carrier:OLED_1.3in_I2C_Socket", "1.3in SH1106 I2C OLED",
                   P("GND", "VCC", "SCL", "SDA")),
        box_symbol("microSD_Catalex", "J", "microSD", "Carrier:microSD_Catalex_Socket", "Catalex microSD module (5V)",
                   P("GND", "VCC", "MISO", "MOSI", "SCK", "CS")),
        box_symbol("RDM6300", "J", "RDM6300", "Carrier:RDM6300_Socket", "RDM6300 125kHz, P1 (1-5) + P2 antenna (6-7)",
                   P("TX", "RX", "NC", "GND", "+5V", "ANT1", "ANT2")),
        box_symbol("Si5351_I2C", "J", "Si5351", "Carrier:Si5351_3SMA_Socket", "Si5351 clock generator module, 3x SMA, 4-pin I2C",
                   P("VCC", "GND", "SCL", "SDA")),
        box_symbol("VS1838B", "U", "VS1838B", "OptoDevice:Vishay_MINICAST-3Pin", "38kHz IR receiver (OUT, GND, VCC)",
                   P("OUT", "GND", "VCC"), half_w=5.08),
        flatten("Transistor_BJT", "PN2222A"),
        flatten("Regulator_Linear", "AMS1117-3.3"),
        flatten("Transistor_FET", "AO3401A"),
        power_symbol("+5V_MOD"),
        power_symbol("+3V3_MOD"),
    ]
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20241209], [Sym("generator"), QStr("carrier_generator")],
           [Sym("generator_version"), QStr("1.1")]] + syms
    with open(SYMLIB, "w", encoding="utf8") as f:
        f.write(dumps(lib) + "\n")


# ------------------------------------------------------------------ footprints
def stroke(w, t="solid"):
    return [Sym("stroke"), [Sym("width"), w], [Sym("type"), Sym(t)]]


def fp_line(x1, y1, x2, y2, layer, w=0.12, t="solid"):
    return [Sym("fp_line"), [Sym("start"), x1, y1], [Sym("end"), x2, y2], stroke(w, t), [Sym("layer"), QStr(layer)], [Sym("uuid"), U()]]


def fp_rect(x1, y1, x2, y2, layer, w=0.1, t="solid"):
    return [Sym("fp_rect"), [Sym("start"), x1, y1], [Sym("end"), x2, y2], stroke(w, t),
            [Sym("fill"), Sym("no")], [Sym("layer"), QStr(layer)], [Sym("uuid"), U()]]


def fp_circle(cx, cy, r, layer, w=0.1):
    return [Sym("fp_circle"), [Sym("center"), cx, cy], [Sym("end"), cx + r, cy], stroke(w),
            [Sym("fill"), Sym("no")], [Sym("layer"), QStr(layer)], [Sym("uuid"), U()]]


def fp_text(txt, x, y, layer="F.SilkS", size=0.8, angle=0, justify=None, thick=None, width=None):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, width or size], [Sym("thickness"), thick or round(max(size * 0.15, 0.12), 3)]]]
    if justify:
        e.append([Sym("justify"), Sym(justify)])
    return [Sym("fp_text"), Sym("user"), QStr(txt), [Sym("at"), x, y, angle], [Sym("layer"), QStr(layer)], [Sym("uuid"), U()], e]


def fprop(name, value, x, y, layer, hide=False, size=1.0):
    p = [Sym("property"), QStr(name), QStr(value), [Sym("at"), x, y, 0], [Sym("layer"), QStr(layer)]]
    if hide:
        p.append([Sym("hide"), Sym("yes")])
    p += [[Sym("uuid"), U()], [Sym("effects"), [Sym("font"), [Sym("size"), size, size], [Sym("thickness"), round(size * 0.15, 3)]]]]
    return p


def tht_pad(num, x, y, rect=False, size=1.7, drill=1.0):
    return [Sym("pad"), QStr(num), Sym("thru_hole"), Sym("rect" if rect else "circle"), [Sym("at"), x, y],
            [Sym("size"), size, size], [Sym("drill"), drill], [Sym("layers"), QStr("*.Cu"), QStr("*.Mask")],
            [Sym("remove_unused_layers"), Sym("no")], [Sym("uuid"), U()]]


def npth(x, y, d):
    return [Sym("pad"), QStr(""), Sym("np_thru_hole"), Sym("circle"), [Sym("at"), x, y], [Sym("size"), d, d],
            [Sym("drill"), d], [Sym("layers"), QStr("*.Cu"), QStr("*.Mask")], [Sym("uuid"), U()]]


def model(name, x=0.0, y=0.0, rot=0.0):
    # KiCad 3D offsets are in model space (Y up); Z rotation turns clockwise on screen
    return [Sym("model"), QStr(M3D + name + ".step"),
            [Sym("offset"), [Sym("xyz"), x, -y, 0]], [Sym("scale"), [Sym("xyz"), 1, 1, 1]],
            [Sym("rotate"), [Sym("xyz"), 0, 0, rot]]]


def silk_box(x1, y1, x2, y2, sides="LRTB", t="dash", w=0.15):
    out = []
    if "T" in sides:
        out.append(fp_line(x1, y1, x2, y1, "F.SilkS", w, t))
    if "B" in sides:
        out.append(fp_line(x1, y2, x2, y2, "F.SilkS", w, t))
    if "L" in sides:
        out.append(fp_line(x1, y1, x1, y2, "F.SilkS", w, t))
    if "R" in sides:
        out.append(fp_line(x2, y1, x2, y2, "F.SilkS", w, t))
    return out


def footprint(name, descr, items, ref_at, val_at):
    fp = [Sym("footprint"), QStr(name), [Sym("version"), 20241229], [Sym("generator"), QStr("carrier_generator")],
          [Sym("layer"), QStr("F.Cu")], [Sym("descr"), QStr(descr)], [Sym("tags"), QStr("carrier module socket")],
          fprop("Reference", "REF**", ref_at[0], ref_at[1], "F.SilkS"),
          fprop("Value", name, val_at[0], val_at[1], "F.Fab"),
          fprop("Datasheet", "", 0, 0, "F.Fab", hide=True),
          fprop("Description", descr, 0, 0, "F.Fab", hide=True),
          [Sym("attr"), Sym("through_hole")]]
    fp += items
    fp.append(fp_text("${REFERENCE}", val_at[0], val_at[1] + 1.6, "F.Fab", 1.0))
    fp.append([Sym("embedded_fonts"), Sym("no")])
    with open(os.path.join(FPLIB, name + ".kicad_mod"), "w", encoding="utf8") as f:
        f.write(dumps(fp) + "\n")


def body(x1, y1, x2, y2, label, sides="LRTB", crt_extra=None):
    """Module body: full outline on Fab, dashed on silk, courtyard = body + 0.5 mm."""
    it = [fp_rect(x1, y1, x2, y2, "F.Fab", 0.1)]
    it += silk_box(x1, y1, x2, y2, sides)
    cx1, cy1, cx2, cy2 = x1, y1, x2, y2
    if crt_extra:
        cx1, cy1 = min(cx1, crt_extra[0]), min(cy1, crt_extra[1])
        cx2, cy2 = max(cx2, crt_extra[2]), max(cy2, crt_extra[3])
    it.append(fp_rect(cx1 - 0.5, cy1 - 0.5, cx2 + 0.5, cy2 + 0.5, "F.CrtYd", 0.05))
    it.append(fp_text(label, (x1 + x2) / 2, (y1 + y2) / 2, "F.Fab", 1.0))
    return it


def fp_devkit():
    from design import DEVKIT_J1, DEVKIT_J3, GPIO_NET
    it = []
    for i in range(22):
        it.append(tht_pad(str(i + 1), 0, i * 2.54, rect=(i == 0)))
        it.append(tht_pad(str(i + 23), 22.86, i * 2.54, rect=(i == 0)))
    for i, n in enumerate(DEVKIT_J1):
        fn = GPIO_NET.get(n)
        txt = n + (" " + fn if fn and fn not in ("+5V", "GND") else "")
        it.append(fp_text(txt, 1.45, i * 2.54, size=0.8, width=0.62, justify="left"))
    for i, n in enumerate(DEVKIT_J3):
        fn = GPIO_NET.get(n)
        txt = (fn + " " if fn and fn not in ("+5V", "GND") else "") + n
        it.append(fp_text(txt, 22.86 - 1.45, i * 2.54, size=0.8, width=0.62, justify="right"))
    x1, y1, x2, y2 = -1.27, -1.40, 24.13, 61.34
    it += [fp_rect(x1, y1, x2, y2, "F.Fab", 0.1)] + silk_box(x1, y1, x2, y2 - 0.6, "LRT")
    # The WROOM antenna overhangs the top of the DevKit
    it.append(fp_rect(2.46, -8.7, 20.6, -1.40, "F.Fab", 0.1))
    it += silk_box(2.46, -8.7, 20.6, -1.40, "LRT")
    it.append(fp_text("ESP ANTENNA - no copper", 11.43, -5.0, "F.SilkS", 0.8))
    it.append(fp_rect(1.0, 55.5, 8.7, 62.0, "F.Fab", 0.1))
    it.append(fp_rect(14.0, 55.5, 21.8, 62.0, "F.Fab", 0.1))
    it.append(fp_text("UART", 4.85, 58.5, "F.Fab", 0.8))
    it.append(fp_text("USB", 17.9, 58.5, "F.Fab", 0.8))
    it.append(fp_text("USB", 11.43, 59.0, "F.SilkS", 1.0))
    it.append(fp_rect(-1.77, -9.2, 24.63, 62.6, "F.CrtYd", 0.05))
    it.append(fp_text("ESP32-S3-DevKitC-1 N16R8", 11.43, 25.0, "F.Fab", 1.0, angle=90))
    it.append(model("PinSocket_1x22_P2.54mm_Vertical", 0, 0, 0))
    it.append(model("PinSocket_1x22_P2.54mm_Vertical", 22.86, 0, 0))
    footprint("ESP32-S3-DevKitC-1_Socket",
              "ESP32-S3-DevKitC-1 v1.1 on 2x 1x22 female sockets, 22.86 mm row spacing (Espressif DXF 2022-04-29)",
              it, (-3.0, -3.0), (11.43, 63.5))


def fp_2x4(name, descr, outer, inner, bw, blen, label, sma_len=9.0):
    """Top view, SMA up, header at the bottom. Outer row (y=0): odd pins 1,3,5,7 left to right.
    Inner row (y=-2.54): even pins 2,4,6,8."""
    it = []
    for k in range(4):
        it.append(tht_pad(str(2 * k + 1), 2.54 * k, 0.0, rect=(k == 0)))
        it.append(tht_pad(str(2 * k + 2), 2.54 * k, -2.54))
        it.append(fp_text(outer[k], 2.54 * k, 4.15, size=0.8, angle=90))
        it.append(fp_text(inner[k], 2.54 * k, -2.54 - 3.1, size=0.8, angle=90))
    cx = 3.81
    x1, x2 = cx - bw / 2, cx + bw / 2
    y2 = 2.2
    y1 = y2 - blen
    it += body(x1, y1, x2, y2, label, sides="B", crt_extra=(cx - 4.0, y1 - sma_len, cx + 4.0, y1))
    it += [fp_line(x1, y1 + 2.0, x1, y2, "F.SilkS", 0.15, "dash"), fp_line(x2, y1 + 2.0, x2, y2, "F.SilkS", 0.15, "dash")]
    it.append(fp_rect(cx - 3.2, y1 - sma_len, cx + 3.2, y1, "F.Fab", 0.1))
    it.append(fp_text("SMA", cx, y1 - sma_len / 2, "F.Fab", 1.0))
    it.append(fp_text(label, cx, y1 + 9.0, "F.SilkS", 1.0))
    it.append(fp_text("SMA ^ out", cx, y1 + 11.0, "F.SilkS", 0.8))
    it.append(model("PinSocket_2x04_P2.54mm_Vertical", 0.0, -2.54, 270))
    footprint(name, descr, it, (cx, y1 + 6.5), (cx, y1 + 13.0))


def fp_pn532():
    it = []
    names = ["GND", "VCC", "SDA", "SCL"]
    for k in range(4):
        it.append(tht_pad(str(k + 1), 0, 2.54 * k, rect=(k == 0)))
        it.append(fp_text(names[k], 1.5, 2.54 * k, size=0.8, justify="left"))
    x1, y1, x2, y2 = -6.5, -16.09, 36.2, 24.31
    it += body(x1, y1, x2, y2, "PN532 NFC V3")
    # The two mounting holes of the Elechouse V3 board (for nylon standoffs)
    it.append(npth(0.2, -9.69, 3.2))
    it.append(npth(31.0, 18.51, 3.2))
    it.append(fp_circle(0.2, -9.69, 2.8, "F.SilkS", 0.12))
    it.append(fp_circle(31.0, 18.51, 2.8, "F.SilkS", 0.12))
    it.append(fp_text("PN532 V3 NFC", 16.0, -6.0, "F.SilkS", 1.2))
    it.append(fp_text("I2C: SW1=ON SW2=OFF", 16.0, -3.5, "F.SilkS", 0.9))
    it.append(fp_text("antenna area - no copper", 16.0, 9.0, "F.SilkS", 0.9))
    it.append(fp_text("support: nylon M3", 16.0, 15.0, "F.SilkS", 0.8))
    it.append(model("PinSocket_1x04_P2.54mm_Vertical", 0, 0, 0))
    footprint("PN532_V3_I2C_Socket", "Elechouse PN532 V3 (42.7x40.4mm), socket for the 1x4 I2C header on its left edge",
              it, (-2.5, -1.5), (16.0, 20.0))


def fp_oled():
    it = []
    names = ["GND", "VCC", "SCL", "SDA"]
    for k in range(4):
        it.append(tht_pad(str(k + 1), 2.54 * k, 0, rect=(k == 0)))
        it.append(fp_text(names[k], 2.54 * k, 3.0, size=0.8, angle=90))
    cx = 3.81
    x1, y1, x2, y2 = cx - 17.7, -1.6, cx + 17.7, 31.9
    it += body(x1, y1, x2, y2, "OLED 1.3in SH1106")
    it.append(fp_rect(cx - 17.2, 3.0, cx + 17.2, 26.0, "F.Fab", 0.1))
    it.append(fp_text("OLED 1.3\" SH1106 I2C", cx, 12.0, "F.SilkS", 1.2))
    it.append(fp_text("GND-VCC-SCL-SDA", cx, 15.0, "F.SilkS", 0.9))
    it.append(model("PinSocket_1x04_P2.54mm_Vertical", 0, 0, 270))
    footprint("OLED_1.3in_I2C_Socket", "1.3in SH1106 I2C OLED (35.4x33.5mm), centred 1x4 header on the top edge",
              it, (x1 + 2.0, 2.0), (cx, 29.0))


def fp_sd():
    it = []
    names = ["GND", "VCC", "MISO", "MOSI", "SCK", "CS"]
    for k in range(6):
        it.append(tht_pad(str(k + 1), 0, 2.54 * k, rect=(k == 0)))
        it.append(fp_text(names[k], 1.5, 2.54 * k, size=0.8, justify="left"))
    x1, y1, x2, y2 = -1.7, -5.65, 40.3, 18.35
    it += body(x1, y1, x2, y2, "Catalex microSD", sides="L")
    it += [fp_line(x1, y1, 38.6, y1, "F.SilkS", 0.15, "dash"), fp_line(x1, y2, 38.6, y2, "F.SilkS", 0.15, "dash")]
    it.append(fp_rect(26.0, 0.35, 40.3, 12.35, "F.Fab", 0.1))
    it.append(fp_text("card slot ->", 31.0, 6.35, "F.Fab", 0.8))
    it.append(fp_text("microSD (Catalex)", 20.0, 3.0, "F.SilkS", 1.1))
    it.append(fp_text("card slot at edge ->", 20.0, 9.5, "F.SilkS", 0.8))
    it.append(model("PinSocket_1x06_P2.54mm_Vertical", 0, 0, 0))
    footprint("microSD_Catalex_Socket", "Catalex microSD module (~42x24mm), 1x6 header on the short edge",
              it, (6.0, -3.5), (20.0, 15.0))


def fp_rdm():
    it = []
    p1 = ["TX", "RX", "NC", "GND", "5V"]
    for k in range(5):
        it.append(tht_pad(str(k + 1), -2.54 * k, 0, rect=(k == 0)))
        it.append(fp_text(p1[k], -2.54 * k, 3.15, size=0.8, angle=90))
    it.append(tht_pad("6", -32.1, -15.8, rect=True))
    it.append(tht_pad("7", -29.56, -15.8))
    it.append(fp_text("ANT1", -32.1, -13.0, size=0.8, angle=90))
    it.append(fp_text("ANT2", -29.56, -13.0, size=0.8, angle=90))
    x1, y1, x2, y2 = -35.6, -17.4, 2.9, 1.6
    it += body(x1, y1, x2, y2, "RDM6300")
    it.append(fp_text("RDM6300 125kHz", -16.0, -9.0, "F.SilkS", 1.2))
    it.append(fp_text("P2 (antenna)", -29.6, -10.0, "F.SilkS", 0.8))
    it.append(fp_text("P1", -5.08, -2.2, "F.SilkS", 0.8))
    it.append(model("PinSocket_1x05_P2.54mm_Vertical", 0, 0, 90))
    it.append(model("PinSocket_1x02_P2.54mm_Vertical", -32.1, -15.8, 270))
    footprint("RDM6300_Socket", "RDM6300 (38.5x19mm): P1 1x5 (TX,RX,NC,GND,+5V) + P2 1x2 antenna socket",
              it, (-12.0, -1.0), (-16.0, -4.0))


def fp_si5351():
    """Top view with the SMA edge up: 1x4 header (VCC, GND, SCL, SDA) centred on the opposite edge."""
    it = []
    names = ["VCC", "GND", "SCL", "SDA"]
    for k in range(4):
        it.append(tht_pad(str(k + 1), 2.54 * k, 0, rect=(k == 0)))
        it.append(fp_text(names[k], 2.54 * k, -3.2, size=0.8, angle=90))
    cx = 3.81
    bw, blen, sma = 32.0, 25.0, 8.0
    x1, x2 = cx - bw / 2, cx + bw / 2
    y2 = 2.0
    y1 = y2 - blen
    it += body(x1, y1, x2, y2, "Si5351", sides="B", crt_extra=(x1, y1 - sma, x2, y1))
    it += [fp_line(x1, y1 + 2.0, x1, y2, "F.SilkS", 0.15, "dash"), fp_line(x2, y1 + 2.0, x2, y2, "F.SilkS", 0.15, "dash")]
    for k, dx in enumerate((-10.0, 0.0, 10.0)):
        it.append(fp_rect(cx + dx - 3.2, y1 - sma, cx + dx + 3.2, y1, "F.Fab", 0.1))
        it.append(fp_text("CLK%d" % k, cx + dx, y1 - sma / 2, "F.Fab", 0.8))
    it.append(fp_text("Si5351 CLOCK GEN", cx, y1 + 9.0, "F.SilkS", 1.1))
    it.append(fp_text("3x SMA out (board edge)", cx, y1 + 11.5, "F.SilkS", 0.8))
    it.append(fp_text("VCC-GND-SCL-SDA", cx, y1 + 13.8, "F.SilkS", 0.8))
    it.append(model("PinSocket_1x04_P2.54mm_Vertical", 0, 0, 270))
    footprint("Si5351_3SMA_Socket", "Si5351 clock generator module (~32x25mm + 3 SMA), 1x4 I2C header (VCC,GND,SCL,SDA)",
              it, (x1 + 2.5, y1 + 4.0), (cx, y1 + 17.0))


def write_fplib():
    os.makedirs(FPLIB, exist_ok=True)
    fp_devkit()
    fp_2x4("NRF24L01_PA_LNA_Socket", "nRF24L01+PA+LNA module with SMA (~16.5x41mm + SMA), 2x4 header socket",
           ["GND", "CE", "SCK", "MISO"], ["VCC", "CSN", "MOSI", "IRQ"], 16.5, 41.0, "NRF24 PA+LNA")
    fp_2x4("CC1101_SMA_2x4_Socket", "CC1101 433MHz module with SMA (~27x40mm + SMA), 2x4 header socket",
           ["GND", "GDO0", "SCK", "MISO"], ["VCC", "CSN", "MOSI", "GDO2"], 27.0, 40.0, "CC1101 433MHz")
    fp_pn532()
    fp_oled()
    fp_sd()
    fp_rdm()
    fp_si5351()


def write_tables():
    with open(os.path.join(PROJ, "sym-lib-table"), "w", encoding="utf8") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "Carrier") (type "KiCad") (uri "${KIPRJMOD}/Carrier.kicad_sym") (options "") (descr "Project symbols"))\n)\n')
    with open(os.path.join(PROJ, "fp-lib-table"), "w", encoding="utf8") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "Carrier") (type "KiCad") (uri "${KIPRJMOD}/Carrier.pretty") (options "") (descr "Project footprints"))\n)\n')


if __name__ == "__main__":
    write_symlib()
    write_fplib()
    write_tables()
    print("library done")
