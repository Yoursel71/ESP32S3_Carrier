"""Tum akis: python uret.py [hepsi|yerlesim|rota|bitir|cikti]

KiCad'in kendi Python'u ile calistirin:  D:\\KiCad\\bin\\python.exe scripts\\uret.py hepsi
"""
import os
import sys
import subprocess
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tasarim as T

KICAD_BIN = r"D:\KiCad\bin"
CLI = os.path.join(KICAD_BIN, "kicad-cli.exe")
PY = os.path.join(KICAD_BIN, "python.exe")
FREEROUTING_JAR = r"D:\KiCad-araclar\freerouting-2.5.0.jar"
JAVA = r"D:\KiCad-araclar\jre\jdk-25.0.4.1+1-jre\bin\java.exe"
SCH = os.path.join(PROJ, T.PROJE + ".kicad_sch")
PCBF = os.path.join(PROJ, T.PROJE + ".kicad_pcb")
OUT = os.path.join(PROJ, "cikti")


def run(cmd, check=True, **kw):
    print(">", " ".join(cmd))
    r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        raise SystemExit("hata: %s (kod %d)" % (cmd[0], r.returncode))
    return r


def py(script, *args):
    run([PY, "-I", os.path.join(HERE, script)] + list(args), cwd=HERE)


def yerlesim():
    py("kutuphane.py")
    py("sema.py")
    os.makedirs(OUT, exist_ok=True)
    run([CLI, "sch", "erc", "--severity-all", "--exit-code-violations", "-o", os.path.join(OUT, "ERC_raporu.rpt"), SCH], check=False)
    run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", os.path.join(HERE, "_net.net"), SCH])
    py("netkontrol.py", os.path.join(HERE, "_net.net"))
    py("pcb.py", "dsn")


def rota(passes="60"):
    dsn = os.path.join(HERE, "_rota.dsn")
    ses = os.path.join(HERE, "_rota.ses")
    if os.path.exists(ses):
        os.remove(ses)
    # Not: freerouting-cli (native) 2.5.0 Windows'ta serilestirme hatasiyla takiliyor; jar + Java 25 kullaniliyor.
    with open(os.path.join(HERE, "_freerouting.log"), "w") as log:
        run([JAVA, "-jar", FREEROUTING_JAR, "--gui.enabled=false", "-de", dsn, "-do", ses,
             "--router.autorouter.max_passes=" + passes, "-l", "en"], cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
    if not os.path.exists(ses):
        raise SystemExit("SES uretilmedi, _freerouting.log'a bakin")


def bitir():
    py("pcb.py", "dsn")  # yonlendirmesiz temiz kart, sonra SES ice aktarilir
    py("bitir.py")


def cikti():
    os.makedirs(OUT, exist_ok=True)
    run([CLI, "sch", "erc", "--severity-all", "-o", os.path.join(OUT, "ERC_raporu.rpt"), SCH], check=False)
    run([CLI, "pcb", "drc", "--severity-all", "--schematic-parity", "-o", os.path.join(OUT, "DRC_raporu.rpt"), PCBF], check=False)
    run([CLI, "pcb", "drc", "--severity-all", "--schematic-parity", "--format", "json", "-o", os.path.join(HERE, "_drc.json"), PCBF], check=False)
    run([CLI, "pcb", "render", "--side", "top", "--quality", "high", "-w", "2400", "-h", "3100", "--background", "opaque",
         "-o", os.path.join(OUT, "ustten_render.png"), PCBF])
    run([CLI, "pcb", "render", "--side", "bottom", "--quality", "basic", "-w", "1600", "-h", "2100", "--background", "opaque",
         "-o", os.path.join(OUT, "alttan_render.png"), PCBF])
    run([CLI, "pcb", "render", "--side", "top", "--quality", "high", "-w", "2400", "-h", "1800", "--rotate", "-40,0,20",
         "--perspective", "--background", "opaque", "-o", os.path.join(OUT, "perspektif_render.png"), PCBF])
    # 1:1 montaj PDF'i (A4, olcekleme yok): sayfa 1 ust montaj, 2 ust bakir, 3 alt bakir
    run([CLI, "pcb", "export", "pdf", "--mode-multipage", "--layers", "F.Cu,B.Cu", "--common-layers", "Edge.Cuts,Dwgs.User",
         "--include-border-title", "--drill-shape-opt", "2", "-o", os.path.join(OUT, "bakir_katmanlari_1-1.pdf"), PCBF])
    run([CLI, "pcb", "export", "pdf", "--mode-single", "--layers", "F.Fab,F.SilkS,F.CrtYd,Edge.Cuts,Dwgs.User",
         "--include-border-title", "--drill-shape-opt", "2", "-o", os.path.join(OUT, "montaj_1-1.pdf"), PCBF])
    run([CLI, "sch", "export", "pdf", "-o", os.path.join(OUT, "sema.pdf"), SCH])
    gb = os.path.join(HERE, "_gerber")
    shutil.rmtree(gb, ignore_errors=True)
    os.makedirs(gb)
    run([CLI, "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
         "-o", gb + os.sep, PCBF])
    run([CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gb + os.sep, PCBF])
    zipf = os.path.join(OUT, "gerber_" + T.PROJE)
    if os.path.exists(zipf + ".zip"):
        os.remove(zipf + ".zip")
    shutil.make_archive(zipf, "zip", gb)
    run([CLI, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,${QUANTITY}", "--labels",
         "Referans,Deger,Footprint,Adet", "--group-by", "Value,Footprint", "--ref-range-delimiter", "",
         "-o", os.path.join(OUT, "BOM.csv"), SCH])


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if step in ("yerlesim", "hepsi"):
        yerlesim()
    if step in ("rota", "hepsi"):
        rota()
    if step in ("bitir", "hepsi"):
        bitir()
    if step in ("cikti", "hepsi"):
        cikti()
