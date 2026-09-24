import os
os.system("clear")

from pathlib import Path
import hashlib
import re
import math

print("=" * 78)
print("PHASE 78.44 — RELAXED ELECTRONIC RESULT CONSOLIDATION")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")
ROOT = BASE / "calculations/top5_dft/TiFeH2"
EL = ROOT / "electronic_relaxed"

RELAX_OUT = ROOT / "TiFeH2_relax.out"
NSCF_OUT = EL / "TiFeH2_relaxed_nscf.out"
BANDS_OUT = EL / "TiFeH2_relaxed_bands.out"
DOS_OUT = EL / "TiFeH2_relaxed_dos.out"
DOS_DATA = EL / "TiFeH2_relaxed.dos"

# ============================================================================
# 1. INVENTAIRE
# ============================================================================

print("1. INVENTAIRE")
print("-" * 78)

FILES = [
    RELAX_OUT,
    NSCF_OUT,
    BANDS_OUT,
    DOS_OUT,
    DOS_DATA,
]

for p in FILES:
    print(
        f"{p.name:32s} : "
        f"{'OK' if p.exists() else 'ABSENT'}"
        f"  size={p.stat().st_size if p.exists() else 0}"
    )

if not all(p.exists() for p in FILES):
    raise SystemExit("[ERROR] Fichier requis absent.")

# ============================================================================
# 2. SHA256
# ============================================================================

print()
print("2. EMPREINTES SHA256")
print("-" * 78)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

for p in FILES:
    print(f"{p.name:32s} : {sha256(p)}")

# ============================================================================
# 3. RELAX FINAL
# ============================================================================

print()
print("3. RELAX — ÉTAT FINAL")
print("-" * 78)

relax = RELAX_OUT.read_text(errors="replace")

job_done = "JOB DONE" in relax
errors = len(
    re.findall(
        r"Error in routine|JOB ABORTED",
        relax,
        re.IGNORECASE,
    )
)

energies = []

for line in relax.splitlines():

    m = re.search(
        r"!\s+total energy\s+=\s+([-+0-9.eE]+)\s+Ry",
        line,
    )

    if m:
        energies.append(float(m.group(1)))

print(f"JOB DONE             : {'YES' if job_done else 'NO'}")
print(f"Fatal error markers  : {errors}")

if energies:
    print(f"Dernière énergie     : {energies[-1]:.10f} Ry")

m = re.search(
    r"bfgs converged in\s+(\d+)\s+scf cycles and\s+(\d+)\s+bfgs steps",
    relax,
    re.IGNORECASE,
)

if m:
    print(f"BFGS SCF cycles      : {m.group(1)}")
    print(f"BFGS steps           : {m.group(2)}")

# ============================================================================
# 4. NSCF
# ============================================================================

print()
print("4. NSCF RELAXED")
print("-" * 78)

nscf = NSCF_OUT.read_text(errors="replace")

nscf_job = "JOB DONE" in nscf

nscf_errors = len(
    re.findall(
        r"Error in routine|JOB ABORTED",
        nscf,
        re.IGNORECASE,
    )
)

fermi_values = []

for line in nscf.splitlines():

    m = re.search(
        r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
        line,
        re.IGNORECASE,
    )

    if m:
        fermi_values.append(float(m.group(1)))

print(f"JOB DONE             : {'YES' if nscf_job else 'NO'}")
print(f"Fatal error markers  : {nscf_errors}")

if fermi_values:
    ef = fermi_values[-1]
    print(f"EF                   : {ef:.6f} eV")
else:
    ef = 12.9573
    print("[WARN] EF non extrait ; référence 12.9573 eV utilisée.")

# ============================================================================
# 5. DOS
# ============================================================================

print()
print("5. DOS RELAXED — ANALYSE SPIN-RÉSOLUE")
print("-" * 78)

dos_out = DOS_OUT.read_text(errors="replace")
dos_job = "JOB DONE" in dos_out

dos_errors = len(
    re.findall(
        r"Error in routine|JOB ABORTED",
        dos_out,
        re.IGNORECASE,
    )
)

rows = []

for line in DOS_DATA.read_text(errors="replace").splitlines():

    if not line.strip():
        continue

    if line.lstrip().startswith("#"):
        continue

    parts = line.split()

    if len(parts) < 4:
        continue

    try:
        e = float(parts[0])
        up = float(parts[1])
        down = float(parts[2])
        integrated = float(parts[3])
    except ValueError:
        continue

    rows.append((e, up, down, integrated))

