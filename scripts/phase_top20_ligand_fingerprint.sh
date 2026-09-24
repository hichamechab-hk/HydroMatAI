#!/usr/bin/env bash
set -euo pipefail

clear

ROOT="$HOME/HydroMatAI"
cd "$ROOT"

echo "=========================================================================="
echo "PHASE TOP20 — LIGAND FINGERPRINT + STRUCTURAL FAMILY AUDIT"
echo "=========================================================================="
echo "[INFO] READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucun fichier scientifique modifié"
echo

python - <<'PY'
from pathlib import Path
from collections import defaultdict
import re

BASE = Path("MOF_Library/MOFXDB_FULL/cif")

targets = {
"5064089":"0120263_hMOF-5064089.cif",
"5077530":"0130776_hMOF-5077530.cif",
"5075051":"0130762_hMOF-5075051.cif",
"5075162":"0130771_hMOF-5075162.cif",
"5075048":"0130770_hMOF-5075048.cif",
"5061451":"0120265_hMOF-5061451.cif",
"5061736":"0120267_hMOF-5061736.cif",
"5065876":"0123989_hMOF-5065876.cif",
"5065937":"0123991_hMOF-5065937.cif",
"5077648":"0130778_hMOF-5077648.cif",
"5065953":"0123992_hMOF-5065953.cif",
"5064231":"0120266_hMOF-5064231.cif",
"5061565":"0120264_hMOF-5061565.cif",
"5065829":"0124066_hMOF-5065829.cif",
"5065821":"0124061_hMOF-5065821.cif",
"5061585":"0120284_hMOF-5061585.cif",
"5065749":"0123996_hMOF-5065749.cif",
"28664":None,
"5076181":"0134359_hMOF-5076181.cif",
"30806":None,
}

def parse_atoms(path):
    lines=path.read_text(errors="ignore").splitlines()
    headers=[]
    start=None

    for i,l in enumerate(lines):
        if l.strip()=="loop_":
            h=[]
            j=i+1
            while j<len(lines) and lines[j].strip().startswith("_"):
                h.append(lines[j].strip().split()[0])
                j+=1
            req={
                "_atom_site_label",
                "_atom_site_type_symbol",
                "_atom_site_fract_x",
                "_atom_site_fract_y",
                "_atom_site_fract_z"
            }
            if req.issubset(h):
                headers=h
                start=j
                break

    if start is None:
        return []

    idx={x:i for i,x in enumerate(headers)}
    atoms=[]

    for l in lines[start:]:
        s=l.strip()
        if not s or s.startswith("_") or s=="loop_":
            break

        t=s.split()
        if len(t)<len(headers):
            continue

        try:
            atoms.append({
                "label":t[idx["_atom_site_label"]].strip("'\""),
                "el":re.sub(r"[^A-Za-z]","",t[idx["_atom_site_type_symbol"]]).capitalize(),
                "x":float(re.sub(r"\(.*?\)","",t[idx["_atom_site_fract_x"]])),
                "y":float(re.sub(r"\(.*?\)","",t[idx["_atom_site_fract_y"]])),
                "z":float(re.sub(r"\(.*?\)","",t[idx["_atom_site_fract_z"]]))
            })
        except:
            pass

    return atoms

def formula(atoms):
    c=defaultdict(int)
    for a in atoms:
        c[a["el"]]+=1
    order=["C","H","N","O","F","P","S","Cl","Br","I","Cu","Zn","Fe","Co","Ni","Mn"]
    out=[]
    for e in order:
        if c[e]:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    for e in sorted(c):
        if e not in order:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    return "".join(out)

print(f"{'RANK':<6}{'ID':<16}{'FILE':<38}{'FORMULA':<25}{'NAT':>6}{'Cu':>5}{'O':>5}{'C':>5}{'N':>5}")
print("-"*115)

for rank,cid in enumerate(targets,1):
    fname=targets[cid]

    if fname:
        path=BASE/fname
    else:
        # résolution stricte : aucun wildcard
        candidates=[p for p in BASE.glob("*.cif")
                     if re.search(rf"hMOF-{re.escape(cid)}(?:\.cif)?$",p.name)]
        path=candidates[0] if len(candidates)==1 else None

    if path is None or not path.exists():
        print(f"{rank:<6}{'hMOF-'+cid:<16}{'NOT RESOLVED':<38}")
        continue

    atoms=parse_atoms(path)

    counts=defaultdict(int)
    for a in atoms:
        counts[a["el"]]+=1

    print(
        f"{rank:<6}"
        f"{'hMOF-'+cid:<16}"
        f"{path.name:<38}"
        f"{formula(atoms):<25}"
        f"{len(atoms):>6}"
        f"{counts['Cu']:>5}"
        f"{counts['O']:>5}"
        f"{counts['C']:>5}"
        f"{counts['N']:>5}"
    )

print()
print("==========================================================================")
print("CONTRÔLE DES COLLISIONS")
print("==========================================================================")

for cid in ("28664","30806"):
    hits=[p.name for p in BASE.glob("*.cif")
          if re.search(rf"hMOF-{re.escape(cid)}(?:\.cif)?$",p.name)]
    print(f"hMOF-{cid}: {len(hits)} correspondance(s)")
    for x in hits:
        print("  ",x)

print()
print("==========================================================================")
print("FIN — READ-ONLY")
print("==========================================================================")
PY
