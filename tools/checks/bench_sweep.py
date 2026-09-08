"""Load a block list into capcell.Bench (parsing states ourselves) and sweep the 8 full-adder inputs (DC)."""
import json, sys, itertools, re
import os as _os
sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "llmgen"))
import capcell as CC, machine as M
ALIAS={"minecraft:smooth_stone":"minecraft:smooth_stone","minecraft:stone":"minecraft:smooth_stone","minecraft:gray_wool":"minecraft:smooth_stone","minecraft:white_wool":"minecraft:smooth_stone"}
def parse(s):
    m=re.match(r'(minecraft:[a-z_]+)(?:\[(.*)\])?$', s); name=m.group(1); props={}
    if m.group(2):
        for kv in m.group(2).split(','):
            k,v=kv.split('='); props[k]=v
    name=ALIAS.get(name,name)
    if name=="minecraft:comparator": props.setdefault("powered","false"); props.setdefault("mode","compare")
    if name=="minecraft:repeater": props.setdefault("powered","false"); props.setdefault("delay","1"); props.setdefault("locked","false")
    if name=="minecraft:lever": props.setdefault("powered","false"); props.setdefault("face","floor")
    if name=="minecraft:redstone_lamp": props.setdefault("lit","false")
    return name, props
def build(layout, pins):
    blocks={}; cells={}
    for r in layout["blocks"]:
        pos=tuple(r[:3]); name,props=parse(r[3]); blocks[pos]=(name,props); cells[pos]=r[3]
    for pos,st in pins.items():
        name,props=blocks[pos]; assert name=="minecraft:redstone_wire", (pos,name); props["power"]=str(st["power"])
    be=None
    if layout.get("barrels"):
        be={}
        for k,n in layout["barrels"].items():
            pos=tuple(int(v) for v in k.split(',')); n=int(n); items=[]
            while n>0:
                c=min(64,n); items.append({"id":"minecraft:cobblestone","count":c,"max_count":64}); n-=c
            be[pos]={"items":items}
    # pins are FLOORS (sources the circuit may raise), not held values: WORLD-4 p4 latch, 2026-09-08
    return CC.Bench(blocks, block_entities=be, floors={pos: int(st["power"]) for pos, st in pins.items()})
def read_out(b, pos):
    e=b.blocks.get(tuple(pos))
    if e is None: return None
    name,props=e
    if name==CC.DUST: return int(props["power"])
    if name==CC.COMPARATOR: return b.cmp_out[tuple(pos)]
    return None
def sweep(layout, lvl=5):
    rows=[]; ok_all=True
    for a,bb,c in itertools.product((0,1),repeat=3):
        pins={tuple(layout["inputs"][k]): {"power": v*lvl} for k,v in (("a",a),("b",bb),("cin",c))}
        b=build(layout, pins); rounds,converged=b.dc_solve()
        s=read_out(b, layout["outputs"]["sum"]); co=read_out(b, layout["outputs"]["cout"])
        ds=int(s is not None and s>=lvl); dc=int(co is not None and co>=lvl)
        ok=converged and (a+bb+c==ds+2*dc); ok_all&=ok
        rows.append((a,bb,c,'sum',s,'cout',co,'dec',ds,dc,'rounds',rounds,converged,ok))
    return rows, ok_all
if __name__=="__main__":
    layout=json.load(open(sys.argv[1],encoding="utf-8")); rows,ok=sweep(layout)
    for r in rows: print(r)
    print("ALL PASS" if ok else "FAIL")
