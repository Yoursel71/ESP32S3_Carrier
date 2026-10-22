"""Builds the unrouted .kicad_pcb from design.py + the schematic netlist (and optionally exports a Specctra DSN)."""
import os
import re
import sys
import json
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
from sexpr import parse, find, findall

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PROJ, D.PROJECT + ".kicad_pcb")
NETLIST = os.path.join(PROJ, "scripts", "_net.net")
UUIDS = os.path.join(PROJ, "scripts", "uuid_table.json")
KFP = r"D:\KiCad\share\kicad\footprints"


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(D.OX + x), mm(D.OY + y))


def read_netlist():
    t = parse(open(NETLIST, encoding="utf8").read())
    pinnet = {}
    for n in findall(find(t, "nets"), "net"):
        name = str(find(n, "name")[1])
        for node in findall(n, "node"):
            pinnet[(str(find(node, "ref")[1]), str(find(node, "pin")[1]))] = name
    return pinnet


def read_sch_fields():
    """Symbol fields (except Reference/Value/Footprint) are copied to the footprints, like 'Update PCB from Schematic'."""
    t = parse(open(os.path.join(PROJ, D.PROJECT + ".kicad_sch"), encoding="utf8").read())
    out = {}
    for s_ in findall(t, "symbol"):
        props = {str(p[1]): str(p[2]) for p in findall(s_, "property")}
        ref = props.get("Reference", "")
        if ref and not ref.startswith("#"):
            out[ref] = {k: v for k, v in props.items() if k not in ("Reference", "Value", "Footprint")}
    return out


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(PROJ, "Carrier.pretty") if lib == "Carrier" else os.path.join(KFP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("footprint not found: " + fpid)
    fp.SetFPIDAsString(fpid)
    return fp


def add_seg(board, x1, y1, x2, y2, layer, w):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(x1, y1))
    s.SetEnd(P(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def add_arc(board, s_, m_, e_, layer, w):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*s_), P(*m_), P(*e_))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def add_text(board, txt, x, y, size=1.0, layer=pcbnew.F_SilkS, angle=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(max(size * 0.15, 0.12)))
    if angle:
        t.SetTextAngleDegrees(angle)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)
    return t


def rule_area(board, name, x1, y1, x2, y2):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        p = P(x, y)
        o.Append(p.x, p.y)
    board.Add(z)


def outline(board):
    W, H, r = D.W, D.H, D.CORNER_R
    L = pcbnew.Edge_Cuts
    add_seg(board, r, 0, W - r, 0, L, 0.1)
    add_seg(board, W, r, W, H - r, L, 0.1)
    add_seg(board, W - r, H, r, H, L, 0.1)
    add_seg(board, 0, H - r, 0, r, L, 0.1)
    k = r * (1 - 0.70710678)
    add_arc(board, (W - r, 0), (W - k, k), (W, r), L, 0.1)
    add_arc(board, (W, H - r), (W - k, H - k), (W - r, H), L, 0.1)
    add_arc(board, (r, H), (k, H - k), (0, H - r), L, 0.1)
    add_arc(board, (0, r), (k, k), (r, 0), L, 0.1)


def setup_rules(board):
    ds = board.GetDesignSettings()
    ns = ds.m_NetSettings
    d = ns.GetDefaultNetclass()
    c = D.NET_CLASSES["Default"]
    d.SetTrackWidth(mm(c["track"]))
    d.SetClearance(mm(c["clearance"]))
    d.SetViaDiameter(mm(c["via_d"]))
    d.SetViaDrill(mm(c["via_drill"]))
    for name in ("Power", "GND"):
        c = D.NET_CLASSES[name]
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(mm(c["track"]))
        nc.SetClearance(mm(c["clearance"]))
        nc.SetViaDiameter(mm(c["via_d"]))
        nc.SetViaDrill(mm(c["via_drill"]))
        ns.SetNetclass(name, nc)
    for net, cls in D.NETCLASS_ASSIGN.items():
        ns.SetNetclassPatternAssignment(net, cls)
    # target width is 0.25 mm; finish.py widens Freerouting's pad-entry neck-downs to >= 0.20 mm
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleClearance = mm(0.25)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_MinClearance = mm(0.2)
    ds.SetCopperLayerCount(2)
    tb = board.GetTitleBlock()
    tb.SetTitle("ESP32-S3 Carrier Board")
    tb.SetDate(D.DATE)
    tb.SetRevision(D.REV)
    tb.SetCompany("github.com/Yoursel71")
    tb.SetComment(0, "2 layers, 1.6 mm FR4, %dx%d mm" % (D.W, D.H))
    tb.SetComment(1, "1:1 scale - print at 100% / actual size")
    board.SetTitleBlock(tb)


