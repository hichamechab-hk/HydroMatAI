#!/usr/bin/env python3

import re
from pathlib import Path

print("\033c", end="")

print("=" * 78)
print("PHASE 78.57 — AUDIT ÉNERGÉTIQUE QE / SMEARING / OCCUPATIONS")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Analyse des calculs 140 Ry / k = 4 à 8")

ROOTS = [
    Path("/home/hk/HydroMatAI/calculations/phase78_50_convergence/TiFeH2"),
    Path("/home/hk/HydroMatAI/calculations/phase78_52_convergence/TiFeH2"),
    Path("/home/hk/HydroMatAI/calculations/phase78_53_convergence/TiFeH2"),
    Path("/home/hk/HydroMatAI/calculations/phase78_55_convergence/TiFeH2"),
]

TARGETS = {
    "4x4x4": None,
    "5x5x5": None,
    "6x6x6": None,
    "7x7x7": None,
    "8x8x8": None,
}


def find_output(pattern):
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.glob(pattern):
            if p.is_file():
                return p
    return None


TARGETS["4x4x4"] = find_output("ecut140_k444.out")
TARGETS["5x5x5"] = find_output("ecut140_k555.out")
TARGETS["6x6x6"] = find_output("ecut140_k666.out")
TARGETS["7x7x7"] = find_output("ecut140_k777.out")
TARGETS["8x8x8"] = find_output("ecut140_k888.out")


def last_float(pattern, text, flags=re.I | re.M):
    matches = re.findall(pattern, text, flags)
    if not matches:
        return None
    value = matches[-1]
    if isinstance(value, tuple):
        value = value[-1]
    try:
        return float(value)
    except Exception:
        return None


def all_floats(pattern, text, flags=re.I | re.M):
    vals = []
    for m in re.findall(pattern, text, flags):
        if isinstance(m, tuple):
            m = m[-1]
        try:
            vals.append(float(m))
        except Exception:
            pass
    return vals


