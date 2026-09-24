#!/usr/bin/env python3

from pathlib import Path
import subprocess
import re

print("\033c", end="")

print("=" * 78)
print("PHASE 78.62 — FINALISATION k=8x8x8 À ecutrho=560 Ry")
print("=" * 78)
print("[INFO] MODE = DFT CONTRÔLÉ")
print("[INFO] Aucun recalcul de 4³–7³")
print("[INFO] Reprise exclusive de k=8x8x8")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print("[INFO] Timeout = 12 heures")
print("[INFO] Aucun fichier scientifique historique modifié")

BASE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_k_convergence/TiFeH2"
)

inp = BASE / "ecut140_rho560_k888.in"
out = BASE / "ecut140_rho560_k888_retry.out"

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

if not QE.exists():
    raise SystemExit(f"[ERROR] QE absent : {QE}")

if not inp.exists():
    raise SystemExit(f"[ERROR] Input absent : {inp}")

text = inp.read_text(errors="replace")

checks = {
    "ecutwfc=140": r"ecutwfc\s*=\s*140",
    "ecutrho=560": r"ecutrho\s*=\s*560",
    "nat=8": r"nat\s*=\s*8",
    "ntyp=3": r"ntyp\s*=\s*3",
    "nspin=2": r"nspin\s*=\s*2",
    "degauss=0.01": r"degauss\s*=\s*0.01",
    "k=8x8x8": r"K_POINTS\s+automatic\s*\n\s*8\s+8\s+8",
}

print()
print("===== 1. VALIDATION INPUT =====")
print("-" * 78)

for label, pattern in checks.items():
    ok = bool(re.search(pattern, text, re.I))
    print(f"{label:18} : {'OK' if ok else 'ABSENT'}")

if not all(re.search(p, text, re.I) for p in checks.values()):
    raise SystemExit("[ERROR] Input 8³ non conforme.")

print()
print("===== 2. EXÉCUTION UNIQUE 8³ =====")
print("-" * 78)

print("[RUN] k = 8x8x8")
print("[RUN] timeout = 12 h")
print(f"[RUN] output = {out}")

try:
    with out.open("w") as fout:
        proc = subprocess.run(
            [str(QE), "-in", str(inp)],
            stdout=fout,
            stderr=subprocess.STDOUT,
            cwd=BASE,
            timeout=12 * 3600,
        )

    rc = proc.returncode

except subprocess.TimeoutExpired:
    print("[ERROR] TIMEOUT après 12 h")
    raise SystemExit(2)

text = out.read_text(errors="replace")

energies = re.findall(
    r"!\s*total energy\s*=\s*"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
    text,
    re.I,
)

fermis = re.findall(
    r"the Fermi energy is\s*"
    r"([-+]?\d+(?:\.\d+)?)\s*eV",
    text,
    re.I,
)

accuracies = re.findall(
    r"estimated scf accuracy\s*<\s*"
    r"([0-9.Ee+-]+)\s*Ry",
    text,
    re.I,
)

print()
print("===== 3. RÉSULTAT =====")
print("-" * 78)

print(f"[RESULT] returncode = {rc}")
print(f"[RESULT] JOB DONE   = {'JOB DONE.' in text}")

if energies:
    print(f"[RESULT] E = {float(energies[-1]):.10f} Ry")
else:
    print("[WARN] Énergie finale non extraite")

if fermis:
    print(f"[RESULT] EF = {float(fermis[-1]):.6f} eV")
else:
    print("[WARN] EF non extrait")

if accuracies:
    print(
        f"[RESULT] SCF accuracy = "
        f"{float(accuracies[-1]):.3e} Ry"
    )

print()
print("=" * 78)
print("PHASE 78.62 TERMINÉE")
print("=" * 78)
