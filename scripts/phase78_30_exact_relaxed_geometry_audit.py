from pathlib import Path
import re
import math

ROOT = Path("/home/hk/HydroMatAI")

RELAX_OUT = ROOT / "calculations/top5_dft/TiFeH2/TiFeH2_relax.out"

ELECTRONIC = {
    "NSCF": (
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_nscf.in",
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_nscf.out",
    ),
    "BANDS": (
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_bands.in",
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_bands.out",
    ),
}

TOL = 1e-8


print("=" * 78)
print("PHASE 78.30 — EXACT RELAXED GEOMETRY + ELECTRONIC OUTPUT AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


def read_text(path):
    return path.read_text(errors="replace")


def extract_last_geometry(text):
    lines = text.splitlines()

    cell_blocks = []
    pos_blocks = []

    i = 0
    while i < len(lines):

        if re.match(r"^\s*CELL_PARAMETERS", lines[i], re.I):
            block = []
            for j in range(i + 1, min(i + 4, len(lines))):
                vals = lines[j].split()
                if len(vals) >= 3:
                    try:
                        block.append([float(vals[0]),
                                      float(vals[1]),
                                      float(vals[2])])
                    except ValueError:
                        pass
            if len(block) == 3:
                cell_blocks.append(block)

        if re.match(r"^\s*ATOMIC_POSITIONS", lines[i], re.I):
            block = []
            for j in range(i + 1, min(i + 9, len(lines))):
                vals = lines[j].split()
                if len(vals) >= 4:
                    try:
                        block.append(
                            (
                                vals[0],
                                float(vals[1]),
                                float(vals[2]),
                                float(vals[3]),
                            )
                        )
                    except ValueError:
                        pass

            if len(block) == 8:
                pos_blocks.append(block)

        i += 1

    if not cell_blocks or not pos_blocks:
        return None, None

    return cell_blocks[-1], pos_blocks[-1]


def extract_first_geometry(text):
    lines = text.splitlines()

    cell = None
    pos = None

    for i, line in enumerate(lines):

        if cell is None and re.match(
            r"^\s*CELL_PARAMETERS", line, re.I
        ):
            block = []
            for j in range(i + 1, min(i + 4, len(lines))):
                vals = lines[j].split()
                if len(vals) >= 3:
                    try:
                        block.append([
                            float(vals[0]),
                            float(vals[1]),
                            float(vals[2]),
                        ])
                    except ValueError:
                        pass
            if len(block) == 3:
                cell = block

        if pos is None and re.match(
            r"^\s*ATOMIC_POSITIONS", line, re.I
        ):
            block = []
            for j in range(i + 1, min(i + 9, len(lines))):
                vals = lines[j].split()
                if len(vals) >= 4:
                    try:
                        block.append((
                            vals[0],
                            float(vals[1]),
                            float(vals[2]),
                            float(vals[3]),
                        ))
                    except ValueError:
                        pass
            if len(block) == 8:
                pos = block

        if cell is not None and pos is not None:
            break

    return cell, pos


def max_cell_diff(a, b):
    return max(
        abs(a[i][j] - b[i][j])
        for i in range(3)
        for j in range(3)
    )


def max_pos_diff(a, b):
    diffs = []

    for x, y in zip(a, b):
        if x[0] != y[0]:
            return math.inf

        diffs.extend([
            abs(x[k] - y[k])
            for k in range(1, 4)
        ])

    return max(diffs)


def compare_geometry(ref_cell, ref_pos, test_cell, test_pos):
    if ref_cell is None or ref_pos is None:
        return False, math.inf, math.inf

    if test_cell is None or test_pos is None:
        return False, math.inf, math.inf

    dc = max_cell_diff(ref_cell, test_cell)
    dp = max_pos_diff(ref_pos, test_pos)

    return dc <= TOL and dp <= TOL, dc, dp


# ----------------------------------------------------------------------
# 1. RELAX FINAL GEOMETRY
# ----------------------------------------------------------------------

print("1. GEOMETRIE FINALE RELAX")
print("-" * 78)

relax_text = read_text(RELAX_OUT)

relax_cell, relax_pos = extract_last_geometry(relax_text)

if relax_cell is None or relax_pos is None:
    print("[FAIL] Géométrie finale introuvable dans RELAX.out")
    raise SystemExit(1)

print("[OK] Dernière CELL_PARAMETERS extraite")
print("[OK] Dernière ATOMIC_POSITIONS extraite")

print()
print("CELL_PARAMETERS finale:")
for row in relax_cell:
    print(" ", " ".join(f"{x:.12f}" for x in row))

print()
print("ATOMIC_POSITIONS finale:")
for atom in relax_pos:
    print(
        f"  {atom[0]:2s} "
        f"{atom[1]:.12f} "
        f"{atom[2]:.12f} "
        f"{atom[3]:.12f}"
    )


# ----------------------------------------------------------------------
# 2. COMPARAISON ELECTRONIC_RELAXED
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("2. COMPARAISON EXACTE RELAX → NSCF/BANDS")
print("=" * 78)

all_ok = True

for label, (inp, out) in ELECTRONIC.items():

    print()
    print("-" * 78)
    print(label)
    print("-" * 78)

    if not inp.exists():
        print("[FAIL] Input absent :", inp)
        all_ok = False
        continue

    if not out.exists():
        print("[FAIL] Output absent:", out)
        all_ok = False
        continue

    inp_text = read_text(inp)
    out_text = read_text(out)

    # Pour les inputs électroniques, on utilise leur géométrie explicite.
    cell, pos = extract_first_geometry(inp_text)

    ok, dc, dp = compare_geometry(
        relax_cell,
        relax_pos,
        cell,
        pos,
    )

    print("Input :", inp)
    print("Output:", out)
    print()
    print(f"Max CELL diff      : {dc:.12e} Å")
    print(f"Max POSITION diff  : {dp:.12e}")
    print(f"Tolerance          : {TOL:.1e}")

    if ok:
        print("[OK] Géométrie électronique = géométrie finale RELAX")
    else:
        print("[FAIL] Géométrie différente")
        all_ok = False

    job_done = bool(
        re.search(r"\bJOB DONE\b", out_text, re.I)
    )

    fatal = bool(
        re.search(
            r"(Error in routine|ERROR:|fatal error|"
            r"cannot open|stopping)",
            out_text,
            re.I,
        )
    )

    c_bands = len(
        re.findall(r"c_bands:", out_text, re.I)
    )

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        out_text,
        re.I,
    )

    print()
    print("JOB DONE          :", "YES" if job_done else "NO")
    print("Fatal/error marker:", "YES" if fatal else "NO")
    print("c_bands warnings  :", c_bands)

    if fermi:
        print("Fermi final       :", fermi[-1], "eV")
    else:
        print("Fermi final       : non trouvé")


# ----------------------------------------------------------------------
# 3. FINAL SYNTHESIS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("3. SYNTHÈSE")
print("=" * 78)

if all_ok:
    print("[OK] Provenance géométrique RELAX → NSCF/BANDS établie")
else:
    print("[WARN] Provenance géométrique non totalement établie")

print()
print("[INFO] Cette phase ne modifie aucun statut AIDA.")
print("[INFO] Elle ne conclut pas à une validation scientifique.")
print("[INFO] Elle vérifie uniquement la provenance géométrique et")
print("       l'état des sorties électroniques relaxées.")

print()
print("=" * 78)
print("PHASE 78.30 TERMINÉE — READ-ONLY")
print("=" * 78)
