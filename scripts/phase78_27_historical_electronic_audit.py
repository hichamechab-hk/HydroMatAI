from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")

BASES = {
    "TiFeH2_electronic": ROOT / "calculations/top5_dft/TiFeH2/electronic",
    "TiFeH2_electronic_relaxed": ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed",
    "phase10_real_electronic": ROOT / "calculations/phase_10_real_electronic",
}

print("=" * 78)
print("PHASE 78.27 — HISTORICAL TiFeH2 DOS/BANDS AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

for label, base in BASES.items():

    print("=" * 78)
    print(label)
    print("=" * 78)

    if not base.exists():
        print("[ABSENT]")
        continue

    files = sorted(p for p in base.iterdir() if p.is_file())

    for p in files:
        print(f"  {p.name}  ({p.stat().st_size} octets)")

    print()

    # --------------------------------------------------------------
    # Inputs
    # --------------------------------------------------------------

    for p in files:
        if p.suffix.lower() != ".in":
            continue

        print("-" * 78)
        print(f"INPUT : {p.name}")
        print("-" * 78)

        text = p.read_text(errors="replace")

        for pattern in [
            r"calculation\s*=",
            r"prefix\s*=",
            r"outdir\s*=",
            r"pseudo_dir\s*=",
            r"nat\s*=",
            r"ntyp\s*=",
            r"ecutwfc\s*=",
            r"ecutrho\s*=",
            r"nspin\s*=",
            r"occupations\s*=",
            r"smearing\s*=",
            r"degauss\s*=",
            r"K_POINTS",
            r"CELL_PARAMETERS",
            r"ATOMIC_POSITIONS",
        ]:
            for m in re.finditer(pattern, text, re.I):
                line = text[m.start():text.find("\n", m.start())]
                print(" ", line.strip())

    # --------------------------------------------------------------
    # Outputs
    # --------------------------------------------------------------

    for p in files:
        if p.suffix.lower() != ".out":
            continue

        print()
        print("-" * 78)
        print(f"OUTPUT : {p.name}")
        print("-" * 78)

        text = p.read_text(errors="replace")
        lines = text.splitlines()

        markers = {
            "JOB DONE": r"JOB DONE",
            "convergence": r"convergence has been achieved",
            "Fermi": r"Fermi energy",
            "bands": r"bands\s*\(ev\)",
            "c_bands": r"c_bands:",
            "DOS": r"\bDOS\b",
            "error": r"\berror\b",
        }

        for label2, pattern in markers.items():
            count = len(re.findall(pattern, text, re.I))
            if count:
                print(f"  {label2:15s}: {count}")

        fermi = re.findall(
            r"(?:the\s+)?Fermi\s+energy\s+is\s+"
            r"([-+0-9.eEdD]+)\s+eV",
            text,
            re.I,
        )

        if fermi:
            print(f"  Fermi final     : {fermi[-1]} eV")

        energies = re.findall(
            r"!\s+total energy\s+=\s*"
            r"([-+0-9.eEdD]+)\s+Ry",
            text,
            re.I,
        )

        if energies:
            print(f"  Total energies  : {len(energies)}")
            print(f"  Last energy     : {energies[-1]} Ry")

        print(f"  Lines           : {len(lines)}")

    # --------------------------------------------------------------
    # Raw DOS files
    # --------------------------------------------------------------

    for p in files:
        if p.suffix.lower() != ".dos":
            continue

        print()
        print("-" * 78)
        print(f"DOS DATA : {p.name}")
        print("-" * 78)

        text = p.read_text(errors="replace")
        lines = [
            x for x in text.splitlines()
            if x.strip() and not x.lstrip().startswith("#")
        ]

        print(f"  data lines      : {len(lines)}")

        if lines:
            print("  première ligne   :", lines[0])
            print("  dernière ligne   :", lines[-1])

        numeric_rows = []

        for line in lines[:20]:
            fields = line.split()

            try:
                [float(x.replace("D", "E").replace("d", "e"))
                 for x in fields]
                numeric_rows.append(fields)
            except ValueError:
                pass

        print(f"  lignes numériques inspectées : {len(numeric_rows)}")


print()
print("=" * 78)
print("PHASE 78.27 TERMINÉE — READ-ONLY")
print("=" * 78)
