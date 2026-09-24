#!/usr/bin/env python3

from pathlib import Path
import subprocess
import re
import shutil

print("=" * 78)
print("PHASE 78.63 — CALCUL ROBUSTE k=8x8x8 À ecutrho=560 Ry")
print("=" * 78)
print("[INFO] MODE = DFT CONTRÔLÉ")
print("[INFO] Calcul UNIQUE : 8x8x8")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] ecutrho = 560 Ry")
print("[INFO] Aucun recalcul de 4³–7³")
print("[INFO] Aucun résultat historique modifié")

BASE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_convergence/TiFeH2"
)

INP = BASE / "ecut140_rho560_k888.in"
OUT = BASE / "ecut140_rho560_k888_phase78_63.out"

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

if not QE.exists():
    raise SystemExit(f"[ERROR] QE absent : {QE}")

if not INP.exists():
    raise SystemExit(f"[ERROR] Input absent : {INP}")

text = INP.read_text(errors="replace")

checks = {
    "ecutwfc": r"ecutwfc\s*=\s*140",
    "ecutrho": r"ecutrho\s*=\s*560",
    "nat": r"nat\s*=\s*8",
    "ntyp": r"ntyp\s*=\s*3",
    "nspin": r"nspin\s*=\s*2",
    "degauss": r"degauss\s*=\s*0.01",
    "k888": r"K_POINTS\s+automatic\s*\n\s*8\s+8\s+8",
}

print()
print("===== 1. VALIDATION INPUT =====")
print("-" * 78)

for name, pattern in checks.items():
    ok = bool(re.search(pattern, text, re.I))
    print(f"{name:12} : {'OK' if ok else 'ABSENT'}")

if not all(re.search(p, text, re.I) for p in checks.values()):
    raise SystemExit("[ERROR] Input 8³ non conforme.")

print()
print("===== 2. INVENTAIRE MPI =====")
print("-" * 78)

mpirun = shutil.which("mpirun")

if mpirun:
    print(f"[OK] mpirun = {mpirun}")
else:
    print("[WARN] mpirun absent ; exécution séquentielle")

print()
print("===== 3. EXÉCUTION =====")
print("-" * 78)

# Exécution directe QE, sans pipe stdout/stderr.
# Cela évite de reproduire le mécanisme susceptible de provoquer
# le Broken pipe observé précédemment.

if mpirun:
    command = [
        mpirun,
        "-np", "1",
        str(QE),
        "-in", str(INP),
    ]
else:
    command = [
        str(QE),
        "-in", str(INP),
    ]

print("[RUN]", " ".join(command))
print("[RUN] timeout = 12 h")
print(f"[RUN] output = {OUT}")

try:
    with OUT.open("w") as fout:
        proc = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=fout,
            stderr=subprocess.STDOUT,
            cwd=BASE,
            timeout=12 * 3600,
        )

    rc = proc.returncode

except subprocess.TimeoutExpired:
    print("[ERROR] TIMEOUT après 12 h")
    raise SystemExit(2)

except Exception as exc:
    print(f"[ERROR] Exception : {exc}")
    raise SystemExit(3)

text = OUT.read_text(errors="replace")

print()
print("===== 4. EXTRACTION =====")
print("-" * 78)

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

kpoints = re.findall(
    r"number of k points\s*=\s*(\d+)",
    text,
    re.I,
)

print(f"[RESULT] returncode = {rc}")
print(f"[RESULT] JOB DONE   = {'JOB DONE.' in text}")

if energies:
    print(f"[RESULT] E = {float(energies[-1]):.10f} Ry")
else:
    print("[WARN] Énergie finale absente")

if fermis:
    print(f"[RESULT] EF = {float(fermis[-1]):.6f} eV")
else:
    print("[WARN] Fermi absent")

if accuracies:
    print(
        f"[RESULT] SCF accuracy = "
        f"{float(accuracies[-1]):.3e} Ry"
    )

if kpoints:
    print(f"[RESULT] k-points QE = {kpoints[-1]}")

print()
print("===== 5. DIAGNOSTIC ERREURS =====")
print("-" * 78)

errors = [
    line for line in text.splitlines()
    if any(
        key in line.lower()
        for key in [
            "error",
            "fatal",
            "abort",
            "broken pipe",
            "segmentation",
        ]
    )
]

if errors:
    for line in errors[-20:]:
        print(line)
else:
    print("[OK] Aucune erreur explicite détectée.")

print()
print("===== 6. FIN DU FICHIER =====")
print("-" * 78)

for line in text.splitlines()[-20:]:
    print(line)

print()
print("=" * 78)
print("PHASE 78.63 TERMINÉE")
print("=" * 78)
