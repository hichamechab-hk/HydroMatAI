#!/usr/bin/env python3

import sys
import re
from pathlib import Path

# Nettoyage terminal sans dépendre de TERM
sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

# Détection volontairement permissive.
# On veut identifier toute ligne contenant :
#     k = ........ bands (ev):
#
# sans imposer un format particulier aux coordonnées.
HEADER_RE = re.compile(
    r"k\s*=\s*.*bands\s*\(ev\)",
    re.IGNORECASE
)

FERMI_RE = re.compile(
    r"the\s+Fermi\s+energy\s+is\s+([+-]?\d+(?:\.\d+)?)\s+ev",
    re.IGNORECASE
)

K_COORD_RE = re.compile(
    r"k\s*=\s*"
    r"([+-]?\d+(?:\.\d+)?)\s+"
    r"([+-]?\d+(?:\.\d+)?)\s+"
    r"([+-]?\d+(?:\.\d+)?)",
    re.IGNORECASE
)

def ffloat(x):
    return float(x.replace("D", "E").replace("d", "e"))

def parse_file(path):

    lines = path.read_text(errors="replace").splitlines()

    up_line = None
    down_line = None
    fermi_line = None
    ef = None

    for i, line in enumerate(lines):

        if "------ SPIN UP" in line:
            up_line = i

        if "------ SPIN DOWN" in line:
            down_line = i

        m = FERMI_RE.search(line)
        if m:
            fermi_line = i
            ef = ffloat(m.group(1))

    if up_line is None:
        raise RuntimeError("SPIN UP introuvable")

    if down_line is None:
        raise RuntimeError("SPIN DOWN introuvable")

    if fermi_line is None:
        raise RuntimeError("Fermi energy introuvable")

    # ---------------------------------------------------------------
    # Détection RAW de tous les headers
    # ---------------------------------------------------------------

    up_headers = []
    down_headers = []

    for i in range(up_line + 1, down_line):

        if HEADER_RE.search(lines[i]):
            up_headers.append(i)

    for i in range(down_line + 1, fermi_line):

        if HEADER_RE.search(lines[i]):
            down_headers.append(i)

    # ---------------------------------------------------------------
    # Extraction des coordonnées
    # ---------------------------------------------------------------

    def header_info(index):

        line = lines[index]

        m = K_COORD_RE.search(line)

        if m:
            k = tuple(ffloat(x) for x in m.groups())
        else:
            k = None

        return k

    # ---------------------------------------------------------------
    # Affichage détaillé des headers
    # ---------------------------------------------------------------

    print()
    print("[RAW HEADERS — SPIN UP]")

    for n, idx in enumerate(up_headers, start=1):

        k = header_info(idx)

        print(
            f"  {n:2d}  L{idx+1:4d}  "
            f"k={k}  "
            f"{lines[idx].strip()}"
        )

    print()
    print("[RAW HEADERS — SPIN DOWN]")

    for n, idx in enumerate(down_headers, start=1):

        k = header_info(idx)

        print(
            f"  {n:2d}  L{idx+1:4d}  "
            f"k={k}  "
            f"{lines[idx].strip()}"
        )

    return {
        "lines": len(lines),
        "up_line": up_line + 1,
        "down_line": down_line + 1,
        "fermi_line": fermi_line + 1,
        "ef": ef,
        "up_headers": up_headers,
        "down_headers": down_headers,
    }


print("=" * 78)
print("PHASE 78.86 — RAW BAND HEADER DETECTION")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

for grid, path in FILES.items():

    print("=" * 78)
    print(f"PHASE 78.86 — {grid}³")
    print("=" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(path.read_text(errors='replace').splitlines())}")
    print(f"[INFO] Octets  : {path.stat().st_size}")

    try:
        r = parse_file(path)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        continue

    print()
    print("[SECTIONS]")
    print(f"SPIN UP   : L{r['up_line']}")
    print(f"SPIN DOWN : L{r['down_line']}")
    print(f"FERMI     : L{r['fermi_line']}")
    print(f"EF        : {r['ef']:.6f} eV")

    expected_k = 30 if grid == 4 else 39

    print()
    print("[VALIDATION DES HEADERS]")
    print(f"UP   : {len(r['up_headers'])} / {expected_k}")
    print(f"DOWN : {len(r['down_headers'])} / {expected_k}")

    if len(r["up_headers"]) == expected_k:
        print("[OK] Tous les headers UP détectés.")
    else:
        print("[WARN] Headers UP incomplets.")

    if len(r["down_headers"]) == expected_k:
        print("[OK] Tous les headers DOWN détectés.")
    else:
        print("[WARN] Headers DOWN incomplets.")

print()
print("=" * 78)
print("PHASE 78.86 — FIN")
print("=" * 78)
