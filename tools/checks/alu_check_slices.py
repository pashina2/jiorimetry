"""n-slice ALU checker (DIRECTOR 8, 2026-09-08). A layout is a SLICE only if this passes for n = 1, 2, 3.
usage: python alu_check_slices.py layout.json [n] [-v]
layout.json = {"blocks":[[x,y,z,state],...], "barrels":{"x,y,z":count},
  "slice": {"pitch": PX,
            "through": {"P": [[x,y,z],...], "Wn": [[x,y,z],...]},   # entry wire cells of slice 0 (x side); slice i>0 gets them from slice i-1's exit
            "ports": {"a": [x,y,z], "b": [x,y,z], "k": [x,y,z], "r": [x,y,z], "f": [x,y,z]}}}   # per-slice cells (slice 0 frame); k of slice 0 is the only k pin; f = comparator of the top slice
Semantics (n bits, A/B/R n-bit, k carry-in, F carry-out; data level 0/3, decode >= 3):
  ADD (P=0, Wn=15): A + B + k == R + 2^n F    SUB (P=0, Wn=0): A - B - k == R - 2^n F
  AND (P=15, Wn=15): R == A & B, F == 0        OR (P=15, Wn=0): R == A | B, F == 0
All outputs must be exactly 0 or 3. Through-line integrity is implied: slice i>0 receives P / Wn / k only through the previous slice.
"""
import sys, json, itertools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_sweep as BS
MODES={"ADD":(0,15),"SUB":(0,0),"AND":(15,15),"OR":(15,0)}
def tiled(lay,n):
    PX=lay["slice"]["pitch"]; blocks=[]; barrels={}
    for i in range(n):
        for r in lay["blocks"]: blocks.append([r[0]+i*PX,r[1],r[2],r[3]])
        for k,v in (lay.get("barrels") or {}).items():
            x,y,z=(int(t) for t in k.split(',')); barrels["%d,%d,%d"%(x+i*PX,y,z)]=v
    return {"blocks":blocks,"barrels":barrels}
def read(bench,pos):
    e=bench.blocks.get(tuple(pos))
    if e is None: return None
    if e[0]=="minecraft:redstone_wire": return int(e[1]['power'])
    if e[0]=="minecraft:comparator": return bench.cmp_out.get(tuple(pos))
    return None
def run(lay,n,A,B,k,P,Wn):
    S=lay["slice"]; PX=S["pitch"]; T=tiled(lay,n); pins={}
    for key,lv in (("P",P),("Wn",Wn)):
        for c in S["through"][key]: pins[tuple(c)]={"power":lv}
    pins[tuple(S["ports"]["k"])]={"power":3*k}
    for i in range(n):
        for key,val in (("a",(A>>i)&1),("b",(B>>i)&1)):
            c=S["ports"][key]; pins[(c[0]+i*PX,c[1],c[2])]={"power":3*val}
    bench=BS.build(T,pins); rnd,conv,conv_hot,diff=bench.dc_solve_both()
    if diff: print("BISTABLE",{"A":A,"B":B,"k":k,"P":P,"Wn":Wn},sorted(diff.items())[:4]); conv=False
    conv=conv and conv_hot
    rs=[read(bench,(S["ports"]["r"][0]+i*PX,S["ports"]["r"][1],S["ports"]["r"][2])) for i in range(n)]
    f=read(bench,(S["ports"]["f"][0]+(n-1)*PX,S["ports"]["f"][1],S["ports"]["f"][2]))
    return rs,f,conv,bench
def check(lay,n,verbose=False):
    ok_n=0; tot=0; fails=[]
    for mode,(P,Wn) in MODES.items():
        for A in range(2**n):
            for B in range(2**n):
                for k in (0,1):
                    rs,f,conv,_=run(lay,n,A,B,k,P,Wn); tot+=1
                    clean=conv and all(r in (0,3) for r in rs) and f in (0,3)
                    R=sum(((r or 0)>=3)<<i for i,r in enumerate(rs)); F=int((f or 0)>=3)
                    if mode=="ADD": rel=(A+B+k)==(R+(2**n)*F)
                    elif mode=="SUB": rel=(A-B-k)==(R-(2**n)*F)
                    elif mode=="AND": rel=(R==(A&B) and F==0)
                    else: rel=(R==(A|B) and F==0)
                    ok=clean and rel; ok_n+=ok
                    if not ok: fails.append((mode,A,B,k,rs,f,conv))
                    if verbose or not ok: print(("ok  " if ok else "FAIL"),mode,"A",A,"B",B,"k",k,"r",rs,"f",f,"conv",conv)
    print("n=%d PASS %d/%d"%(n,ok_n,tot)); return ok_n==tot
if __name__=="__main__":
    lay=json.load(open(sys.argv[1],encoding="utf-8")); args=[a for a in sys.argv[2:] if a!="-v"]; n=int(args[0]) if args else 1
    check(lay,n,"-v" in sys.argv)
