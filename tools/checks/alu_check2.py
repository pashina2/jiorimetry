"""Generalized ALU-stage check + placement lint (DIRECTOR 8, 2026-09-08).
usage: python alu_check2.py layout.json [-v]
layout.json = {"blocks":[[x,y,z,"minecraft:..[props]"],...], "barrels":{"x,y,z":count},
               "pins":{"a":[[x,y,z],...],"b":[..],"k":[..],"P":[..],"Wn":[..]},   # every pin cell must be a redstone_wire
               "reads":{"r":[x,y,z],"f":[x,y,z]}}                                   # r/f = wire (power) or comparator (stored output)
Rows: 32 (ADD P=0 Wn=15 / SUB P=0 Wn=0 / AND P=15 Wn=15 / OR P=15 Wn=0), data 0/3, decode bit = level>=3, outputs must be exactly 0 or 3.
Lint (vanilla placement rules the Bench does not enforce):
  L1 every wire/comparator/repeater/standing torch needs a full block below (smooth_stone, barrel, redstone_block, other solid).
  L2 a y-level wire whose horizontal neighbour is air connects diagonally to the wire one level below at that neighbour (VERT-1) -> reported.
  L3 a wire directly adjacent to a solid that is the FRONT of a comparator/repeater (strong power) -> reported (info; may be intended).
"""
import sys, json, itertools, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_sweep as BS
OPS={"ADD":(0,15,"a + b + k == r + 2*f"),"SUB":(0,0,"a - b - k == r - 2*f"),"AND":(15,15,"r == (a and b) and f == 0"),"OR":(15,0,"r == (a or b) and f == 0")}
D={'north':(0,0,-1),'south':(0,0,1),'east':(1,0,0),'west':(-1,0,0)}
FULL={"minecraft:smooth_stone","minecraft:barrel","minecraft:redstone_block","minecraft:stone","minecraft:gray_wool","minecraft:white_wool"}
def name(s): return s.split('[')[0]
def facing(s): return s.split('facing=')[1].split(',')[0].split(']')[0] if 'facing=' in s else None
def lint(lay):
    B={tuple(r[:3]):r[3] for r in lay["blocks"]}; out=[]
    for p,s in sorted(B.items()):
        n=name(s)
        if n in ("minecraft:redstone_wire","minecraft:comparator","minecraft:repeater","minecraft:redstone_torch"):
            b=B.get((p[0],p[1]-1,p[2]))
            if b is None or name(b) not in FULL: out.append(("L1 no support",p,n,b))
    wires={p for p,s in B.items() if name(s)=="minecraft:redstone_wire"}
    for p in wires:
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            q=(p[0]+dx,p[1],p[2]+dz)
            if q not in B and (q[0],q[1]-1,q[2]) in wires: out.append(("L2 diagonal-down wire link",p,"->",(q[0],q[1]-1,q[2])))
            if (q[0],q[1]+1,q[2]) in wires and ((p[0],p[1]+1,p[2]) not in B or name(B[(p[0],p[1]+1,p[2])]) not in FULL): out.append(("L2 diagonal-up wire link",p,"->",(q[0],q[1]+1,q[2])))
    fronts={}
    for p,s in B.items():
        if name(s) in ("minecraft:comparator","minecraft:repeater"):
            d=D[facing(s)]; f=(p[0]-d[0],p[1],p[2]-d[2])
            if f in B and name(B[f]) in FULL: fronts[f]=p
    for p in wires:
        for dx,dy,dz in ((1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(0,1,0),(0,-1,0)):
            q=(p[0]+dx,p[1]+dy,p[2]+dz)
            if q in fronts: out.append(("L3 wire touches strongly-powered relay",p,"relay",q,"driven by",fronts[q]))
    return out
def read(bench,pos):
    pos=tuple(pos); e=bench.blocks.get(pos)
    if e is None: return None
    if e[0]=="minecraft:redstone_wire": return int(e[1]['power'])
    if e[0]=="minecraft:comparator": return bench.cmp_out.get(pos)
    return None
def run(lay,a,b,k,P,Wn):
    pins={}
    for key,lv in (("a",3*a),("b",3*b),("k",3*k),("P",P),("Wn",Wn)):
        for c in lay["pins"][key]: pins[tuple(c)]={"power":lv}
    bench=BS.build(lay,pins); rnd,conv=bench.dc_solve()
    return read(bench,lay["reads"]["r"]), read(bench,lay["reads"]["f"]), conv, bench
if __name__=="__main__":
    lay=json.load(open(sys.argv[1],encoding="utf-8")); verbose='-v' in sys.argv
    for w in lint(lay): print("LINT",*w)
    n=0; rows=[]
    for op,(P,Wn,rel) in OPS.items():
        for a,b,k in itertools.product((0,1),repeat=3):
            r,f,conv,_=run(lay,a,b,k,P,Wn); dr,df=int((r or 0)>=3),int((f or 0)>=3)
            ok=conv and r in (0,3) and f in (0,3) and bool(eval(rel,{},{"a":a,"b":b,"k":k,"r":dr,"f":df})); n+=ok
            rows.append([op,[a,b,k],r,f,bool(ok)])
            if not ok or verbose: print(("ok  " if ok else "FAIL"),op,(a,b,k),"r",r,"f",f,"conv",conv)
    print("PASS %d/32"%n)
    open(sys.argv[1]+".rows.json","wb").write(json.dumps(rows,indent=0).encode())
