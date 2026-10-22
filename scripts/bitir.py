"""Yonlendirme sonrasi: SES ice aktar, iki katmana GND dokumu, dikis via'lari, doldur, kaydet."""
import os
import sys
import math
import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import tasarim as T
from pcb import PCB, P, mm, sayfa_a4_dikey

SES = os.path.join(os.path.dirname(__file__), "_rota.ses")


def gnd_zone(board, layer, net):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName("GND_" + ("F" if layer == pcbnew.F_Cu else "B"))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.4))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(0)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0, 0), (T.W, 0), (T.W, T.H), (0, T.H)):
        p = P(x, y)
        o.Append(p.x, p.y)
    board.Add(z)
    return z


def fill(board):
    f = pcbnew.ZONE_FILLER(board)
    f.Fill(board.Zones())


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def stitch(board, gnd, step=6.0, margin=3.5):
    via_d, via_drill = 0.8, 0.4
    clr = 0.35
    keepouts = [z for z in board.Zones() if z.GetIsRuleArea()]
    zones = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    tracks = list(board.GetTracks())
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    holes = [(fp.GetPosition(), 3.2) for fp in board.GetFootprints() if fp.GetReference().startswith("H")]
    added = 0
    n = 0
    y = margin
    while y <= T.H - margin:
        x = margin
        while x <= T.W - margin:
            n += 1
            pt = P(x, y)
            ok = True
            for k in keepouts:
                if k.Outline().Contains(pt):
                    ok = False
                    break
            if ok:
                for h, d in holes:
                    if math.hypot(pt.x - h.x, pt.y - h.y) < mm(d / 2 + via_d / 2 + 1.0):
                        ok = False
                        break
            if ok:
                for t in tracks:
                    if t.GetClass() == "PCB_VIA":
                        r = t.GetWidth(pcbnew.F_Cu) / 2 if hasattr(t, "GetWidth") else mm(0.4)
                        if math.hypot(pt.x - t.GetPosition().x, pt.y - t.GetPosition().y) < r + mm(via_d / 2 + clr):
                            ok = False
                            break
                    else:
                        s, e = t.GetStart(), t.GetEnd()
                        if seg_dist(pt.x, pt.y, s.x, s.y, e.x, e.y) < t.GetWidth() / 2 + mm(via_d / 2 + clr):
                            ok = False
                            break
            if ok:
                for p in pads:
                    bb = p.GetBoundingBox()
                    bb.Inflate(mm(via_d / 2 + clr))
                    if bb.Contains(pt):
                        ok = False
                        break
            if ok:
                # her iki katmanda da GND dolgusunun icinde olmali (cevresiyle)
                for z in zones:
                    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                        q = pcbnew.VECTOR2I(pt.x + mm(dx * via_d), pt.y + mm(dy * via_d))
                        if not z.HitTestFilledArea(z.GetLayer(), q):
                            ok = False
                            break
                    if not ok:
                        break
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pt)
                v.SetDrill(mm(via_drill))
                v.SetWidth(mm(via_d))
                v.SetNet(gnd)
                board.Add(v)
                tracks.append(v)
                added += 1
            x += step
        y += step
    return added, n


def clearance_of(item):
    cls = T.NET_SINIF_ATAMA.get(item.GetNetname(), "Default")
    return T.NET_SINIFLARI[cls]["clearance"]


def widen_safe(board, target=0.2):
    items = [t for t in board.GetTracks()] + [p for fp in board.GetFootprints() for p in fp.Pads()]
    thin = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(target)]
    n = 0
    kalan = 0
    for t in thin:
        old = t.GetWidth()
        t.SetWidth(mm(target))
        layer = t.GetLayer()
        shp = t.GetEffectiveShape(layer)
        bb = t.GetBoundingBox()
        bb.Inflate(mm(0.5))
        ok = True
        for o in items:
            if o is t or o.GetNetCode() == t.GetNetCode():
                continue
            if not o.IsOnLayer(layer):
                continue
            if not bb.Intersects(o.GetBoundingBox()):
                continue
            req = mm(max(clearance_of(t), clearance_of(o)) + 0.005)
            if shp.Collide(o.GetEffectiveShape(layer), req):
                ok = False
                break
        if ok:
            n += 1
        else:
            t.SetWidth(old)
            kalan += 1
    return n, kalan


def main():
    board = pcbnew.LoadBoard(PCB)
    if os.path.exists(SES):
        ok = pcbnew.ImportSpecctraSES(board, SES)
        print("SES ice aktarma:", ok)
    # Freerouting pad girislerinde izleri 0.15-0.19 mm'ye inceltebiliyor; bosluk izin veriyorsa >= 0.20 mm yap
    n, kalan = widen_safe(board)
    if kalan:
        print("UYARI: genisletilemeyen ince iz:", kalan)
    print("genisletilen ince iz:", n, "kalan:", kalan)
    gnd = board.FindNet("GND")
    # U1 GND padleri anten yasak alanina/izlere komsu: termal kollari capraz (45 derece) olsun
    for fp in board.GetFootprints():
        if fp.GetReference() == "U1":
            for pad in fp.Pads():
                if pad.GetNetname() == "GND":
                    pad.SetThermalSpokeAngleDegrees(45)
                if pad.GetNumber() == "23":  # J3-1 GND: ust ve sag tarafi anten yasak alani/izler, tam baglanti
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        # RF modul soketlerinin GND padi: cevresi izlerle cevrili kucuk dokum adalari tek kolla kalmasin
        if fp.GetReference() in ("J1", "J2", "J3"):
            for pad in fp.Pads():
                if pad.GetNetname() == "GND":
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for z in [z for z in board.Zones() if not z.GetIsRuleArea()]:
        board.Remove(z)
    gnd_zone(board, pcbnew.F_Cu, gnd)
    gnd_zone(board, pcbnew.B_Cu, gnd)
    fill(board)
    added, n = stitch(board, gnd)
    print("dikis via:", added, "/", n)
    fill(board)
    pcbnew.SaveBoard(PCB, board)
    sayfa_a4_dikey(PCB)
    print("kaydedildi")


if __name__ == "__main__":
    main()
