#!/usr/bin/env python3

import re
from pathlib import Path

print("\033c", end="")

print("=" * 78)
print("PHASE 78.68 — AUDIT DU c_bands FINAL À 8³")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Cible : 140 Ry / 560 Ry / 8x8x8")
print("[INFO] Objectif : caractériser le dernier c_bands")
print()

PATH = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_convergence/TiFeH2/"
    "ecut140_rho560_k888_phase78_63.out"
)

if not PATH.exists():
    print("[ERROR] Fichier absent :")
    print(PATH)
    raise SystemExit(1)

text = PATH.read_text(errors="replace")
lines = text.splitlines()

print("===== 1. FICHIER CIBLE =====")
print("-" * 78)
print(PATH)
print(f"Taille : {PATH.stat().st_size} octets")
print()

print("===== 2. DERNIÈRE ITÉRATION SCF =====")
print("-" * 78)

iteration_indices = []

for i, line in enumerate(lines):
    if re.search(r"iteration\s*#\s*18\b", line, re.I):
        iteration_indices.append(i)

if not iteration_indices:
    print("[ERROR] Itération 18 non trouvée.")
    raise SystemExit(1)

idx = iteration_indices[-1]

print(f"Ligne détectée : {idx + 1}")
print()

start = max(0, idx - 8)
end = min(len(lines), idx + 80)

for n in range(start, end):
    print(f"{n + 1:>6}: {lines[n]}")


print()
print("===== 3. RECHERCHE DU c_bands FINAL =====")
print("-" * 78)

cbands_positions = []

for i, line in enumerate(lines):
    if "c_bands:" in line.lower():
        cbands_positions.append(i)

print(
    f"Nombre total de lignes c_bands : "
    f"{len(cbands_positions)}"
)

if cbands_positions:

    last_cb = cbands_positions[-1]

    print(
        f"Dernier c_bands : ligne "
        f"{last_cb + 1}"
    )

    print()
    print("Contexte ±12 lignes :")
    print()

    s = max(0, last_cb - 12)
    e = min(len(lines), last_cb + 13)

    for n in range(s, e):
        marker = " >>> " if n == last_cb else "     "
        print(
            f"{marker}{n + 1:>6}: {lines[n]}"
        )


print()
print("===== 4. RECHERCHE DES MESSAGES DE DIAGONALISATION =====")
print("-" * 78)

patterns = [
    "cdiaghg",
    "rdiaghg",
    "cegterg",
    "eigenvalues",
    "not converged",
    "diagonal",
    "orthogonal",
    "davcio",
    "subspace",
]

for pattern in patterns:

    matches = []

    for i, line in enumerate(lines):

        if pattern.lower() in line.lower():
            matches.append((i, line.strip()))

    print()
    print(f"[{pattern}] : {len(matches)} occurrence(s)")

    for i, line in matches[-10:]:
        print(f"  ligne {i + 1}: {line}")


print()
print("===== 5. FIN EXACTE DU SCF =====")
print("-" * 78)

# Cherche la dernière énergie, accuracy, c_bands et JOB DONE
energy_matches = []

for i, line in enumerate(lines):

    if re.search(
        r"!\s*total energy\s*=",
        line,
        re.I
    ):
        energy_matches.append((i, line.strip()))

accuracy_matches = []

for i, line in enumerate(lines):

    if re.search(
        r"estimated scf accuracy",
        line,
        re.I
    ):
        accuracy_matches.append((i, line.strip()))

print("Dernière énergie :")
if energy_matches:
    i, line = energy_matches[-1]
    print(f"  ligne {i + 1}: {line}")

print()
print("Dernière SCF accuracy :")
if accuracy_matches:
    i, line = accuracy_matches[-1]
    print(f"  ligne {i + 1}: {line}")

print()
print("Dernier c_bands :")
if cbands_positions:
    i = cbands_positions[-1]
    print(f"  ligne {i + 1}: {lines[i].strip()}")

print()
print("JOB DONE :")
print(
    "  OUI"
    if "JOB DONE." in text
    else "  NON"
)


print()
print("===== 6. ÉCART ENTRE c_bands FINAL ET ÉNERGIE FINALE =====")
print("-" * 78)

if cbands_positions and energy_matches:

    cb = cbands_positions[-1]
    en = energy_matches[-1][0]

    print(
        f"Ligne c_bands : {cb + 1}"
    )
    print(
        f"Ligne énergie : {en + 1}"
    )
    print(
        f"Écart         : {en - cb} lignes"
    )

    if en >= cb:
        print(
            "[INFO] L'énergie finale apparaît après "
            "le dernier c_bands."
        )
    else:
        print(
            "[INFO] Le dernier c_bands apparaît après "
            "la dernière énergie détectée."
        )


print()
print("===== 7. RECHERCHE DES ERREURS / ABORTS =====")
print("-" * 78)

error_patterns = [
    "error in routine",
    "fatal",
    "segmentation",
    "abort",
    "stopping",
    "cannot",
    "failed",
    "convergence NOT achieved",
]

found_errors = []

for i, line in enumerate(lines):

    low = line.lower()

    for pattern in error_patterns:

        if pattern in low:

            found_errors.append(
                (i + 1, line.strip())
            )

            break

if found_errors:

    for n, line in found_errors[-20:]:
        print(f"ligne {n}: {line}")

else:
    print("[RESULT] Aucun motif d'erreur critique détecté.")


print()
print("===== 8. DIAGNOSTIC =====")
print("-" * 78)

if cbands_positions:

    last_cb = cbands_positions[-1]

    # Trouver la dernière itération connue avant le c_bands
    current_iter = None

    for i in range(last_cb, -1, -1):

        m = re.search(
            r"iteration\s*#\s*(\d+)",
            lines[i],
            re.I
        )

        if m:
            current_iter = int(m.group(1))
            break

    print(
        f"[RESULT] Dernier c_bands associé à "
        f"l'itération {current_iter}."
    )

    if current_iter == 18:
        print(
            "[WARN] Le c_bands est associé à la dernière "
            "itération SCF de 8³."
        )
        print(
            "[INFO] Il faut distinguer ce message d'une "
            "échec de convergence SCF globale."
        )

else:

    print(
        "[RESULT] Aucun c_bands détecté."
    )

print()
print("[IMPORTANT]")
print(
    "Cette phase ne modifie aucun résultat scientifique."
)
print(
    "Elle ne relance aucun calcul QE."
)
print(
    "Elle sert uniquement à caractériser le dernier "
    "événement de diagonalisation."
)

print()
print("=" * 78)
print("PHASE 78.68 TERMINÉE")
print("=" * 78)
