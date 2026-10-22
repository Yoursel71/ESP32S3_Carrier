"""Semadan cikan netlisti tasarim.py ile karsilastirir."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, find, findall
import tasarim as T
t = parse(open(sys.argv[1], encoding="utf8").read())
nets = find(t, "nets")
got = {}
for n in findall(nets, "net"):
    name = str(find(n, "name")[1]).lstrip("/")
    for node in findall(n, "node"):
        ref = str(find(node, "ref")[1]); pin = str(find(node, "pin")[1])
        got[(ref, pin)] = name
want = {}
for c in T.BILESENLER:
    for pin, net in c["pins"].items():
        want[(c["ref"], pin)] = net
bad = 0
for k, v in sorted(want.items()):
    g = got.get(k)
    if v is None:
        if g is not None and not g.startswith("unconnected"):
            print("NC beklenirdi:", k, g); bad += 1
    elif g != v:
        print("FARK:", k, "beklenen", v, "bulunan", g); bad += 1
comps = {str(find(c, "ref")[1]): (str(find(c, "value")[1]), str(find(c, "footprint")[1])) for c in findall(find(t, "components"), "comp")}
for c in T.BILESENLER:
    if comps.get(c["ref"]) != (c["val"], c["fp"]):
        print("BILESEN FARKI:", c["ref"], comps.get(c["ref"]), (c["val"], c["fp"])); bad += 1
netcount = len({v for v in want.values() if v})
print("pin:", len(want), "net:", netcount, "hata:", bad)
