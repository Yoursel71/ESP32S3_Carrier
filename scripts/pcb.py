"""Tasarim verisi + sema netlistinden .kicad_pcb uretir (yonlendirme oncesi)."""
import os
import sys
import json
import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import tasarim as T
from sexpr import parse, find, findall

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PROJ, T.PROJE + ".kicad_pcb")
NETLIST = os.path.join(PROJ, "scripts", "_net.net")
UUIDS = os.path.join(PROJ, "scripts", "uuid_tablosu.json")
KFP = r"D:\KiCad\share\kicad\footprints"


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(T.OX + x), mm(T.OY + y))


def read_netlist():
    t = parse(open(NETLIST, encoding="utf8").read())
    pinnet = {}
    for n in findall(find(t, "nets"), "net"):
        name = str(find(n, "name")[1])
        for node in findall(n, "node"):
            pinnet[(str(find(node, "ref")[1]), str(find(node, "pin")[1]))] = name
    return pinnet


def read_sch_fields():
    """Sema sembol alanlari (Reference/Value/Footprint disinda) -> footprint alanlari."""
    sch = os.path.join(PROJ, T.PROJE + ".kicad_sch")
    t = parse(open(sch, encoding="utf8").read())
    out = {}
    for s_ in findall(t, "symbol"):
        props = {str(p[1]): str(p[2]) for p in findall(s_, "property")}
        ref = props.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        out[ref] = {k: v for k, v in props.items() if k not in ("Reference", "Value", "Footprint")}
    return out


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(PROJ, "Tasiyici.pretty") if lib == "Tasiyici" else os.path.join(KFP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("footprint yok: " + fpid)
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


def add_text(board, txt, x, y, size=1.0, layer=pcbnew.F_SilkS, angle=0, thick=None, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick or size * 0.15))
    if angle:
        t.SetTextAngleDegrees(angle)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        t.SetMirrored(True)
    board.Add(t)
    return t


def rule_area(board, name, x1, y1, x2, y2, tracks=True, vias=True, fills=True):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(fills)
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
    return z


def outline(board):
    W, H, r = T.W, T.H, T.KOSE_R
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
    c = T.NET_SINIFLARI["Default"]
    d.SetTrackWidth(mm(c["track"]))
    d.SetClearance(mm(c["clearance"]))
    d.SetViaDiameter(mm(c["via_d"]))
    d.SetViaDrill(mm(c["via_drill"]))
    for name in ("Guc", "GND"):
        c = T.NET_SINIFLARI[name]
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(mm(c["track"]))
        nc.SetClearance(mm(c["clearance"]))
        nc.SetViaDiameter(mm(c["via_d"]))
        nc.SetViaDrill(mm(c["via_drill"]))
        ns.SetNetclass(name, nc)
    for net, cls in T.NET_SINIF_ATAMA.items():
        ns.SetNetclassPatternAssignment(net, cls)
    ds.m_TrackMinWidth = mm(0.15)  # hedef 0.25; Freerouting'in birakabildigi tek tuk 0.18 mm'lik izler icin alt sinir (6 mil)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_HoleClearance = mm(0.25)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_MinClearance = mm(0.2)
    ds.SetCopperLayerCount(2)
    tb = board.GetTitleBlock()
    tb.SetTitle("ESP32-S3 Tasiyici Kart")
    tb.SetDate(T.TARIH)
    tb.SetRevision(T.REV)
    tb.SetCompany("github.com/Yoursel71")
    tb.SetComment(0, "2 katman, 1.6 mm FR4, %dx%d mm" % (T.W, T.H))
    tb.SetComment(1, "1:1 olcek - %100 / gercek boyut yazdirin")
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
    sheetfile = T.PROJE + ".kicad_sch"
    for c in T.BILESENLER:
        fp = load_fp(c["fp"])
        fp.SetReference(c["ref"])
        fp.SetValue(c["val"])
        x, y, rot = c["pcb"]
        fp.SetPosition(P(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuids[c["ref"]]))
        fp.SetSheetname("/")
        fp.SetSheetfile(sheetfile)
        for k, v in schf.get(c["ref"], {}).items():
            fp.SetField(k, v)
            f = fp.GetField(k)
            if f is not None:
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue
            n = pinnet.get((c["ref"], num))
            if n:
                pad.SetNet(nets[n])
        board.Add(fp)
        # buton etiketleri
        if c.get("etiket"):
            add_text(board, c["etiket"], x + 3.25, y + 2.25 + 4.6, 1.0)
        ry = T.REF_YER.get(c["ref"])
        if ry:
            rf = fp.Reference()
            rf.SetPosition(P(ry[0], ry[1]))
            rf.SetTextAngleDegrees(ry[2])
    for ref, x, y in T.MONTAJ:
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(ref)
        fp.SetValue("M3")
        fp.SetPosition(P(x, y))
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
        board.Add(fp)
    outline(board)

    # Bakir yasak alanlari (anten)
    rule_area(board, "ESP32 anten", 48.0, 80.0, 68.0, 92.3)
    rule_area(board, "PN532 anten", 82.0, 55.0, 115.2, 95.4)

    # Serigrafi notlari
    add_text(board, "ESP32-S3 TAŞIYICI v%s" % T.REV, 92.0, 148.6, 1.3)
    add_text(board, T.TARIH + "  github.com/Yoursel71", 92.0, 151.2, 0.8)
    add_text(board, "MODÜL GÜCÜ", 34.5, 148.6, 0.9)
    add_text(board, "AÇIK", 27.2, 152.4, 0.8)
    add_text(board, "KAPALI", 42.3, 152.4, 0.8)
    add_text(board, "125kHz BOBİN", 7.5, 115.2, 0.8)
    add_text(board, "MISO köprü", 73.0, 123.7, 0.8, angle=90)
    add_text(board, "IR TX", 43.25, 33.0, 0.8)
    add_text(board, "IR RX", 71.5, 13.0, 0.8)
    # Arka yuz bilgi
    add_text(board, "ESP32-S3 TAŞIYICI v%s" % T.REV, 21.5, 72.0, 1.0, layer=pcbnew.B_SilkS)
    add_text(board, "Modüller ön yüze takılır", 21.5, 75.0, 1.0, layer=pcbnew.B_SilkS)

    # 1:1 olcek kontrol cubugu (kartin altinda, Dwgs.User)
    yb = T.H + 7.0
    L = pcbnew.Dwgs_User
    add_seg(board, 0, yb, 50, yb, L, 0.2)
    for xx in range(0, 51, 10):
        add_seg(board, xx, yb - (1.5 if xx % 50 == 0 else 0.8), xx, yb, L, 0.2)
    add_text(board, "50 mm - %100 ölçekte yazdırınca bu çizgi 50 mm olmalı", 25.0, yb + 2.2, 1.2, layer=L)
    add_text(board, "Kart %d x %d mm" % (T.W, T.H), 85.0, yb, 1.5, layer=L)
    return board


def sayfa_a4_dikey(path):
    txt = open(path, encoding="utf8").read()
    import re as _re
    txt = _re.sub(r'\(paper "[^"]*"( portrait)?\)', '(paper "A4" portrait)', txt, count=1)
    open(path, "w", encoding="utf8").write(txt)


if __name__ == "__main__":
    b = build()
    pcbnew.SaveBoard(PCB, b)
    sayfa_a4_dikey(PCB)
    print("pcb kaydedildi:", PCB)
    if len(sys.argv) > 1 and sys.argv[1] == "dsn":
        out = os.path.join(PROJ, "scripts", "_rota.dsn")
        ok = pcbnew.ExportSpecctraDSN(b, out)
        print("dsn:", ok, out)
