#!/usr/bin/env bash
set -euo pipefail
clear
cd "$HOME/HydroMatAI"

python - <<'PY'
from pathlib import Path
from collections import Counter,defaultdict
import re

BASE=Path("MOF_Library/MOFXDB_FULL/cif")

IDS=[
"5064089","5077530","5075051","5075162","5075048",
"5061451","5061736","5065876","5065937","5077648",
"5065953","5064231","5061565","5065829","5065821",
"5061585","5065749","28664","5076181","30806"
]

def find_file(cid):
    pat=re.compile(rf"(^|_)hMOF-{re.escape(cid)}\.cif$",re.I)
    hits=[p for p in BASE.glob("*.cif") if pat.search(p.name)]
    return hits

def parse_atoms(path):
    lines=path.read_text(errors="ignore").splitlines()
    headers=None
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

    if headers is None:
        return []

    ix={x:i for i,x in enumerate(headers)}
    atoms=[]

    for l in lines[start:]:
        s=l.strip()
        if not s or s.startswith("_") or s=="loop_":
            if s.startswith("_") or s=="loop_":
                break
            continue

        t=s.split()
        if len(t)<len(headers):
            continue

        try:
            label=t[ix["_atom_site_label"]].strip("'\"")
            el=re.sub(r"[^A-Za-z]","",t[ix["_atom_site_type_symbol"]]).capitalize()
            x=float(re.sub(r"\(.*?\)","",t[ix["_atom_site_fract_x"]]))
            y=float(re.sub(r"\(.*?\)","",t[ix["_atom_site_fract_y"]]))
            z=float(re.sub(r"\(.*?\)","",t[ix["_atom_site_fract_z"]]))
        except:
            continue

        atoms.append((label,el,x,y,z))

    return atoms

def formula(atoms):
    c=Counter(a[1] for a in atoms)
    order=["C","H","N","O","F","P","S","Cl","Br","I","Cu","Zn","Fe","Co","Ni","Mn"]
    out=[]
    for e in order:
        if c[e]:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    for e in sorted(c):
        if e not in order:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    return "".join(out)

print("="*120)
print("PHASE TOP20 — LIGAND FINGERPRINT V2")
print("="*120)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] Résolution stricte par nom hMOF-ID")
print()

families=defaultdict(list)

for rank,cid in enumerate(IDS,1):
    hits=find_file(cid)

    print(f"[{rank:02d}] hMOF-{cid}")

    if len(hits)==0:
        print("  STATUS : NOT FOUND")
        print()
        continue

    if len(hits)>1:
        print("  STATUS : AMBIGUOUS")
        for p in hits:
            print("   ",p.name)
        print()
        continue

    path=hits[0]
    atoms=parse_atoms(path)
    c=Counter(a[1] for a in atoms)

    f=formula(atoms)
    fam=(f,c["Cu"],c["O"],c["N"])

    families[fam].append(cid)

    print(f"  FILE     : {path.name}")
    print(f"  NAT      : {len(atoms)}")
    print(f"  FORMULA  : {f}")
    print(f"  Cu/O/C/N : {c['Cu']}/{c['O']}/{c['C']}/{c['N']}")
    print()

print("="*120)
print("FAMILLES DE COMPOSITION")
print("="*120)

for i,(fam,ids) in enumerate(families.items(),1):
    f,cu,o,n=fam
    print(f"FAMILY {i:02d}")
    print(f"  FORMULA : {f}")
    print(f"  Cu/O/N  : {cu}/{o}/{n}")
    print(f"  MEMBERS : "+", ".join("hMOF-"+x for x in ids))
    print()

print("="*120)
print("FIN — READ-ONLY")
print("="*120)
PY
