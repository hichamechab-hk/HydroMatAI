import os
os.system("clear")

from pathlib import Path
import re
import hashlib

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/top5_dft/TiFeH2"

FILES = {
    "DOS_INPUT":
        BASE / "electronic_relaxed/TiFeH2_relaxed_dos.in",

    "DOS_OUTPUT":
        BASE / "electronic_relaxed/TiFeH2_relaxed_dos.out",

    "DOS_DATA":
        BASE / "electronic_relaxed/TiFeH2_relaxed.dos",

    "NSCF_INPUT":
        BASE / "electronic_relaxed/TiFeH2_relaxed_nscf.in",

    "NSCF_OUTPUT":
        BASE / "electronic_relaxed/TiFeH2_relaxed_nscf.out",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


print("=" * 78)
print("PHASE 78.32 — RELAXED DOS PROVENANCE AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


# ----------------------------------------------------------------------
# 1. INVENTAIRE
# ----------------------------------------------------------------------

print("1. INVENTAIRE")
print("-" * 78)

for label, path in FILES.items():

    print()
    print(label)
    print("PATH :", path)

    if not path.exists():
        print("[ABSENT]")
        continue

    print("SIZE :", path.stat().st_size)
    print("SHA256 :", sha256(path))


# ----------------------------------------------------------------------
# 2. DOS INPUT
# ----------------------------------------------------------------------

dos_in = FILES["DOS_INPUT"]

print()
print("=" * 78)
print("2. ANALYSE DOS INPUT")
print("=" * 78)

if dos_in.exists():

    text = dos_in.read_text(errors="replace")

    for key in [
        "prefix",
        "outdir",
        "fildos",
        "Emin",
        "Emax",
        "DeltaE",
    ]:

        matches = re.findall(
            rf"^\s*{re.escape(key)}\s*=\s*([^,\n]+)",
            text,
            re.I | re.M,
        )

        if matches:
            print(f"{key:10s} : {matches[-1].strip()}")
        else:
            print(f"{key:10s} : NON TROUVÉ")

else:
    print("[ABSENT]")


# ----------------------------------------------------------------------
# 3. COMPARAISON PREFIX / OUTDIR
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("3. COHÉRENCE NSCF → DOS")
print("=" * 78)

if dos_in.exists() and FILES["NSCF_INPUT"].exists():

    dos_text = dos_in.read_text(errors="replace")
    nscf_text = FILES["NSCF_INPUT"].read_text(errors="replace")

    def get_value(text, key):
        m = re.search(
            rf"^\s*{re.escape(key)}\s*=\s*([^,\n]+)",
            text,
            re.I | re.M,
        )
        return m.group(1).strip() if m else None

    dos_prefix = get_value(dos_text, "prefix")
    nscf_prefix = get_value(nscf_text, "prefix")

    dos_outdir = get_value(dos_text, "outdir")
    nscf_outdir = get_value(nscf_text, "outdir")

    print("DOS prefix  :", dos_prefix)
    print("NSCF prefix :", nscf_prefix)

    if dos_prefix == nscf_prefix:
        print("[OK] Prefix identique")
    else:
        print("[WARN] Prefix différent")

    print()
    print("DOS outdir  :", dos_outdir)
    print("NSCF outdir :", nscf_outdir)

    if dos_outdir == nscf_outdir:
        print("[OK] Outdir identique")
    else:
        print("[WARN] Outdir différent")

else:
    print("[WARN] Inputs insuffisants")


# ----------------------------------------------------------------------
# 4. DOS OUTPUT
# ----------------------------------------------------------------------

dos_out = FILES["DOS_OUTPUT"]

print()
print("=" * 78)
print("4. DOS OUTPUT")
print("=" * 78)

if dos_out.exists():

    text = dos_out.read_text(errors="replace")

    job_done = bool(re.search(r"\bJOB DONE\b", text, re.I))

    errors = re.findall(
        r"(?:Error in routine|ERROR:|fatal error|stopping|cannot open)",
        text,
        re.I,
    )

    c_bands = len(
        re.findall(r"c_bands:", text, re.I)
    )

    print("JOB DONE      :", "YES" if job_done else "NO")
    print("Error markers :", len(errors))
    print("c_bands       :", c_bands)

    if errors:
        print()
        print("Erreurs détectées :")
        for line in errors:
            print(" ", line)

else:
    print("[ABSENT]")


# ----------------------------------------------------------------------
# 5. DOS DATA
# ----------------------------------------------------------------------

dos_data = FILES["DOS_DATA"]

print()
print("=" * 78)
print("5. DOS DATA")
print("=" * 78)

if dos_data.exists():

    lines = [
        line.strip()
        for line in dos_data.read_text(errors="replace").splitlines()
        if line.strip()
    ]

    print("Lignes non vides :", len(lines))

    numeric = []

    for line in lines:

        parts = line.split()

        try:
            values = [float(x.replace("D", "E")) for x in parts]
        except ValueError:
            continue

        if len(values) >= 3:
            numeric.append(values)

    print("Lignes numériques :", len(numeric))

    if numeric:

        energies = [x[0] for x in numeric]

        print("Emin data :", min(energies), "eV")
        print("Emax data :", max(energies), "eV")

        if len(energies) > 1:

            steps = [
                energies[i + 1] - energies[i]
                for i in range(len(energies) - 1)
            ]

            print("DeltaE min :", min(steps), "eV")
            print("DeltaE max :", max(steps), "eV")

            if max(steps) - min(steps) < 1e-10:
                print("[OK] Grille énergétique régulière")
            else:
                print("[WARN] Grille énergétique non parfaitement régulière")

else:
    print("[ABSENT]")


# ----------------------------------------------------------------------
# 6. NSCF
# ----------------------------------------------------------------------

nscf_out = FILES["NSCF_OUTPUT"]

print()
print("=" * 78)
print("6. NSCF RELAXED — ÉTAT")
print("=" * 78)

if nscf_out.exists():

    text = nscf_out.read_text(errors="replace")

    job_done = bool(re.search(r"\bJOB DONE\b", text, re.I))

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        text,
        re.I,
    )

    print("JOB DONE :", "YES" if job_done else "NO")

    if fermi:
        print("Fermi final :", fermi[-1], "eV")

else:
    print("[ABSENT]")


# ----------------------------------------------------------------------
# 7. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. SYNTHÈSE")
print("=" * 78)

print("[OK] Provenance DOS relaxée auditée.")
print("[OK] Relation NSCF → DOS inspectée.")
print("[OK] Données DOS inspectées.")
print("[OK] Aucun calcul QE.")
print("[OK] Aucun fichier modifié.")
print("[OK] Aucun changement AIDA.")

print()
print("STATUT : PHASE 78.32 TERMINÉE — READ-ONLY")
print("=" * 78)
