
"""RIG-1 build + Bench sweep (Fable worker, DIRECTOR 8, 2026-09-08).
Stage = alu_stage_v7.json (untouched, 2 floor cells cleared by the operator).
Rig = 5-lever feeder + 2 lamps.  Bench substitutions: composter[level=3] -> barrel 247, redstone_lamp -> smooth_stone."""
import json, sys, itertools, os
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "checks"))
import alu_check2 as AC, bench_sweep as BS
ORIGIN=(6005,133,-4113)
SS="minecraft:smooth_stone"; W="minecraft:redstone_wire"; COMP="minecraft:composter[level=3]"; LAMP="minecraft:redstone_lamp[lit=false]"
def LEV(f="north"): return "minecraft:lever[face=floor,facing=%s,powered=false]"%f
def C(f,m="compare"): return "minecraft:comparator[facing=%s,mode=%s]"%(f,m)
def R(f): return "minecraft:repeater[facing=%s,delay=1]"%f
stage=json.load(open(os.path.join(HERE,"..","..","artifacts","layouts","alu_stage_v7.json"),encoding="utf-8"))
S={tuple(r[:3]):r[3] for r in stage["blocks"]}
CLEAR=[(7,0,6),(8,0,7)]                      # stage floor cells the operator airs first (support nothing in v7)
DEMO={(-1,1,2):C("west"),(-2,1,2):"minecraft:barrel[facing=up,open=false]",(-1,0,2):SS,(4,1,11):SS,(4,2,11):LEV()}   # standing, not in the program
rig={}
def put(p,s):
    assert p not in rig,(p,s,rig[p]); rig[p]=s
# --- k: side wire + lever on the standing k comparator (-1,1,2) fW
put((-1,1,1),W); put((-1,0,1),SS); put((-2,1,1),SS); put((-2,2,1),LEV())
# --- b: gate (-1,1,4) fW, back composter (-2,1,4), side wire (-1,1,5), base (-2,1,5), lever (-2,2,5)
put((-1,1,4),C("west")); put((-1,0,4),SS); put((-2,1,4),COMP); put((-1,1,5),W); put((-1,0,5),SS); put((-2,1,5),SS); put((-2,2,5),LEV())
# --- a: one lever, base (12,1,5), lever (12,2,5); base strongly powers a3's side wire (11,1,5) and the wire (12,0,5) under it
put((12,1,5),SS); put((12,2,5),LEV())
#   a3: gate (11,1,4) fE, back composter (12,1,4), front = pin (10,1,4), side wire (11,1,5)
put((11,1,4),C("east")); put((11,0,4),SS); put((12,1,4),COMP); put((11,1,5),W); put((11,0,5),SS)
#   down to y=-1 without diagonals: (12,0,5) -> (12,0,6) -> repeater (12,0,7) fN -> strong solid (12,0,8) -> wire (12,-1,8) under it
put((12,0,5),W); put((12,-1,5),SS); put((12,0,6),W); put((12,-1,6),SS); put((12,0,7),R("north")); put((12,-1,7),SS); put((12,0,8),SS)
#   y=-1 run x=12..5 at z=8
for x in range(12,4,-1):
    put((x,-1,8),W); put((x,-2,8),SS)
#   a2: repeater (7,-1,7) fS -> strong solid (7,-1,6) -> side wire (7,0,6) above it [cleared]; gate (8,0,6) fS, back composter (8,0,7) [cleared], front = stage floor (8,0,5) -> pin (8,1,5)
put((7,-1,7),R("south")); put((7,-2,7),SS); put((7,-1,6),SS)
put((8,0,6),C("south")); put((8,-1,6),SS); put((8,0,7),COMP); put((7,0,6),W)
#   a1: repeater (5,-1,6) fS -> strong solid (5,-1,5) -> side wire (5,0,5) above it; gate (4,0,5) fS, back composter (4,0,6), front = stage floor (4,0,4) -> pin (4,1,4)
put((5,-1,7),W); put((5,-2,7),SS); put((5,-1,6),R("south")); put((5,-2,6),SS); put((5,-1,5),SS); put((5,0,5),W)
put((4,0,5),C("south")); put((4,-1,5),SS); put((4,0,6),COMP)
# --- P: one lever, base (-4,1,4), lever (-4,2,4); y=1 line x=-4 z=-1..3 and 5..8, rows z=-1 (x=-3..0) to pin (0,1,0) and z=8 (x=-3..-1) to pin (0,1,8)
put((-4,1,4),SS); put((-4,2,4),LEV())
for p in [(-4,1,z) for z in (-1,0,1,2,3,5,6,7,8)]+[(x,1,-1) for x in (-3,-2,-1,0)]+[(x,1,8) for x in (-3,-2,-1)]:
    put(p,W); put((p[0],0,p[2]),SS)
