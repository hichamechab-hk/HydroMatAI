#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess

print("\033c", end="")

print("=" * 78)
print("PHASE 78.61 — CONVERGENCE k À ecutrho=560 Ry")
print("=" * 78)
print("[INFO] MODE = DFT CONTRÔLÉ")
print("[INFO] ecutwfc = 140 Ry FIXE")
print("[INFO] ecutrho = 560 Ry FIXE")
print("[INFO] VARIABLE UNIQUE = MAILLAGE k")
print("[INFO] GRILLES = 4x4x4 → 8x8x8")
print("[INFO] Aucun résultat historique modifié")

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")

BASE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_convergence/TiFeH2"
)
BASE.mkdir(parents=True, exist_ok=True)

SOURCE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_55_convergence/TiFeH2/ecut140_k777.in"
)

GRIDS = [4, 5, 6, 7, 8]

RY_TO_EV = 13.605693009
NAT = 8

if not QE.exists():
    raise SystemExit(f"[ERROR] pw.x absent : {QE}")

if not SOURCE.exists():
    raise SystemExit(f"[ERROR] Input source absent : {SOURCE}")

source = SOURCE.read_text(errors="replace")

print()
print("===== 1. VALIDATION DE LA BASE =====")
print("-" * 78)

required = {
    "ecutwfc": r"ecutwfc\s*=\s*140",
    "ecutrho": r"ecutrho\s*=\s*240",
    "nspin": r"nspin\s*=\s*2",
    "nat": r"nat\s*=\s*8",
    "ntyp": r"ntyp\s*=\s*3",
    "degauss": r"degauss\s*=\s*0.01",
}

for name, pattern in required.items():
    ok = bool(re.search(pattern, source, re.I))
    print(f"{name:10} : {'OK' if ok else 'ABSENT/DIFF'}")

if not re.search(r"ecutwfc\s*=\s*140", source, re.I):
    raise SystemExit("[ERROR] ecutwfc != 140")

if not re.search(r"ecutrho\s*=\s*240", source, re.I):
    raise SystemExit("[ERROR] source inattendue")

print("[OK] Source compatible.")
print("[INFO] ecutrho sera remplacé par 560 Ry.")


print()
print("===== 2. PRÉPARATION DES INPUTS =====")
print("-" * 78)

jobs = []

for k in GRIDS:

    name = f"ecut140_rho560_k{k}{k}{k}"

    inp = BASE / f"{name}.in"
    out = BASE / f"{name}.out"

    text = source

    text = re.sub(
        r"^\s*ecutrho\s*=\s*[0-9.]+",
        "    ecutrho = 560",
        text,
        flags=re.I | re.M,
    )

    text = re.sub(
        r"prefix\s*=\s*['\"][^'\"]+['\"]",
        f"prefix = '{name}'",
        text,
        flags=re.I,
    )

    text = re.sub(
        r"(K_POINTS\s+automatic\s*\n\s*)"
        r"\d+\s+\d+\s+\d+(\s+0\s+0\s+0)",
        rf"\g<1>{k} {k} {k}\g<2>",
        text,
        flags=re.I,
    )

    inp.write_text(text)

    jobs.append((k, inp, out))

    print(
        f"[OK] {name} | "
        f"ecutwfc=140 | ecutrho=560 | k={k}x{k}x{k}"
    )


print()
print("===== 3. VÉRIFICATION DES INPUTS =====")
print("-" * 78)

for k, inp, out in jobs:

    text = inp.read_text(errors="replace")

    ew = re.search(r"ecutwfc\s*=\s*([0-9.]+)", text, re.I)
    er = re.search(r"ecutrho\s*=\s*([0-9.]+)", text, re.I)
    kp = re.search(
        r"K_POINTS\s+automatic\s*\n\s*"
        r"(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.I,
    )

    print(
        f"{k}³ | "
        f"ecutwfc={ew.group(1) if ew else '?'} | "
        f"ecutrho={er.group(1) if er else '?'} | "
        f"k={kp.groups() if kp else '?'}"
    )


print()
print("===== 4. EXÉCUTION QE =====")
print("-" * 78)

results = []

