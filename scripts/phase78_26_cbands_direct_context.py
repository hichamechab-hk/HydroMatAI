from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations" / "new_campaign" / "TiFeH2"

FILES = {
    "2x2x2": BASE / "convergence/run_kpoints_2x2x2/TiFeH2_kpoints_2.out",
    "3x3x3": BASE / "convergence/run_kpoints_3x3x3/TiFeH2_kpoints_3.out",
    "4x4x4": BASE / "convergence/run_kpoints_4x4x4/TiFeH2_kpoints_4.out",
}

print("=" * 78)
print("PHASE 78.26 — AUDIT DIRECT C_BANDS / K-POINTS")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

for mesh, path in FILES.items():

    print("=" * 78)
    print(f"K-POINTS : {mesh}")
    print("=" * 78)

    if not path.exists():
        print(f"[FAIL] Fichier absent : {path}")
        continue

    text = path.read_text(errors="replace")
    lines = text.splitlines()

    print(f"Fichier : {path}")
    print(f"Lignes  : {len(lines)}")

    # --------------------------------------------------------------
    # C_BANDS warnings
    # --------------------------------------------------------------

    warnings = []

    for i, line in enumerate(lines):
        if re.search(r"c_bands:\s+\d+\s+eigenvalues\s+not\s+converged",
                     line, re.I):
            warnings.append(i)

    print()
    print(f"C_BANDS warnings : {len(warnings)}")

    if not warnings:
        print("[OK] Aucun warning c_bands")
        continue

    # --------------------------------------------------------------
    # Context around each warning
    # --------------------------------------------------------------

    for n, idx in enumerate(warnings, 1):

        print()
        print("-" * 78)
        print(f"C_BANDS #{n} — ligne {idx + 1}")
        print("-" * 78)

        start = max(0, idx - 12)
        end = min(len(lines), idx + 20)

        for j in range(start, end):
            marker = ">>>" if j == idx else "   "
            print(f"{marker} {j + 1:5d}: {lines[j]}")

        # ----------------------------------------------------------
        # Previous k-point marker
        # ----------------------------------------------------------

        previous_k = None

        for j in range(idx - 1, -1, -1):
            if re.search(r"^\s*k\s*=", lines[j], re.I):
                previous_k = (j, lines[j].strip())
                break

        # ----------------------------------------------------------
        # Next k-point marker
        # ----------------------------------------------------------

        next_k = None

        for j in range(idx + 1, len(lines)):
            if re.search(r"^\s*k\s*=", lines[j], re.I):
                next_k = (j, lines[j].strip())
                break

        print()
        print("K-point précédent :")
        if previous_k:
            print(
                f"  ligne {previous_k[0] + 1}: "
                f"{previous_k[1]}"
            )
        else:
            print("  NON TROUVÉ")

        print("K-point suivant :")
        if next_k:
            print(
                f"  ligne {next_k[0] + 1}: "
                f"{next_k[1]}"
            )
        else:
            print("  NON TROUVÉ")

        # ----------------------------------------------------------
        # Nearby bands blocks
        # ----------------------------------------------------------

        print()
        print("Blocs 'bands (ev)' proches :")

        nearby = []

        for j in range(max(0, idx - 100), min(len(lines), idx + 100)):
            if "bands (ev)" in lines[j].lower():
                nearby.append((j, lines[j].strip()))

        if nearby:
            for j, line in nearby:
                print(f"  ligne {j + 1}: {line}")
        else:
            print("  Aucun bloc trouvé dans ±100 lignes")

    # --------------------------------------------------------------
    # Final convergence
    # --------------------------------------------------------------

    print()
    print("État final du SCF :")

    convergence_lines = [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if re.search(
            r"convergence has been achieved|"
            r"JOB DONE",
            line,
            re.I,
        )
    ]

    if convergence_lines:
        for line_no, line in convergence_lines[-5:]:
            print(f"  {line_no}: {line}")
    else:
        print("  Aucun marqueur final trouvé")

    # --------------------------------------------------------------
    # Fermi
    # --------------------------------------------------------------

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.eEdD]+)\s+ev",
        text,
        re.I,
    )

    print()
    if fermi:
        print(f"Fermi final détecté : {fermi[-1]} eV")
    else:
        print("Fermi final : non détecté")


print()
print("=" * 78)
print("PHASE 78.26 TERMINÉE — READ-ONLY")
print("=" * 78)