# --- lamps
put((6,2,10),LAMP); put((9,1,2),LAMP)
# --- collision checks
bad=[p for p in rig if p in S and p not in CLEAR]; assert not bad, bad
bad=[p for p in rig if p in DEMO]; assert not bad, bad
assert all(p in rig for p in CLEAR)
ys=[p[1] for p in rig]; assert min(ys)>=-3
# --- program (rig only)
blocks=[[*p,s] for p,s in sorted(rig.items())]
prog={"layout":"blocks","name":"alu_stage_v7_rig1","description":"RIG-1: 5-lever feeder (a,b,k,P + standing Wn) and r/f lamps for alu_stage_v7 at origin %s; stage cells excluded; operator clears (7,0,6),(8,0,7) first"%(ORIGIN,),"blocks":blocks}
mn=[min(p[i] for p in rig) for i in range(3)]
anchor=[ORIGIN[i]+mn[i] for i in range(3)]
# --- Bench layout: stage (minus cleared) + demo + rig, with substitutions
SUB={COMP:"minecraft:barrel[facing=up,open=false]",LAMP:SS}
full={p:s for p,s in S.items() if p not in CLEAR}; full.update(DEMO); full.update(rig)
lay={"blocks":[[*p,SUB.get(s,s)] for p,s in sorted(full.items())],
     "barrels":dict(stage["barrels"]),"pins":stage["pins"],"reads":stage["reads"],
     "levers":{"k":[-2,2,1],"b":[-2,2,5],"a":[12,2,5],"P":[-4,2,4],"Wn":[4,2,11]},
     "substitutions":{"%d,%d,%d"%p:{"program":s,"bench":SUB[s]} for p,s in sorted(full.items()) if s in SUB}}
lay["barrels"]["-2,1,2"]=247    # standing demo barrel: 5 bows = level 3; declared as 247 cobblestone (level 3) for the Bench
for p,s in full.items():
    if s==COMP: lay["barrels"]["%d,%d,%d"%p]=247
OPS=AC.OPS
def run(a,b,k,P,Wn):
    on={"a":a==0,"b":b==0,"k":k==0,"P":P==15,"Wn":Wn==15}     # data lever ON = bit 0; control lever ON = 15
    L=json.loads(json.dumps(lay))
    for nm,pos in L["levers"].items():
        i=[j for j,r in enumerate(L["blocks"]) if tuple(r[:3])==tuple(pos)][0]
        assert L["blocks"][i][3].startswith("minecraft:lever"),(nm,L["blocks"][i])
        L["blocks"][i][3]="minecraft:lever[face=floor,facing=north,powered=%s]"%("true" if on[nm] else "false")
    bench=BS.build(L,{}); rnd,conv=bench.dc_solve()
    return AC.read(bench,lay["reads"]["r"]),AC.read(bench,lay["reads"]["f"]),conv,on,bench
if __name__=="__main__":
    for w in AC.lint(lay): print("LINT",*w)
    ref=json.load(open(os.path.join(HERE,"..","..","artifacts","rows","alu_stage_v7.json.rows.json")))
    n=0; rows=[]; same=0
    for op,(P,Wn,rel) in OPS.items():
        for a,b,k in itertools.product((0,1),repeat=3):
            r,f,conv,on,bench=run(a,b,k,P,Wn); dr,df=int((r or 0)>=3),int((f or 0)>=3)
            ok=conv and r in (0,3) and f in (0,3) and bool(eval(rel,{},{"a":a,"b":b,"k":k,"r":dr,"f":df})); n+=ok
            rr=[x for x in ref if x[0]==op and x[1]==[a,b,k]][0]; same+=(rr[2]==r and rr[3]==f)
            sides={"k":bench.blocks[(-1,1,1)][1]["power"],"b":bench.blocks[(-1,1,5)][1]["power"],"a3":bench.blocks[(11,1,5)][1]["power"],"a2":bench.blocks[(7,0,6)][1]["power"],"a1":bench.blocks[(5,0,5)][1]["power"],"P1":bench.blocks[(0,1,0)][1]["power"],"P2":bench.blocks[(0,1,8)][1]["power"],"Wn":bench.blocks[(4,1,10)][1]["power"]}
            pins={key:[int(bench.blocks[tuple(c)][1]["power"]) for c in lay["pins"][key]] for key in lay["pins"]}
            rows.append({"op":op,"a":a,"b":b,"k":k,"P":P,"Wn":Wn,"levers_on":on,"r":r,"f":f,"r_lamp":bool((r or 0)>0),"f_lamp":bool((f or 0)>0),"ok":bool(ok),"converged":bool(conv),"pin_levels":pins,"side_levels":sides,"ref_r":rr[2],"ref_f":rr[3]})
            print(("ok  " if ok else "FAIL"),op,(a,b,k),"levers a%d b%d k%d P%d Wn%d"%tuple(int(on[x]) for x in "a b k P Wn".split()),"r",r,"f",f,"conv",conv,"pins",pins,"sides",sides)
    print("PASS %d/32  (r,f identical to pinned alu_check2 rows: %d/32)"%(n,same))
    out=os.path.join(HERE,sys.argv[1] if len(sys.argv)>1 else "rig1_full_bench.json")
    open(os.path.join(HERE,"rig1.program.json"),"wb").write(json.dumps(prog,indent=0).encode())
    lay2=dict(lay); lay2["rows"]=rows; lay2["pass"]="%d/32"%n; lay2["anchor_abs"]=anchor; lay2["origin_abs"]=list(ORIGIN); lay2["cleared_stage_cells"]=[list(p) for p in CLEAR]
    open(out,"wb").write(json.dumps(lay2,indent=0).encode())
    print("program blocks",len(blocks),"bbox min",mn,"anchor",anchor,"wrote",out)