for k, inp, out in jobs:

    print()
    print(f"[RUN] k = {k}x{k}x{k}")

    try:
        with out.open("w") as fout:
            proc = subprocess.run(
                [str(QE), "-in", str(inp)],
                stdout=fout,
                stderr=subprocess.STDOUT,
                cwd=BASE,
                timeout=6 * 3600,
            )

        rc = proc.returncode

    except subprocess.TimeoutExpired:

        print("[ERROR] TIMEOUT")

        results.append({
            "k": k,
            "energy": None,
            "fermi": None,
            "accuracy": None,
            "job_done": False,
            "rc": "TIMEOUT",
        })

        continue

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

    energy = float(energies[-1]) if energies else None
    fermi = float(fermis[-1]) if fermis else None
    accuracy = float(accuracies[-1]) if accuracies else None

    job_done = "JOB DONE." in text

    print(f"[RESULT] returncode = {rc}")
    print(f"[RESULT] JOB DONE   = {job_done}")

    if energy is not None:
        print(f"[RESULT] E          = {energy:.10f} Ry")

    if fermi is not None:
        print(f"[RESULT] EF         = {fermi:.6f} eV")

    if accuracy is not None:
        print(f"[RESULT] SCF accuracy = {accuracy:.3e} Ry")

    results.append({
        "k": k,
        "energy": energy,
        "fermi": fermi,
        "accuracy": accuracy,
        "job_done": job_done,
        "rc": rc,
    })


print()
print("===== 5. TABLEAU DE CONVERGENCE =====")
print("-" * 78)

print(
    f"{'k':>5} | "
    f"{'E (Ry)':>16} | "
    f"{'ΔE précédent':>17} | "
    f"{'ΔE/at (meV)':>15} | "
    f"{'EF (eV)':>10} | "
    f"{'JOB':>5}"
)

print("-" * 78)

previous_energy = None

for r in results:

    e = r["energy"]

    if e is None:
        print(
            f"{r['k']}³ | "
            f"{'ABSENT':>16} | "
            f"{'ABSENT':>17}"
        )
        continue

    if previous_energy is None:
        delta_ry = None
        delta_mev = None
    else:
        delta_ry = e - previous_energy
        delta_mev = (
            delta_ry * RY_TO_EV * 1000 / NAT
        )

    d1 = (
        f"{delta_ry:+.10f} Ry"
        if delta_ry is not None
        else "REFERENCE"
    )

    d2 = (
        f"{delta_mev:+.6f}"
        if delta_mev is not None
        else "---"
    )

    ef = (
        f"{r['fermi']:.6f}"
        if r["fermi"] is not None
        else "ABSENT"
    )

    print(
        f"{r['k']:>5} | "
        f"{e:16.10f} | "
        f"{d1:>17} | "
        f"{d2:>15} | "
        f"{ef:>10} | "
        f"{str(r['job_done']):>5}"
    )

    previous_energy = e


print()
print("===== 6. TEST DU CRITÈRE 1 meV/ATOME =====")
print("-" * 78)

valid = [r for r in results if r["energy"] is not None]

if len(valid) >= 2:

    for a, b in zip(valid[:-1], valid[1:]):

        delta = (
            (b["energy"] - a["energy"])
            * RY_TO_EV
            * 1000
            / NAT
        )

        print(
            f"{a['k']}³ → {b['k']}³ : "
            f"{delta:+.6f} meV/atome"
        )

        if abs(delta) <= 1.0:
            print("    [OK] critère <= 1 meV/atome")
        else:
            print("    [NON] critère > 1 meV/atome")


print()
print("===== 7. RANGE GLOBAL =====")
print("-" * 78)

if valid:

    energies = [r["energy"] for r in valid]

    emin = min(energies)
    emax = max(energies)

    spread = (
        (emax - emin)
        * RY_TO_EV
        * 1000
        / NAT
    )

    imin = energies.index(emin)
    imax = energies.index(emax)

    print(
        f"Minimum observé : "
        f"k={valid[imin]['k']}³ | {emin:.10f} Ry"
    )

    print(
        f"Maximum observé : "
        f"k={valid[imax]['k']}³ | {emax:.10f} Ry"
    )

    print(
        f"Étendue totale : "
        f"{spread:.6f} meV/atome"
    )


print()
print("===== 8. DIAGNOSTIC =====")
print("-" * 78)

if len(valid) == len(GRIDS):
    print("[OK] 5/5 calculs terminés avec énergie exploitable.")
else:
    print(
        f"[WARN] {len(valid)}/{len(GRIDS)} "
        "calculs exploitables."
    )

print()
print("[IMPORTANT]")
print("Cette phase isole le maillage k avec ecutrho=560 Ry.")
print("Le résultat doit être comparé à la série 240 Ry,")
print("mais les deux séries ne doivent pas être mélangées.")
print("Aucune grille n'est déclarée convergée automatiquement.")

print()
print("=" * 78)
print("PHASE 78.61 TERMINÉE")
print("=" * 78)
