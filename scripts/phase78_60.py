#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import shutil

print("\033c", end="")

print("=" * 78)
print("PHASE 78.60 — AUDIT CONTRÔLÉ ecutrho / TiFeH2")
print("=" * 78)
print("[INFO] MODE = DFT CONTRÔLÉ")
print("[INFO] ecutwfc FIXE = 140 Ry")
print("[INFO] K-POINTS FIXES = 7x7x7")
print("[INFO] Variable unique = ecutrho")
print("[INFO] Aucun fichier scientifique antérieur modifié")

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")
BASE = Path("/home/hk/HydroMatAI/calculations/phase78_60_convergence/TiFeH2")
BASE.mkdir(parents=True, exist_ok=True)

SOURCE_IN = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_55_convergence/TiFeH2/ecut140_k777.in"
)

CUTOFFS = [240, 280, 320, 400, 560]

RY_TO_EV = 13.605693009
NAT = 8

if not QE.exists():
    raise SystemExit(f"[ERROR] pw.x absent : {QE}")

if not SOURCE_IN.exists():
    raise SystemExit(f"[ERROR] Input source absent : {SOURCE_IN}")

print()
print("===== 1. VÉRIFICATIONS =====")
print("-" * 78)
print(f"[OK] pw.x : {QE}")
print(f"[OK] source : {SOURCE_IN}")
print(f"[OK] dossier isolé : {BASE}")

source = SOURCE_IN.read_text(errors="replace")

# ----------------------------------------------------------------------
# Vérification source
# ----------------------------------------------------------------------

print()
print("===== 2. INPUT DE RÉFÉRENCE =====")
print("-" * 78)

checks = {
    "ecutwfc": r"^\s*ecutwfc\s*=\s*([0-9.]+)",
    "ecutrho": r"^\s*ecutrho\s*=\s*([0-9.]+)",
    "nspin": r"^\s*nspin\s*=\s*([0-9]+)",
    "nat": r"^\s*nat\s*=\s*([0-9]+)",
    "ntyp": r"^\s*ntyp\s*=\s*([0-9]+)",
    "degauss": r"^\s*degauss\s*=\s*([0-9.]+)",
}

for name, pattern in checks.items():
    m = re.search(pattern, source, re.I | re.M)
    print(f"{name:10} = {m.group(1) if m else 'ABSENT'}")

if not re.search(r"ecutwfc\s*=\s*140", source, re.I):
    raise SystemExit("[ERROR] ecutwfc source différent de 140 Ry")

if not re.search(r"K_POINTS\s+automatic", source, re.I):
    raise SystemExit("[ERROR] K_POINTS automatic absent")

m = re.search(
    r"K_POINTS\s+automatic\s*\n\s*"
    r"(\d+)\s+(\d+)\s+(\d+)",
    source,
    re.I,
)

if not m:
    raise SystemExit("[ERROR] grille K non détectée")

kgrid = tuple(map(int, m.groups()))

if kgrid != (7, 7, 7):
    raise SystemExit(
        f"[ERROR] grille source = {kgrid}, attendu (7,7,7)"
    )

print("[OK] ecutwfc = 140 Ry")
print("[OK] grille = 7x7x7")


# ----------------------------------------------------------------------
# Extraction pseudo_dir correcte
# ----------------------------------------------------------------------

print()
print("===== 3. PSEUDOPOTENTIELS =====")
print("-" * 78)

pseudo_match = re.search(
    r"pseudo_dir\s*=\s*['\"]([^'\"]+)['\"]",
    source,
    re.I,
)

if pseudo_match:
    pseudo_dir = Path(pseudo_match.group(1))
    print(f"[OK] pseudo_dir = {pseudo_dir}")
else:
    pseudo_dir = None
    print("[WARN] pseudo_dir non extrait de l'input")

pseudo_files = re.findall(
    r"^\s*(\S+)\s+\d+\.\d+\s+(\S+)",
    source,
    re.M,
)

print("[INFO] Espèces/pseudos détectés depuis ATOMIC_SPECIES :")

species_block = re.search(
    r"ATOMIC_SPECIES\s*\n(.*?)(?:\n[A-Z_]+|\Z)",
    source,
    re.S | re.I,
)

pseudo_names = []

if species_block:
    for line in species_block.group(1).splitlines():
        parts = line.split()
        if len(parts) >= 3:
            print("  ", " ".join(parts))
            pseudo_names.append(parts[2])

if pseudo_dir and pseudo_dir.exists():
    print()
    print("[INFO] Audit léger des fichiers UPF")

    for pseudo in pseudo_names:
        path = pseudo_dir / pseudo

        if not path.exists():
            print(f"[WARN] absent : {path}")
            continue

        text = path.read_text(errors="replace")

        print(f"\n--- {pseudo} ---")
        print(f"[OK] {path}")

        for pattern, label in [
            (r"cutoff_wfc\s*=\s*['\"]?([0-9.]+)", "cutoff_wfc"),
            (r"cutoff_rho\s*=\s*['\"]?([0-9.]+)", "cutoff_rho"),
        ]:
            vals = re.findall(pattern, text, re.I)

            if vals:
                print(f"{label:12} = {vals[-1]}")
            else:
                print(f"{label:12} = non indiqué")
else:
    print("[WARN] pseudo_dir non accessible depuis cet input")


# ----------------------------------------------------------------------
# Création des inputs isolés
# ----------------------------------------------------------------------

print()
print("===== 4. PRÉPARATION DES CINQ CALCULS =====")
print("-" * 78)

inputs = []

