"""Full pipeline:  python build.py [all|place|route|finish|outputs|viewer]

Run it with KiCad's own Python:  D:\\KiCad\\bin\\python.exe scripts\\build.py all
"""
import os
import sys
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import design as D

# Tool locations (portable installs on this machine)
KICAD_BIN = r"D:\KiCad\bin"
CLI = os.path.join(KICAD_BIN, "kicad-cli.exe")
PY = os.path.join(KICAD_BIN, "python.exe")
FREEROUTING_JAR = r"D:\KiCad-araclar\freerouting-2.5.0.jar"
JAVA = r"D:\KiCad-araclar\jre\jdk-25.0.4.1+1-jre\bin\java.exe"

SCH = os.path.join(PROJ, D.PROJECT + ".kicad_sch")
PCBF = os.path.join(PROJ, D.PROJECT + ".kicad_pcb")
OUT = os.path.join(PROJ, "output")


def run(cmd, check=True, **kw):
    print(">", " ".join(cmd))
    r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        raise SystemExit("failed: %s (exit %d)" % (cmd[0], r.returncode))
    return r


def py(script, *args):
    run([PY, "-I", os.path.join(HERE, script)] + list(args), cwd=HERE)


def place():
    py("library.py")
    py("schematic.py")
    os.makedirs(OUT, exist_ok=True)
    run([CLI, "sch", "erc", "--severity-all", "-o", os.path.join(OUT, "ERC_report.rpt"), SCH], check=False)
    run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", os.path.join(HERE, "_net.net"), SCH])
    py("netcheck.py", os.path.join(HERE, "_net.net"))
    py("pcb.py", "dsn")


def route(passes="60"):
    dsn = os.path.join(HERE, "_route.dsn")
    ses = os.path.join(HERE, "_route.ses")
    if os.path.exists(ses):
        os.remove(ses)
    # Note: the native freerouting-cli 2.5.0 hangs on Windows (serialization error); the jar + Java 25 works.
    with open(os.path.join(HERE, "_freerouting.log"), "w") as log:
        run([JAVA, "-jar", FREEROUTING_JAR, "--gui.enabled=false", "-de", dsn, "-do", ses,
             "--router.autorouter.max_passes=" + passes, "-l", "en"], cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
    if not os.path.exists(ses):
        raise SystemExit("no SES produced, see _freerouting.log")


def finish():
    py("pcb.py", "dsn")  # clean unrouted board, then the SES is imported on top of it
    py("finish.py")


def outputs():
    os.makedirs(OUT, exist_ok=True)
    run([CLI, "sch", "erc", "--severity-all", "-o", os.path.join(OUT, "ERC_report.rpt"), SCH], check=False)
    run([CLI, "pcb", "drc", "--severity-all", "--schematic-parity", "-o", os.path.join(OUT, "DRC_report.rpt"), PCBF], check=False)
    run([CLI, "pcb", "render", "--side", "top", "--quality", "high", "-w", "2400", "-h", "3400", "--background", "opaque",
         "-o", os.path.join(OUT, "render_top.png"), PCBF])
    run([CLI, "pcb", "render", "--side", "bottom", "--quality", "basic", "-w", "1600", "-h", "2300", "--background", "opaque",
         "-o", os.path.join(OUT, "render_bottom.png"), PCBF])
    run([CLI, "pcb", "render", "--side", "top", "--quality", "high", "-w", "2400", "-h", "1800", "--rotate", "-40,0,20",
         "--perspective", "--background", "opaque", "-o", os.path.join(OUT, "render_perspective.png"), PCBF])
    # 1:1 PDFs on A4, no scaling
    run([CLI, "pcb", "export", "pdf", "--mode-single", "--layers", "F.Fab,F.SilkS,F.CrtYd,Edge.Cuts,Dwgs.User",
         "--include-border-title", "--drill-shape-opt", "2", "-o", os.path.join(OUT, "assembly_1to1.pdf"), PCBF])
    run([CLI, "pcb", "export", "pdf", "--mode-multipage", "--layers", "F.Cu,B.Cu", "--common-layers", "Edge.Cuts,Dwgs.User",
         "--include-border-title", "--drill-shape-opt", "2", "-o", os.path.join(OUT, "copper_layers_1to1.pdf"), PCBF])
    run([CLI, "sch", "export", "pdf", "-o", os.path.join(OUT, "schematic.pdf"), SCH])
    gb = os.path.join(HERE, "_gerber")
    shutil.rmtree(gb, ignore_errors=True)
    os.makedirs(gb)
    run([CLI, "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
         "-o", gb + os.sep, PCBF])
    run([CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gb + os.sep, PCBF])
    zipf = os.path.join(OUT, "gerbers_" + D.PROJECT)
    if os.path.exists(zipf + ".zip"):
        os.remove(zipf + ".zip")
    shutil.make_archive(zipf, "zip", gb)
    run([CLI, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,${QUANTITY}", "--labels",
         "Reference,Value,Footprint,Qty", "--group-by", "Value,Footprint", "--ref-range-delimiter", "",
         "-o", os.path.join(OUT, "BOM.csv"), SCH])


def viewer():
    py("export_viewer.py")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("place", "all"):
        place()
    if step in ("route", "all"):
        route()
    if step in ("finish", "all"):
        finish()
    if step in ("outputs", "all"):
        outputs()
    if step in ("viewer", "all"):
        viewer()
