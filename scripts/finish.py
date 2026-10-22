"""After routing: import the SES, tidy track widths, pour GND on both layers, add stitching vias, fill, save."""
import os
import sys
import math
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
from pcb import PCB, P, mm, page_a4_portrait

SES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_route.ses")
# GND pads that get a solid zone connection (surrounded by tracks/keep-outs, a thermal would be starved)
SOLID_GND = {("U1", "23"), ("J1", "1"), ("J2", "1"), ("J3", "1"), ("J6", "1")}


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
    for x, y in ((0, 0), (D.W, 0), (D.W, D.H), (0, D.H)):
        p = P(x, y)
        o.Append(p.x, p.y)
    board.Add(z)


def fill(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def stitch(board, gnd, step=6.0, margin=3.5):
    via_d, via_drill, clr = 0.8, 0.4, 0.35
    keepouts = [z for z in board.Zones() if z.GetIsRuleArea()]
    zones = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    tracks = list(board.GetTracks())
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    holes = [fp.GetPosition() for fp in board.GetFootprints() if fp.GetReference().startswith("H")]
    added = n = 0
    y = margin
    while y <= D.H - margin:
        x = margin
        while x <= D.W - margin:
            n += 1
            pt = P(x, y)
            ok = not any(k.Outline().Contains(pt) for k in keepouts)
            ok = ok and all(math.hypot(pt.x - h.x, pt.y - h.y) >= mm(1.6 + via_d / 2 + 1.0) for h in holes)
            if ok:
                for t in tracks:
                    if t.GetClass() == "PCB_VIA":
                        if math.hypot(pt.x - t.GetPosition().x, pt.y - t.GetPosition().y) < mm(0.4) + mm(via_d / 2 + clr):
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
            if ok:  # the via must sit inside the GND fill on both layers
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
    return D.NET_CLASSES[D.NETCLASS_ASSIGN.get(item.GetNetname(), "Default")]["clearance"]


def widen_safe(board, target=0.2):
    """Freerouting necks tracks down to 0.15-0.19 mm at some pad entries; widen them to 0.20 mm where clearance allows."""
    items = list(board.GetTracks()) + [p for fp in board.GetFootprints() for p in fp.Pads()]
    thin = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(target)]
    done = left = 0
    for t in thin:
        old = t.GetWidth()
        t.SetWidth(mm(target))
        layer = t.GetLayer()
        shp = t.GetEffectiveShape(layer)
        bb = t.GetBoundingBox()
        bb.Inflate(mm(0.5))
        ok = True
        for o in items:
            if o is t or o.GetNetCode() == t.GetNetCode() or not o.IsOnLayer(layer):
                continue
            if not bb.Intersects(o.GetBoundingBox()):
                continue
            if shp.Collide(o.GetEffectiveShape(layer), mm(max(clearance_of(t), clearance_of(o)) + 0.005)):
                ok = False
                break
        if ok:
            done += 1
        else:
            t.SetWidth(old)
            left += 1
    return done, left


def main():
    board = pcbnew.LoadBoard(PCB)
    if os.path.exists(SES):
        print("SES import:", pcbnew.ImportSpecctraSES(board, SES))
    done, left = widen_safe(board)
    print("thin tracks widened:", done, "left as-is:", left)
    gnd = board.FindNet("GND")
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != "GND":
                continue
            if fp.GetReference() == "U1":
                pad.SetThermalSpokeAngleDegrees(45)
            if (fp.GetReference(), pad.GetNumber()) in SOLID_GND:
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for z in [z for z in board.Zones() if not z.GetIsRuleArea()]:
        board.Remove(z)
    gnd_zone(board, pcbnew.F_Cu, gnd)
    gnd_zone(board, pcbnew.B_Cu, gnd)
    fill(board)
    added, n = stitch(board, gnd)
    print("stitching vias:", added, "/", n)
    fill(board)
    pcbnew.SaveBoard(PCB, board)
    page_a4_portrait(PCB)
    print("saved")


if __name__ == "__main__":
    main()