def parse_file(path):
    text = path.read_text(errors="replace")

    result = {
        "path": str(path),
        "job_done": "JOB DONE" in text,
        "energy": last_float(
            r"!\s+total energy\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
            text,
        ),
        "fermi": last_float(
            r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
            text,
        ),
        "smearing": last_float(
            r"smearing contrib\.\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
            text,
        ),
        "entropy": last_float(
            r"one-electron contribution\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
            text,
        ),
        "estimated_accuracy": last_float(
            r"estimated scf accuracy\s*<\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
            text,
        ),
    }

    # Paramètres QE
    result["ecutwfc"] = last_float(
        r"ecutwfc\s*=\s*([-+]?\d+(?:\.\d+)?)", text
    )
    result["ecutrho"] = last_float(
        r"ecutrho\s*=\s*([-+]?\d+(?:\.\d+)?)", text
    )
    result["degauss"] = last_float(
        r"degauss\s*=\s*([-+]?\d+(?:\.\d+)?)", text
    )

    m = re.search(
        r"smearing\s*=\s*['\"]?([A-Za-z0-9_-]+)",
        text,
        re.I,
    )
    result["smearing_type"] = m.group(1) if m else None

    m = re.search(
        r"occupations\s*=\s*['\"]?([A-Za-z0-9_-]+)",
        text,
        re.I,
    )
    result["occupations"] = m.group(1) if m else None

    # Contributions énergétiques : dernière occurrence.
    patterns = {
        "one_electron": r"one-electron contribution\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
        "hartree": r"hartree contribution\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
        "xc": r"xc contribution\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
        "ewald": r"ewald contribution\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
        "smearing_contrib": r"smearing contrib\.\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    }

    for key, pattern in patterns.items():
        result[key] = last_float(pattern, text)

    # Nombre d'itérations SCF.
    iter_matches = re.findall(
        r"iteration\s*#\s*(\d+)",
        text,
        re.I,
    )
    result["scf_iterations"] = (
        max(map(int, iter_matches)) if iter_matches else None
    )

    # Nombre de lignes "estimated scf accuracy".
    result["accuracy_count"] = len(
        re.findall(r"estimated scf accuracy", text, re.I)
    )

    # Nombre de blocs Fermi.
    result["fermi_count"] = len(
        re.findall(r"the Fermi energy is", text, re.I)
    )

    return result


print()
print("===== 1. INVENTAIRE DES SORTIES =====")
print("-" * 78)

data = {}

for k, path in TARGETS.items():
    if path is None:
        print(f"[WARN] {k:>6} : sortie introuvable")
        continue

    print(f"[OK]   {k:>6} : {path}")
    data[k] = parse_file(path)

print()
print("===== 2. PARAMÈTRES QE =====")
print("-" * 78)

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    print(
        f"{k:>6} | "
        f"ecutwfc={d['ecutwfc']} Ry | "
        f"ecutrho={d['ecutrho']} Ry | "
        f"degauss={d['degauss']} Ry | "
        f"occ={d['occupations']} | "
        f"smearing={d['smearing_type']}"
    )

print()
print("===== 3. ÉNERGIE / FERMI / CONVERGENCE SCF =====")
print("-" * 78)

print(
    f"{'K':>8} "
    f"{'E(Ry)':>18} "
    f"{'EF(eV)':>12} "
    f"{'SCF':>6} "
    f"{'JOB':>6}"
)

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    print(
        f"{k:>8} "
        f"{d['energy'] if d['energy'] is not None else float('nan'):18.8f} "
        f"{d['fermi'] if d['fermi'] is not None else float('nan'):12.5f} "
        f"{str(d['scf_iterations']):>6} "
        f"{'DONE' if d['job_done'] else 'FAIL':>6}"
    )

print()
print("===== 4. CONTRIBUTIONS ÉNERGÉTIQUES QE =====")
print("-" * 78)

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    print()
    print(f"[{k}]")

    for label, key in [
        ("one-electron contribution", "one_electron"),
        ("hartree contribution", "hartree"),
        ("xc contribution", "xc"),
        ("ewald contribution", "ewald"),
        ("smearing contribution", "smearing_contrib"),
    ]:
        value = d.get(key)

        if value is None:
            print(f"  {label:<28} : ABSENT")
        else:
            print(f"  {label:<28} : {value:.10f} Ry")

print()
print("===== 5. ENTROPIE / SMEARING =====")
print("-" * 78)

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    print(
        f"{k:>6} | "
        f"smearing_contrib = "
        f"{d['smearing_contrib'] if d['smearing_contrib'] is not None else 'ABSENT'} | "
        f"one-electron = "
        f"{d['one_electron'] if d['one_electron'] is not None else 'ABSENT'}"
    )

print()
print("===== 6. ESTIMATED SCF ACCURACY =====")
print("-" * 78)

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    vals = all_floats(
        r"estimated scf accuracy\s*<\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
        Path(d["path"]).read_text(errors="replace"),
    )

    if vals:
        print(
            f"{k:>6} | "
            f"dernier = {vals[-1]:.6e} Ry | "
            f"occurrences = {len(vals)}"
        )
    else:
        print(f"{k:>6} | aucune valeur trouvée")

print()
print("===== 7. CONTRÔLE DE COHÉRENCE DES PARAMÈTRES =====")
print("-" * 78)

reference = None
consistent = True

for k in TARGETS:
    if k not in data:
        continue

    d = data[k]

    signature = (
        d["ecutwfc"],
        d["ecutrho"],
        d["degauss"],
        d["occupations"],
        d["smearing_type"],
    )

    if reference is None:
        reference = signature
    elif signature != reference:
        consistent = False
        print(f"[WARN] Paramètres différents pour {k}: {signature}")

if consistent and reference is not None:
    print("[OK] Paramètres occupation/smearing cohérents entre les calculs.")

print()
print("===== 8. ANALYSE DES VARIATIONS =====")
print("-" * 78)

ordered = ["4x4x4", "5x5x5", "6x6x6", "7x7x7", "8x8x8"]

previous = None

for k in ordered:
    if k not in data:
        continue

    d = data[k]

    if previous is not None:
        pk, pd = previous

        if pd["energy"] is not None and d["energy"] is not None:
            delta_ry = d["energy"] - pd["energy"]
            delta_mev_atom = delta_ry * 13.605693009 * 1000 / 8

            print(
                f"{pk} → {k} | "
                f"ΔE = {delta_ry:+.8f} Ry | "
                f"ΔE/atome = {delta_mev_atom:+.4f} meV/atome"
            )

        if pd["fermi"] is not None and d["fermi"] is not None:
            delta_ef = d["fermi"] - pd["fermi"]

            print(
                f"{'':14} "
                f"ΔEF = {delta_ef:+.5f} eV"
            )

    previous = (k, d)

print()
print("===== 9. TESTS DE STABILITÉ =====")
print("-" * 78)

energies = [
    (k, data[k]["energy"])
    for k in ordered
    if k in data and data[k]["energy"] is not None
]

fermis = [
    (k, data[k]["fermi"])
    for k in ordered
    if k in data and data[k]["fermi"] is not None
]

if len(energies) >= 2:
    emin = min(v for _, v in energies)
    emax = max(v for _, v in energies)

    span_mev_atom = (emax - emin) * 13.605693009 * 1000 / 8

    kmin = min(energies, key=lambda x: x[1])
    kmax = max(energies, key=lambda x: x[1])

    print(
        f"[INFO] Minimum énergie : {kmin[0]} = {kmin[1]:.8f} Ry"
    )
    print(
        f"[INFO] Maximum énergie : {kmax[0]} = {kmax[1]:.8f} Ry"
    )
    print(
        f"[INFO] Plage énergétique = {span_mev_atom:.4f} meV/atome"
    )

    if span_mev_atom <= 1.0:
        print("[OK] Plage énergétique <= 1 meV/atome")
    else:
        print("[WARN] Plage énergétique > 1 meV/atome")

if len(fermis) >= 2:
    fmin = min(fermis, key=lambda x: x[1])
    fmax = max(fermis, key=lambda x: x[1])

    span_ef = fmax[1] - fmin[1]

    print(
        f"[INFO] EF minimum : {fmin[0]} = {fmin[1]:.5f} eV"
    )
    print(
        f"[INFO] EF maximum : {fmax[0]} = {fmax[1]:.5f} eV"
    )
    print(
        f"[INFO] Plage EF = {span_ef:.5f} eV"
    )

print()
print("===== 10. DIAGNOSTIC FINAL =====")
print("-" * 78)

all_done = all(
    data[k]["job_done"]
    for k in TARGETS
    if k in data
)

if all_done:
    print("[OK] Tous les calculs analysés sont JOB DONE.")
else:
    print("[WARN] Au moins une sortie n'est pas JOB DONE ou est absente.")

smearing_values = {
    data[k]["smearing_type"]
    for k in data
    if data[k]["smearing_type"] is not None
}

occupation_values = {
    data[k]["occupations"]
    for k in data
    if data[k]["occupations"] is not None
}

degauss_values = {
    data[k]["degauss"]
    for k in data
    if data[k]["degauss"] is not None
}

print(f"[INFO] Types de smearing observés : {sorted(smearing_values)}")
print(f"[INFO] Occupations observées      : {sorted(occupation_values)}")
print(f"[INFO] Degauss observés           : {sorted(degauss_values)}")

if len(smearing_values) == 1 and len(occupation_values) == 1:
    print("[OK] Même schéma occupations/smearing pour toute la série.")

if degauss_values == {0.01}:
    print("[OK] degauss = 0.01 Ry constant.")

print()
print("[CONCLUSION]")
print("Cette phase ne déclare PAS de grille k convergée.")
print("Elle vérifie uniquement la cohérence énergétique et")
print("le rôle du smearing/occupations dans les sorties QE.")
print()
print("=" * 78)
print("PHASE 78.57 TERMINÉE — READ-ONLY")
print("=" * 78)
