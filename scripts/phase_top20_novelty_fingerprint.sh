#!/usr/bin/env bash
set -euo pipefail
clear
cd "$HOME/HydroMatAI"

python - <<'PY'
from pathlib import Path
from collections import Counter,defaultdict
from math import sqrt,cos,sin,pi
import re,hashlib

BASE=Path("MOF_Library/MOFXDB_FULL/cif")

IDS=[
"5064089","5077530","5075051","5075162","5075048",
"5061451","5061736","5065876","5065937","5077648",
"5065953","5064231","5061565","5065829","5065821",
"5061585","5065749","28664","5076181","30806"
]

def find_file(cid):
    hits=[p for p in BASE.glob("*.cif")
          if re.search(rf"(^|_)hMOF-{re.escape(cid)}\.cif$",p.name,re.I)]
    return hits[0] if len(hits)==1 else None

def getval(lines,key):
    for l in lines:
        s=l.strip()
        if s.startswith(key):
            z=s[len(key):].strip()
            if z:
                return z.split()[0].strip("'\"")
    return None

def cellmat(a,b,c,al,be,ga):
    al,be,ga=[x*pi/180 for x in (al,be,ga)]
    return (
      (a,b*cos(ga),c*cos(be)),
      (0,b*sin(ga),c*(cos(al)-cos(be)*cos(ga))/sin(ga)),
      (0,0,sqrt(max(0,c*c-(c*cos(be))**2-
                     (c*(cos(al)-cos(be)*cos(ga))/sin(ga))**2)))
    )

def dist(f1,f2,m):
    d=[f1[i]-f2[i] for i in range(3)]
    d=[x-round(x) for x in d]
    x=m[0][0]*d[0]+m[0][1]*d[1]+m[0][2]*d[2]
    y=m[1][0]*d[0]+m[1][1]*d[1]+m[1][2]*d[2]
    z=m[2][0]*d[0]+m[2][1]*d[1]+m[2][2]*d[2]
    return sqrt(x*x+y*y+z*z)

def parse(path):
    lines=path.read_text(errors="ignore").splitlines()

    vals=[]
    for k in ["_cell_length_a","_cell_length_b","_cell_length_c",
              "_cell_angle_alpha","_cell_angle_beta","_cell_angle_gamma"]:
        vals.append(float(getval(lines,k)))
    mat=cellmat(*vals)

    headers=None
    start=None

    for i,l in enumerate(lines):
        if l.strip()!="loop_":
            continue
        h=[]
        j=i+1
        while j<len(lines) and lines[j].strip().startswith("_"):
            h.append(lines[j].strip().split()[0])
            j+=1
        req={"_atom_site_label","_atom_site_type_symbol",
             "_atom_site_fract_x","_atom_site_fract_y","_atom_site_fract_z"}
        if req.issubset(h):
            headers=h
            start=j
            break

    ix={h:i for i,h in enumerate(headers)}
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
              "label":t[ix["_atom_site_label"]].strip("'\""),
              "el":re.sub(r"[^A-Za-z]","",
                    t[ix["_atom_site_type_symbol"]]).capitalize(),
              "f":tuple(float(re.sub(r"\(.*?\)","",t[ix[k]]))
                       for k in ["_atom_site_fract_x",
                                 "_atom_site_fract_y",
                                 "_atom_site_fract_z"])
            })
        except:
            pass

    return vals,mat,atoms

def formula(atoms):
    c=Counter(a["el"] for a in atoms)
    order=["C","H","N","O","F","P","S","Cl","Br","I",
           "Cu","Zn","Fe","Co","Ni","Mn"]
    out=[]
    for e in order:
        if c[e]:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    for e in sorted(c):
        if e not in order:
            out.append(e+(str(c[e]) if c[e]!=1 else ""))
    return "".join(out)

print("="*120)
print("PHASE NOVELTY-1 — TOP20 LIGAND / CONNECTIVITY FINGERPRINT")
print("="*120)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] PBC minimum-image")
print()

family=defaultdict(list)

for rank,cid in enumerate(IDS,1):
    path=find_file(cid)

    print(f"[{rank:02d}] hMOF-{cid}")

    if not path:
        print("  STATUS = NOT RESOLVED")
        print("-"*120)
        continue

    cell,mat,atoms=parse(path)
    cu=[a for a in atoms if a["el"]=="Cu"]
    O=[a for a in atoms if a["el"]=="O"]
    C=[a for a in atoms if a["el"]=="C"]
    N=[a for a in atoms if a["el"]=="N"]

    # Cu-O-C graph
    edges=[]
    carbox=[]

    for o in O:
        oo=[]
        for c in C:
            d=dist(o["f"],c["f"],mat)
            if d<=1.65:
                oo.append((d,c))
        if oo:
            oo.sort(key=lambda x:x[0])
            c=oo[0][1]
            edges.append((o["label"],c["label"],oo[0][0]))

    # group O by carbon
    byC=defaultdict(list)
    for ol,cl,d in edges:
        byC[cl].append((ol,d))

    for cl,os in byC.items():
        if len(os)>=2:
            carbox.append((cl,tuple(sorted(o for o,d in os))))

    # Cu environment signature
    cu_sig=[]
    for cu0 in cu:
        neigh=[]
        for o in O:
            d=dist(cu0["f"],o["f"],mat)
            if d<=2.20:
                neigh.append((o["label"],d))
        neigh.sort()
        cu_sig.append(tuple(x[0] for x in neigh))

    # normalized local graph signature
    graph=[]
    for c,(ols) in sorted(byC.items()):
        graph.append((len(ols),tuple(sorted(o for o,d in ols))))
    graph_txt=str(sorted((n,sorted(ol)) for _,ol in carbox for n in [len(ol)]))
    digest=hashlib.sha256(
        (formula(atoms)+"|"+graph_txt).encode()
    ).hexdigest()[:16]

    fam=(formula(atoms),len(cu),len(O),len(N))
    family[fam].append(cid)

    print(f"  FILE      = {path.name}")
    print(f"  FORMULA   = {formula(atoms)}")
    print(f"  NAT       = {len(atoms)}")
    print(f"  Cu/O/C/N  = {len(cu)}/{len(O)}/{len(C)}/{len(N)}")
    print(f"  O-C PAIRS = {len(edges)}")
    print(f"  C(O>=2)   = {len(carbox)}")
    print(f"  FINGERPRINT = {digest}")

    print("  CARBOXYLATE-LIKE C:")
    for cl,ols in sorted(carbox):
        print("    "+cl+" -> "+", ".join(
            f"{o} ({d:.3f} A)" for o,d in sorted(byC[cl])
        ))

    print("  Cu O-neighbor labels:")
    for i,sig in enumerate(cu_sig,1):
        print(f"    Cu{i}: "+", ".join(sig))

    print("-"*120)

print()
print("="*120)
print("FAMILIES — CANDIDATS À RECHERCHE BIBLIOGRAPHIQUE")
print("="*120)

for i,(fam,members) in enumerate(family.items(),1):
    print(f"FAMILY {i:02d}")
    print(f"  FORMULA : {fam[0]}")
    print(f"  MEMBERS : "+", ".join("hMOF-"+x for x in members))
    print()

print("="*120)
print("FIN — READ-ONLY")
print("="*120)
PY
