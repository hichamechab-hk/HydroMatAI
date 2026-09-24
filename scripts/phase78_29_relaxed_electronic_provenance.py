from pathlib import Path
import re
import hashlib

ROOT = Path("/home/hk/HydroMatAI")

FILES = {
    "CIF_relaxed":
        ROOT / "calculations/top5_dft/TiFeH2/TiFeH2.cif",

    "RELAX_input":
        ROOT / "calculations/top5_dft/TiFeH2/TiFeH2_relax.in",

    "RELAX_output":
        ROOT / "calculations/top5_dft/TiFeH2/TiFeH2_relax.out",

    "NSCF_relaxed":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_nscf.in",

    "BANDS_relaxed":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_bands.in",

    "DOS_relaxed":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/TiFeH2_relaxed_dos.in",
}

print("=" * 78)
print("PHASE 78.29 — RELAXED ELECTRONIC PROVENANCE")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def show_block(text, keyword):
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if re.search(keyword, line, re.I):
            print(f"  {i+1:5d}: {line}")

            for j in range(i + 1, min(i + 8, len(lines))):
                if lines[j].strip():
                    print(f"  {j+1:5d}: {lines[j]}")

            print()

for label, path in FILES.items():

    print("-" * 78)
    print(label)
    print("-" * 78)

    if not path.exists():
        print("[ABSENT]", path)
        continue

    print("PATH   :", path)
    print("SIZE   :", path.stat().st_size)
    print("SHA256 :", sha256(path))

    text = path.read_text(errors="replace")

    if path.suffix.lower() in {".in", ".out"}:

        for pattern in [
            r"prefix\s*=",
            r"outdir\s*=",
            r"calculation\s*=",
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
            show_block(text, pattern)

print("=" * 78)
print("COMPARAISON RELAX / ELECTRONIC_RELAXED")
print("=" * 78)

relax_out = FILES["RELAX_output"]
nscf = FILES["NSCF_relaxed"]
bands = FILES["BANDS_relaxed"]
dos = FILES["DOS_relaxed"]

for label, path in [
    ("RELAX", relax_out),
    ("NSCF", nscf),
    ("BANDS", bands),
    ("DOS", dos),
]:
    if not path.exists():
        continue

    text = path.read_text(errors="replace")

    print()
    print(label)

    for pattern in [
        r"JOB DONE",
        r"Fermi\s+energy",
        r"End of band structure calculation",
        r"c_bands:",
    ]:
        matches = re.findall(pattern, text, re.I)
        print(f"  {pattern:40s}: {len(matches)}")

print()
print("=" * 78)
print("PHASE 78.29 TERMINÉE — READ-ONLY")
print("=" * 78)