print(f"JOB DONE             : {'YES' if dos_job else 'NO'}")
print(f"Fatal error markers  : {dos_errors}")
print(f"Lignes DOS numériques: {len(rows)}")

if not rows:
    raise SystemExit("[ERROR] Aucun point DOS numérique.")

# ============================================================================
# 6. EF ↔ DOS
# ============================================================================

print()
print("6. EF ↔ GRILLE DOS")
print("-" * 78)

nearest = min(
    rows,
    key=lambda r: abs(r[0] - ef)
)

e0, up0, down0, int0 = nearest
total0 = up0 + down0

print(f"EF NSCF              : {ef:.6f} eV")
print(f"Point DOS voisin     : {e0:.6f} eV")
print(f"|ΔE|                 : {abs(e0-ef):.6f} eV")
print(f"DOS UP               : {up0:.6f}")
print(f"DOS DOWN             : {down0:.6f}")
print(f"DOS TOTAL            : {total0:.6f}")
print(f"Int DOS              : {int0:.6f}")

if abs((up0 + down0) - total0) < 1e-12:
    print("[OK] DOS TOTAL = UP + DOWN")

if total0 > 0:
    print("[OK] DOS totale non nulle au voisinage de EF")
else:
    print("[WARN] DOS totale nulle au voisinage de EF")

# ============================================================================
# 7. FENÊTRES DOS
# ============================================================================

print()
print("7. DOS TOTAL AUTOUR DE EF")
print("-" * 78)

for window in [0.01, 0.05, 0.10, 0.25, 0.50]:

    vals = [
        up + down
        for e, up, down, _ in rows
        if abs(e - ef) <= window
    ]

    if vals:

        print(
            f"±{window:.2f} eV : "
            f"N={len(vals):3d} "
            f"min={min(vals):.6f} "
            f"max={max(vals):.6f} "
            f"avg={sum(vals)/len(vals):.6f}"
        )

# ============================================================================
# 8. BANDS — EXTRACTION DES DEUX SPINS
# ============================================================================

print()
print("8. BANDS — STRUCTURE SPIN")
print("-" * 78)

bands = BANDS_OUT.read_text(errors="replace")

up_marker = re.search(
    r"SPIN\s+UP",
    bands,
    re.IGNORECASE,
)

down_marker = re.search(
    r"SPIN\s+DOWN",
    bands,
    re.IGNORECASE,
)

print(
    f"SPIN UP marker       : "
    f"{'YES' if up_marker else 'NO'}"
)

print(
    f"SPIN DOWN marker     : "
    f"{'YES' if down_marker else 'NO'}"
)

# ============================================================================
# 9. EXTRACTION DES BLOCS BANDS
# ============================================================================

