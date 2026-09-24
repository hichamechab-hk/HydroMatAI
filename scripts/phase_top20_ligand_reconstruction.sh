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
IDS=["5064089","5077530","5075051","5075162","5075048","5061451","5061736","5065876","5065937","5077648","5065953","5064231","5061565","5065829","5065821","5061585","5065749","28664","5076181","30806"]

def find(cid):
    x=[p for p in BASE.glob("*.cif") if re.search(r"(^|_)hMOF-"+cid+r"\.cif$",p.name,re.I)]
    return x[0] if len(x)==1 else None

def val(L,k):
    for x in L:
        if x.strip().startswith(k):
            return x.strip()[len(k):].split()[0].strip("'\"")

def mat(a,b,c,A,B,G):
    A,B,G=[x*pi/180 for x in (A,B,G)]
    return ((a,b*cos(G),c*cos(B)),(0,b*sin(G),c*(cos(A)-cos(B)*cos(G))/sin(G)),(0,0,sqrt(max(0,c*c-(c*cos(B))**2-(c*(cos(A)-cos(B)*cos(G))/sin(G))**2))))

def d(a,b,m):
    q=[a[i]-b[i] for i in range(3)]
    q=[x-round(x) for x in q]
    x=m[0][0]*q[0]+m[0][1]*q[1]+m[0][2]*q[2]
    y=m[1][0]*q[0]+m[1][1]*q[1]+m[1][2]*q[2]
    z=m[2][0]*q[0]+m[2][1]*q[1]+m[2][2]*q[2]
    return sqrt(x*x+y*y+z*z)

def parse(p):
    L=p.read_text(errors="ignore").splitlines()
    cell=[float(val(L,k)) for k in ["_cell_length_a","_cell_length_b","_cell_length_c","_cell_angle_alpha","_cell_angle_beta","_cell_angle_gamma"]]
    M=mat(*cell)
    H=None; S=None
    for i,x in enumerate(L):
        if x.strip()=="loop_":
            h=[]; j=i+1
            while j<len(L) and L[j].strip().startswith("_"):
                h.append(L[j].strip().split()[0]); j+=1
            req={"_atom_site_label","_atom_site_type_symbol","_atom_site_fract_x","_atom_site_fract_y","_atom_site_fract_z"}
            if req<=set(h): H=h; S=j; break
    ix={x:i for i,x in enumerate(H)}
    A=[]
    for x in L[S:]:
        if not x.strip() or x.strip().startswith("_") or x.strip()=="loop_": break
        t=x.split()
        if len(t)<len(H): continue
        try:
            A.append((t[ix["_atom_site_label"]].strip("'\""),re.sub(r"[^A-Za-z]","",t[ix["_atom_site_type_symbol"]]).capitalize(),tuple(float(re.sub(r"\(.*?\)","",t[ix[k]])) for k in ["_atom_site_fract_x","_atom_site_fract_y","_atom_site_fract_z"])))
        except: pass
    return M,A

def cutoff(a,b):
    p=tuple(sorted((a,b)))
    return {("C","C"):1.75,("C","N"):1.70,("C","O"):1.65,("C","H"):1.20,("N","H"):1.25,("O","H"):1.15}.get(p)

print("="*110)
print("PHASE NOVELTY-2A — LIGAND CONNECTIVITY")
print("="*110)
print("[INFO] READ-ONLY | Aucun pw.x | Aucun fichier scientifique modifié | PBC")
print()

families=defaultdict(list)

for rank,cid in enumerate(IDS,1):
    p=find(cid)
    print(f"[{rank:02d}] hMOF-{cid}")
    if not p:
        print("  STATUS = NOT RESOLVED"); continue

    M,A=parse(p)
    O=[x for x in A if x[1]=="O"]
    C=[x for x in A if x[1]=="C"]
    organic=[x for x in A if x[1] in {"C","N","O","H"}]

    edges=[]
    for i in range(len(organic)):
        for j in range(i+1,len(organic)):
            z=cutoff(organic[i][1],organic[j][1])
            if z and d(organic[i][2],organic[j][2],M)<=z:
                edges.append((i,j))

    adj=defaultdict(list)
    for i,j in edges:
        adj[i].append(j); adj[j].append(i)

    seen=set(); comps=[]
    for i in range(len(organic)):
        if i in seen: continue
        q=[i]; seen.add(i); c=[]
        while q:
            x=q.pop(); c.append(x)
            for y in adj[x]:
                if y not in seen: seen.add(y); q.append(y)
        comps.append(sorted(c))

    comps.sort(key=len,reverse=True)
    print(f"  FILE = {p.name}")
    print(f"  ORGANIC_ATOMS = {len(organic)}")
    print(f"  ORGANIC_BONDS = {len(edges)}")
    print(f"  COMPONENTS = {len(comps)}")

    for k,c in enumerate(comps[:4],1):
        cnt=Counter(organic[i][1] for i in c)
        f="".join(e+(str(cnt[e]) if cnt[e]!=1 else "") for e in ["C","H","N","O"] if cnt[e])
        labels=[organic[i][0] for i in c]
        sig=hashlib.sha256(("|".join(sorted(labels))+"|"+f).encode()).hexdigest()[:16]
        print(f"  COMPONENT {k}: NAT={len(c)} FORMULA={f} SIGNATURE={sig}")
        if k==1:
            for i in c:
                ns=[]
                for x,y in edges:
                    if x==i: ns.append(f"{organic[y][0]}({d(organic[i][2],organic[y][2],M):.3f})")
                    elif y==i: ns.append(f"{organic[x][0]}({d(organic[i][2],organic[x][2],M):.3f})")
                print(f"    {organic[i][0]}({organic[i][1]}) -> "+", ".join(sorted(ns)))
            families[sig].append(cid)
    print("-"*110)

print()
print("="*110)
print("LIGAND SIGNATURE FAMILIES")
print("="*110)
for n,(sig,members) in enumerate(families.items(),1):
    print(f"FAMILY {n:02d}  SIGNATURE={sig}")
    print("  MEMBERS = "+", ".join("hMOF-"+x for x in members))
print("="*110)
print("FIN — READ-ONLY")
print("="*110)
PY
