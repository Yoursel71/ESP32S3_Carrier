"""Compares the netlist exported from the schematic with design.py, pin by pin."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find, findall
import design as D

t = parse(open(sys.argv[1], encoding="utf8").read())
got = {}
for n in findall(find(t, "nets"), "net"):
    name = str(find(n, "name")[1]).lstrip("/")
    for node in findall(n, "node"):
        got[(str(find(node, "ref")[1]), str(find(node, "pin")[1]))] = name
want = {(c["ref"], pin): net for c in D.COMPONENTS for pin, net in c["pins"].items()}
bad = 0
for k, v in sorted(want.items()):
    g = got.get(k)
    if v is None:
        if g is not None and not g.startswith("unconnected"):
            print("expected no-connect:", k, g)
            bad += 1
    elif g != v:
        print("MISMATCH:", k, "expected", v, "got", g)
        bad += 1
comps = {str(find(c, "ref")[1]): (str(find(c, "value")[1]), str(find(c, "footprint")[1]))
         for c in findall(find(t, "components"), "comp")}
for c in D.COMPONENTS:
    if comps.get(c["ref"]) != (c["val"], c["fp"]):
        print("COMPONENT MISMATCH:", c["ref"], comps.get(c["ref"]), (c["val"], c["fp"]))
        bad += 1
print("pins:", len(want), "nets:", len({v for v in want.values() if v}), "errors:", bad)
sys.exit(1 if bad else 0)