for cutoff in CUTOFFS:

    name = f"ecut140_rho{cutoff}_k777"
    inp = BASE / f"{name}.in"
    out = BASE / f"{name}.out"

    text = source

    text = re.sub(
        r"^\s*ecutrho\s*=\s*[0-9.]+",
        f"    ecutrho = {cutoff}",
        text,
        flags=re.I | re.M,
    )

    text = re.sub(
        r"prefix\s*=\s*['\"][^'\"]+['\"]",
        f"prefix = '{name}'",
        text,
        flags=re.I,
    )

    inp.write_text(text)

    inputs.append((cutoff, inp, out))

    print(
        f"[OK] {name} | "
        f"ecutwfc=140 | ecutrho={cutoff} | k=7x7x7"
    )


# ----------------------------------------------------------------------
# Lancement QE
# ----------------------------------------------------------------------

print()
print("===== 5. EXÉCUTION QE =====")
print("-" * 78)

results = []

for cutoff, inp, out in inputs:

    print()
    print(f"[RUN] ecutrho = {cutoff} Ry")

    command = [
        str(QE),
        "-in",
        str(inp),
    ]

    try:
        with out.open("w") as fout:
            proc = subprocess.run(
                command,
                stdout=fout,
                stderr=subprocess.STDOUT,
                cwd=BASE,
                timeout=6 * 3600,
            )

        rc = proc.returncode

    except subprocess.TimeoutExpired:
        print("[ERROR] TIMEOUT")
        results.append({
            "ecutrho": cutoff,
            "energy": None,
            "fermi": None,
            "job_done": False,
            "returncode": "TIMEOUT",
        })
        continue

    text = out.read_text(errors="replace")

    job_done = "JOB DONE." in text

    energy_matches = re.findall(
        r"!\s*total energy\s*=\s*"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*Ry",
        text,
        re.I,
    )

    fermi_matches = re.findall(
        r"the Fermi energy is\s*"
        r"([-+]?\d+(?:\.\d+)?)\s*eV",
        text,
        re.I,
    )

    energy = float(energy_matches[-1]) if energy_matches else None
    fermi = float(fermi_matches[-1]) if fermi_matches else None

    accuracy_matches = re.findall(
        r"estimated scf accuracy\s*<\s*"
        r"([0-9.Ee+-]+)\s*Ry",
        text,
        re.I,
    )

    accuracy = (
        float(accuracy_matches[-1])
        if accuracy_matches
        else None
    )

    print(f"[RESULT] returncode = {rc}")
    print(f"[RESULT] JOB DONE   = {job_done}")

    if energy is not None:
        print(f"[RESULT] E          = {energy:.10f} Ry")
    else:
        print("[WARN] énergie absente")

    if fermi is not None:
        print(f"[RESULT] EF         = {fermi:.6f} eV")

    if accuracy is not None:
        print(
            f"[RESULT] SCF accuracy = "
            f"{accuracy:.3e} Ry"
        )

    results.append({
        "ecutrho": cutoff,
        "energy": energy,
        "fermi": fermi,
        "accuracy": accuracy,
        "job_done": job_done,
        "returncode": rc,
    })


# ----------------------------------------------------------------------
# Tableau énergétique
# ----------------------------------------------------------------------

print()
print("===== 6. COMPARAISON ecutrho =====")
print("-" * 78)

print(
    f"{'ecutrho':>8} | "
    f"{'E (Ry)':>16} | "
    f"{'ΔE/at (meV)':>15} | "
    f"{'EF (eV)':>10} | "
    f"{'JOB':>5}"
)

print("-" * 78)

reference_energy = None
previous = None

for r in results:

    e = r["energy"]

    if e is None:
        delta = None
    elif reference_energy is None:
        reference_energy = e
        delta = 0.0
    else:
        delta = (
            (e - reference_energy)
            * RY_TO_EV
            * 1000
            / NAT
        )

    if e is not None and previous is not None:
        successive = (
            (e - previous)
            * RY_TO_EV
            * 1000
            / NAT
        )
    else:
        successive = None

    delta_txt = (
        f"{delta:+.6f}"
        if delta is not None
        else "ABSENT"
    )

    print(
        f"{r['ecutrho']:8.0f} | "
        f"{e:16.10f} | "
        f"{delta_txt:>15} | "
        f"{r['fermi'] if r['fermi'] is not None else 'ABSENT':>10} | "
        f"{str(r['job_done']):>5}"
    )

    if e is not None:
        previous = e


# ----------------------------------------------------------------------
# Audit convergence
# ----------------------------------------------------------------------

print()
print("===== 7. TEST DE STABILITÉ =====")
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
            f"{a['ecutrho']} → {b['ecutrho']} Ry : "
            f"{delta:+.6f} meV/atome"
        )

        if abs(delta) <= 1.0:
            print("    [OK] |ΔE| <= 1 meV/atome")
        else:
            print("    [INFO] |ΔE| > 1 meV/atome")


# ----------------------------------------------------------------------
# Conclusion
# ----------------------------------------------------------------------

print()
print("===== 8. CONCLUSION AUTOMATIQUE =====")
print("-" * 78)

if len(valid) == len(CUTOFFS):
    print("[OK] Les cinq calculs ecutrho sont terminés.")
else:
    print(
        f"[WARN] {len(valid)}/{len(CUTOFFS)} "
        "calculs possèdent une énergie exploitable."
    )

print()
print("[IMPORTANT]")
print("- Cette phase ne modifie aucun résultat historique.")
print("- Les calculs sont isolés dans phase78_60_convergence.")
print("- ecutwfc reste fixé à 140 Ry.")
print("- k reste fixé à 7x7x7.")
print("- Seul ecutrho varie.")
print("- Aucune conclusion sur la convergence k n'est tirée ici.")

print()
print("=" * 78)
print("PHASE 78.60 TERMINÉE")
print("=" * 78)