def build():
    pinnet = read_netlist()
    schf = read_sch_fields()
    uuids = json.load(open(UUIDS, encoding="utf8"))
    board = pcbnew.NewBoard(PCB)
    setup_rules(board)
    nets = {}
    for name in sorted(set(pinnet.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    for c in D.COMPONENTS:
        fp = load_fp(c["fp"])
        fp.SetReference(c["ref"])
        fp.SetValue(c["val"])
        x, y, rot = c["pcb"]
        fp.SetPosition(P(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuids[c["ref"]]))
        fp.SetSheetname("/")
        fp.SetSheetfile(D.PROJECT + ".kicad_sch")
        for k, v in schf.get(c["ref"], {}).items():
            fp.SetField(k, v)
            f = fp.GetField(k)
            if f is not None:
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num and (c["ref"], num) in pinnet:
                pad.SetNet(nets[pinnet[(c["ref"], num)]])
        board.Add(fp)
        if c.get("label"):  # button captions
            add_text(board, c["label"], x + 3.25, y + 2.25 + 4.6, 1.0)
        rp = D.REF_POS.get(c["ref"])
        if rp:
            rf = fp.Reference()
            rf.SetPosition(P(rp[0], rp[1]))
            rf.SetTextAngleDegrees(rp[2])
    for ref, x, y in D.MOUNTING:
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(ref)
        fp.SetValue("M3")
        fp.SetPosition(P(x, y))
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
        board.Add(fp)
    outline(board)
    for name, x1, y1, x2, y2 in D.KEEPOUTS:
        rule_area(board, name, x1, y1, x2, y2)

    # Silkscreen notes (front)
    add_text(board, "ESP32-S3 CARRIER v%s" % D.REV, 21.5, 88.3, 1.2)
    add_text(board, "MODULE PWR", 6.0, 170.5, 0.8)
    add_text(board, "ON", 7.0, 177.4, 0.8)
    add_text(board, "BAT ON", 7.2, 137.2, 0.8)
    add_text(board, "OFF", 7.0, 183.6, 0.8)
    add_text(board, "OFF", 7.0, 144.6, 0.8)
    add_text(board, "125kHz COIL", 7.5, 115.2, 0.8)
    add_text(board, "MISO bridge", 73.0, 123.7, 0.8, angle=90)
    add_text(board, "IR TX x3", 36.5, 39.0, 0.8)
    add_text(board, "IR RX", 84.8, 16.0, 0.8)
    # Back side
    B = pcbnew.B_SilkS
    add_text(board, "ESP32-S3 CARRIER v%s" % D.REV, 21.5, 70.0, 1.0, layer=B)
    add_text(board, "github.com/Yoursel71  %s" % D.DATE, 21.5, 72.5, 0.8, layer=B)
    add_text(board, "Modules plug in on the front", 21.5, 75.0, 0.9, layer=B)

    # 1:1 scale check bar below the board (Dwgs.User)
    yb = D.H + 7.0
    L = pcbnew.Dwgs_User
    add_seg(board, 0, yb, 50, yb, L, 0.2)
    for xx in range(0, 51, 10):
        add_seg(board, xx, yb - (1.5 if xx % 50 == 0 else 0.8), xx, yb, L, 0.2)
    add_text(board, "50 mm - must measure 50 mm when printed at 100% (actual size)", 25.0, yb + 2.2, 1.2, layer=L)
    add_text(board, "Board %d x %d mm" % (D.W, D.H), 85.0, yb, 1.5, layer=L)
    return board


def page_a4_portrait(path):
    txt = open(path, encoding="utf8").read()
    txt = re.sub(r'\(paper "[^"]*"( portrait)?\)', '(paper "A4" portrait)', txt, count=1)
    open(path, "w", encoding="utf8").write(txt)


if __name__ == "__main__":
    b = build()
    pcbnew.SaveBoard(PCB, b)
    page_a4_portrait(PCB)
    print("pcb saved:", PCB)
    if len(sys.argv) > 1 and sys.argv[1] == "dsn":
        out = os.path.join(PROJ, "scripts", "_route.dsn")
        print("dsn:", pcbnew.ExportSpecctraDSN(b, out), out)