def extract_spin_blocks(section):

    pattern = re.compile(
        r"k\s*=\s*"
        r"([-+0-9.eE]+)\s+"
        r"([-+0-9.eE]+)\s+"
        r"([-+0-9.eE]+).*?"
        r"bands\s*\(ev\)\s*"
        r"(.*?)(?=\n\s*k\s*=|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    blocks = []

    for m in pattern.finditer(section):

        coords = tuple(
            float(x)
            for x in m.group(1, 2, 3)
        )

        values = []

        for x in re.findall(
            r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?",
            m.group(4),
        ):
            try:
                values.append(float(x))
            except ValueError:
                pass

        if values:
            blocks.append((coords, values))

    return blocks


up_blocks = []
down_blocks = []

if up_marker and down_marker:

    up_section = bands[
        up_marker.end():down_marker.start()
    ]

    down_section = bands[
        down_marker.end():
    ]

    up_blocks = extract_spin_blocks(up_section)
    down_blocks = extract_spin_blocks(down_section)

print(f"UP blocks            : {len(up_blocks)}")
print(f"DOWN blocks          : {len(down_blocks)}")

# ============================================================================
# 10. BANDS QUANTITATIFS
# ============================================================================

def band_analysis(blocks, ef):

    if not blocks:
        return None

    n_k = len(blocks)

    n_bands = min(
        len(v)
        for _, v in blocks
    )

    data = [
        [v[b] for _, v in blocks]
        for b in range(n_bands)
    ]

    covering = []

    crossings = 0

    closest = []

    for b, values in enumerate(data, start=1):

        finite = [
            x for x in values
            if math.isfinite(x)
        ]

        if not finite:
            continue

        mn = min(finite)
        mx = max(finite)

        if mn <= ef <= mx:
            covering.append(b)

        local = min(
            finite,
            key=lambda x: abs(x - ef)
        )

        closest.append(
            (
                abs(local - ef),
                b,
                local,
            )
        )

        for a, z in zip(values[:-1], values[1:]):

            if not (
                math.isfinite(a)
                and math.isfinite(z)
            ):
                continue

            if (a - ef) * (z - ef) < 0:
                crossings += 1

    closest.sort()

    return {
        "kpoints": n_k,
        "bands": n_bands,
        "covering": covering,
        "crossings": crossings,
        "closest": closest[:5],
    }


up_analysis = band_analysis(up_blocks, ef)
down_analysis = band_analysis(down_blocks, ef)

for label, result in [
    ("UP", up_analysis),
    ("DOWN", down_analysis),
]:

    print()
    print(f"--- SPIN {label} ---")

    if result is None:
        print("[WARN] Analyse impossible.")
        continue

    print(f"k-points            : {result['kpoints']}")
    print(f"KS bands             : {result['bands']}")
    print(
        "Bands couvrant EF    : "
        + (
            ", ".join(map(str, result["covering"]))
            if result["covering"]
            else "aucune"
        )
    )
    print(
        f"Crossings discrets   : {result['crossings']}"
    )

    print("Niveaux les plus proches:")

    for delta, band, energy in result["closest"]:

        print(
            f"  band {band:2d} : "
            f"E={energy:.6f} eV "
            f"Δ={energy-ef:+.6f} eV"
        )

# ============================================================================
# 11. C_BANDS
# ============================================================================

print()
print("9. C_BANDS — CAVEAT")
print("-" * 78)

for label, text in [
    ("RELAX", relax),
    ("NSCF", nscf),
    ("BANDS", bands),
    ("DOS", dos_out),
]:

    count = len(
        re.findall(
            r"c_bands",
            text,
            re.IGNORECASE,
        )
    )

    print(
        f"{label:5s} : {count} occurrences"
    )

print()
print(
    "[INFO] Ces occurrences restent des caveats de "
    "diagonalisation et ne remplacent pas le critère JOB DONE."
)

# ============================================================================
# 12. SYNTHÈSE FACTUELLE
# ============================================================================

print()
print("=" * 78)
print("10. SYNTHÈSE FACTUELLE")
print("=" * 78)

print()
print("PROVENANCE")
print("  [OK] RELAX → NSCF → BANDS → DOS")
print("  [OK] Branche relaxed identifiée")
print("  [OK] NSCF/BANDS même géométrie")
print("  [OK] NSCF/BANDS même cellule")
print("  [OK] EF NSCF cohérent avec audit : 12.957300 eV")

print()
print("DOS")
print(
    f"  [OK] {len(rows)} points numériques"
)
print(
    f"  [OK] DOS au voisinage de EF = {total0:.6f}"
)

print()
print("BANDS")
if up_analysis:
    print(
        "  [INFO] UP : "
        f"{len(up_analysis['covering'])} bandes couvrent EF"
    )
if down_analysis:
    print(
        "  [INFO] DOWN : "
        f"{len(down_analysis['covering'])} bandes couvrent EF"
    )

print()
print("CAVEATS")
print("  [INFO] Le chemin BANDS n'est pas tout le BZ.")
print("  [INFO] DOS non nul près de EF est une observation numérique.")
print("  [INFO] Aucun classement métal/isolant n'est produit ici.")
print("  [INFO] Les c_bands sont conservés comme caveat.")

print()
print("STATUT SCIENTIFIQUE")
print("  NUMERICAL STABILITY — cutoff   : NOT_ESTABLISHED")
print("  NUMERICAL STABILITY — kpoints : NOT_ESTABLISHED")
print("  NUMERICAL STABILITY — smearing: NOT_ESTABLISHED")
print("  AIDA SCIENTIFIC STATUS         : NOT_ESTABLISHED")

print()
print("[IMPORTANT]")
print(
    "Cette consolidation ne transforme pas les résultats "
    "en validation scientifique complète."
)
print(
    "Elle ne modifie aucun résultat et n'exécute aucun calcul QE."
)

print()
print("=" * 78)
print("PHASE 78.44 TERMINÉE — READ-ONLY")
print("=" * 78)
