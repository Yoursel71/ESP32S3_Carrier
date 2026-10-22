"""Exports the routed board to JSON and builds the interactive 3D explorer (output/board_explorer.html)."""
import os
import sys
import json
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
from sexpr import parse, find, findall

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
PCB = os.path.join(PROJ, D.PROJECT + ".kicad_pcb")
NETLIST = os.path.join(HERE, "_net.net")
TEMPLATE = os.path.join(HERE, "viewer_template.html")
OUT_HTML = os.path.join(PROJ, "output", "board_explorer.html")
OUT_FRAGMENT = os.path.join(HERE, "_board_explorer_fragment.html")  # page body without <html>/<head>, for publishing

F, B = pcbnew.F_Cu, pcbnew.B_Cu


def mm(v):
    return round(pcbnew.ToMM(v), 3)


def xy(p):
    return [round(pcbnew.ToMM(p.x) - D.OX, 2), round(pcbnew.ToMM(p.y) - D.OY, 2)]


def chains(ps, step=1):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        n = o.PointCount()
        pts = []
        for j in range(0, n, step):
            pts += xy(o.CPoint(j))
        out.append(pts)
    return out


def netlist_pins():
    t = parse(open(NETLIST, encoding="utf8").read())
    pins = {}
    for n in findall(find(t, "nets"), "net"):
        name = str(find(n, "name")[1])
        lst = []
        for node in findall(n, "node"):
            pf = find(node, "pinfunction")
            ref, pin, fn = str(find(node, "ref")[1]), str(find(node, "pin")[1]), str(pf[1]) if pf else ""
            if fn.endswith("_" + pin):  # KiCad appends the pin number to the pin name
                fn = fn[: -len(pin) - 1]
            lst.append([ref, pin, fn])
        pins[name] = lst
    return pins


def kind_of(fpid):
    lib, name = fpid.split(":")
    if lib == "Carrier":
        return "module"
    for key, k in (("CP_Radial", "cap"), ("SW_PUSH", "button"), ("Buzzer", "buzzer"), ("TO-92", "to92"),
                   ("LED_D5.0mm_Horizontal", "led"), ("SOT-223", "sot223"), ("SOT-23", "sot23"), ("SW_Slide", "slide"),
                   ("D_DO-35", "diode"), ("MINICAST", "irrx"), ("PinHeader", "header"), ("MountingHole", "hole"),
                   ("SolderJumper", "jumper"), ("R_", "smd"), ("C_", "smd")):
        if key in name:
            return k
    return "smd"


def main():
    board = pcbnew.LoadBoard(PCB)
    netpins = netlist_pins()
    nets = sorted({n.GetNetname() for n in board.GetNetsByName().values() if n.GetNetname()})
    nets = [n for n in nets if not n.startswith("unconnected")]
    nidx = {n: i for i, n in enumerate(nets)}

    def ni(item):
        return nidx.get(item.GetNetname(), -1)

    tracks, vias = [], []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias.append(xy(t.GetPosition()) + [mm(t.GetWidth(F)), mm(t.GetDrillValue()), ni(t)])
        else:
            s, e = xy(t.GetStart()), xy(t.GetEnd())
            tracks.append(s + e + [mm(t.GetWidth()), 0 if t.GetLayer() == F else 1, ni(t)])

    pads, comps = [], []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            layers = (1 if p.IsOnLayer(F) else 0) | (2 if p.IsOnLayer(B) else 0)
            if not layers:
                continue
            lay = F if layers & 1 else B
            poly = p.GetEffectivePolygon(lay, pcbnew.ERROR_INSIDE)
            drill = mm(p.GetDrillSize().x) if p.GetDrillSize().x > 0 else 0
            pads.append({"r": ref, "n": p.GetNumber(), "net": ni(p), "l": layers, "d": drill,
                         "c": xy(p.GetPosition()), "poly": chains(poly)[0] if poly.OutlineCount() else []})
        crt = None
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_CrtYd:
                bb = g.GetBoundingBox()
                if crt is None:
                    crt = pcbnew.BOX2I(bb.GetOrigin(), bb.GetSize())
                else:
                    crt.Merge(bb)
        if crt is None:
            crt = fp.GetBoundingBox(False)
        x1, y1 = xy(crt.GetOrigin())
        x2, y2 = xy(crt.GetEnd())
        comps.append({"r": ref, "v": fp.GetValue(), "k": kind_of(fp.GetFPIDAsString()), "c": xy(fp.GetPosition()),
                      "rot": round(fp.GetOrientationDegrees(), 1), "bb": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]})

    zones = []
    for z in board.Zones():
        if z.GetIsRuleArea():
            bb = z.GetBoundingBox()
            zones.append({"keepout": z.GetZoneName(), "bb": xy(bb.GetOrigin()) + xy(bb.GetEnd())})
            continue
        for lay in (F, B):
            if z.IsOnLayer(lay):
                zones.append({"l": 0 if lay == F else 1, "net": ni(z), "polys": chains(z.GetFilledPolysList(lay))})

    # Silkscreen as polygons (front and back)
    silk = {}
    for lay, key in ((pcbnew.F_SilkS, "F"), (pcbnew.B_SilkS, "B")):
        ps = pcbnew.SHAPE_POLY_SET()
        items = [d for d in board.GetDrawings() if d.GetLayer() == lay]
        for fp in board.GetFootprints():
            items += [g for g in fp.GraphicalItems() if g.GetLayer() == lay]
            for fld in (fp.Reference(), fp.Value()):
                if fld.GetLayer() == lay and fld.IsVisible():
                    items.append(fld)
        for it in items:
            if it.GetClass() in ("PCB_TEXT", "PCB_FIELD"):
                it.TransformTextToPolySet(ps, 0, pcbnew.FromMM(0.02), pcbnew.ERROR_INSIDE)
            else:
                it.TransformShapeToPolygon(ps, lay, 0, pcbnew.FromMM(0.02), pcbnew.ERROR_INSIDE)
        ps.Simplify()
        ps.Fracture()
        silk[key] = chains(ps)

    pinmeta = {}
    for name, lst in netpins.items():
        if name in nidx:
            pinmeta[nidx[name]] = lst
    classes = {n: D.NETCLASS_ASSIGN.get(n, "Default") for n in nets}
    data = {"board": {"w": D.W, "h": D.H, "r": D.CORNER_R, "t": 1.6, "rev": D.REV, "date": D.DATE},
            "nets": nets, "netclass": classes, "pins": pinmeta, "tracks": tracks, "vias": vias, "pads": pads,
            "zones": zones, "comps": comps, "silk": silk}
    js = json.dumps(data, separators=(",", ":"))
    tpl = open(TEMPLATE, encoding="utf8").read()
    fragment = tpl.replace("/*__BOARD_DATA__*/null", js)
    with open(OUT_FRAGMENT, "w", encoding="utf8") as f:
        f.write(fragment)
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf8") as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '</head>\n<body>\n' + fragment + '\n</body>\n</html>\n')
    print("tracks %d vias %d pads %d comps %d nets %d json %.0f kB" % (len(tracks), len(vias), len(pads), len(comps), len(nets), len(js) / 1024))


if __name__ == "__main__":
    main()
