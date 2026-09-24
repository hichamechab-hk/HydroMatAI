from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")

FILES = [
    ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_bands.out",
    ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_nscf.out",
    ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_dos.out",

    ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_bands.out",
    ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_nscf.out",
    ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_dos.out",
]

print("=" * 78)
print("PHASE 78.28 — HISTORICAL C_BANDS / ELECTRONIC JOBS")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

for path in FILES:

    print("=" * 78)
    print(path.name)
    print("=" * 78)

    if not path.exists():
        print("[ABSENT]")
        continue

    text = path.read_text(errors="replace")
    lines = text.splitlines()

    warnings = []

    for i, line in enumerate(lines):
        if re.search(
            r"c_bands:\s+\d+\s+eigenvalues\s+not\s+converged",
            line,
            re.I,
        ):
            warnings.append(i)

    print(f"Fichier : {path}")
    print(f"Lignes  : {len(lines)}")
    print(f"C_BANDS : {len(warnings)}")

    # --------------------------------------------------------------
    # Contextes des warnings
    # --------------------------------------------------------------

    for n, idx in enumerate(warnings, 1):

        print()
        print("-" * 70)
        print(f"C_BANDS #{n} — ligne {idx + 1}")
        print("-" * 70)

        start = max(0, idx - 5)
        end = min(len(lines), idx + 12)

        for j in range(start, end):
            marker = ">>>" if j == idx else "   "
            print(f"{marker} {j + 1:5d}: {lines[j]}")

    # --------------------------------------------------------------
    # Convergence / JOB DONE
    # --------------------------------------------------------------

    convergence = [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if re.search(
            r"convergence has been achieved",
            line,
            re.I,
        )
    ]

    jobdone = [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if re.search(r"JOB DONE", line, re.I)
    ]

    print()
    print("CONVERGENCE :")

    if convergence:
        for item in convergence[-3:]:
            print(f"  {item}")
    else:
        print("  Aucun marqueur de convergence")

    print("JOB DONE :")

    if jobdone:
        print(f"  {jobdone[-1]}")
    else:
        print("  ABSENT")

    # --------------------------------------------------------------
    # Fermi
    # --------------------------------------------------------------

    fermi = re.findall(
        r"(?:the\s+)?Fermi\s+energy\s+is\s+"
        r"([-+0-9.eEdD]+)\s+eV",
        text,
        re.I,
    )

    if fermi:
        print()
        print(f"FERMI FINAL : {fermi[-1]} eV")

    # --------------------------------------------------------------
    # Errors / fatal
    # --------------------------------------------------------------

    fatal = []

    for i, line in enumerate(lines, 1):
        low = line.lower()

        if (
            "error in routine" in low
            or "fatal error" in low
            or "segmentation fault" in low
            or "stopping" in low
        ):
            fatal.append((i, line.strip()))

    print()
    print("ERREURS FATALES :")

    if fatal:
        for item in fatal[:20]:
            print(f"  {item}")
    else:
        print("  Aucune détectée")

print()
print("=" * 78)
print("PHASE 78.28 TERMINÉE — READ-ONLY")
print("=" * 78)
