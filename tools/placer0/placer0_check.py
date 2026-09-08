"""PLACER-0 checker (DIRECTOR 8, 2026-09-08). Judges a SOLUTION for a PROBLEM on the Bench (rule replica), independent of any solver.
usage: python placer0_check.py problems.json <problem_name> solution.json [-v]
solution.json = {"blocks":[[x,y,z,state],...], "barrels":{"x,y,z":count}}   # only the cells the solver ADDS; composter[level=3] must be declared as barrel 247 for the Bench
Rules: solution cells must lie in bbox, not overlap fixed cells, not use forbidden cells, count <= max_blocks; pins and outputs are fixed wire cells.
Pass = for every combination of pin levels, every output wire reads exactly the expected level (eval of "expect" over pin names), Bench converged, lint L1/L2 = 0.
"""
import sys, json, itertools, os
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "checks"))   # bench_sweep, alu_check2
import bench_sweep as BS, alu_check2 as A
def check(prob, sol, verbose=False):
    (x0,y0,z0),(x1,y1,z1)=prob["bbox"]; fixed={tuple(r[:3]):r[3] for r in prob["fixed"]}
    forb={tuple(c) for c in prob.get("forbidden",[])}; errs=[]
    solc={}
    for r in sol["blocks"]:
        p=tuple(r[:3])
        if not (x0<=p[0]<=x1 and y0<=p[1]<=y1 and z0<=p[2]<=z1): errs.append(("outside bbox",p))
        if p in fixed: errs.append(("overlaps fixed",p))
        if p in forb: errs.append(("forbidden",p))
        if p in solc: errs.append(("duplicate",p))
        solc[p]=r[3]
    if len(solc)>prob["max_blocks"]: errs.append(("too many blocks",len(solc),">",prob["max_blocks"]))
    for k in (sol.get("barrels") or {}):   # hole closed 2026-09-08 (second reviewer): a solution barrel may not override a fixed barrel, and must sit on a solution barrel block
        if k in (prob.get("barrels") or {}): errs.append(("overrides fixed barrel",k))
        c=tuple(int(t) for t in k.split(","))
        if "barrel" not in solc.get(c,"") and "composter" not in solc.get(c,""): errs.append(("barrel count without a barrel block",k))
    if errs: return False, errs
    lay={"blocks":[[*p,s] for p,s in fixed.items()]+[[*p,s] for p,s in solc.items()],
         "barrels":{**(prob.get("barrels") or {}), **(sol.get("barrels") or {})}}
    lint=[w for w in A.lint(lay) if w[0].startswith(("L1","L2"))]
    if lint: return False, [("lint",)+w for w in lint]
    names=list(prob["pins"].keys()); combos=list(itertools.product(*[prob["pins"][n]["levels"] for n in names]))
    fails=[]
    for combo in combos:
        pins={tuple(prob["pins"][n]["cell"]):{"power":lv} for n,lv in zip(names,combo)}
        bench=BS.build(lay,pins); rnd,conv,conv_hot,diff=bench.dc_solve_both(); env=dict(zip(names,combo))
        if diff: print("BISTABLE",prob["name"],env,sorted(diff.items())[:4]); fails.append((env,"bistable",sorted(diff)[:4],None)); continue
        conv=conv and conv_hot
        for o in prob["outputs"]:
            got=int(bench.blocks[tuple(o["cell"])][1]["power"]); exp=int(eval(o["expect"],{"max":max,"min":min},env))
            ok=conv and got==exp
            if verbose or not ok: print(("ok  " if ok else "FAIL"),prob["name"],env,o["name"],"got",got,"expect",exp,"conv",conv)
            if not ok: fails.append((env,o["name"],got,exp))
    if fails: return False, fails
    # TIME clause (2026-09-08, after FEED-1's p4): drive the combos in order on ONE bench; after each change the
    # circuit must rest within T_BOUND gt AND rest at the DC solution of the new row. A latch rests at the wrong
    # value; a slow decay does not rest in time. Both are FAIL here, as they are in a 40 gt world regime.
    outs=[tuple(o["cell"]) for o in prob["outputs"]]; worst=0
    for src in combos:                      # every ordered pair (a -> b): both directions of every input are covered
        for combo in combos:
            if combo==src: continue
            pins0={tuple(prob["pins"][n]["cell"]):{"power":lv} for n,lv in zip(names,src)}
            bench=BS.build(lay,pins0); bench.dc_solve()
            env=dict(zip(names,combo)); vals={tuple(prob["pins"][n]["cell"]):lv for n,lv in zip(names,combo)}
            gt,rested,last=bench.settle_after(vals,outs,limit=T_BOUND); worst=max(worst,gt)
            exp=[int(eval(o["expect"],{"max":max,"min":min},env)) for o in prob["outputs"]]
            got=[int(bench.blocks[c][1]["power"]) for c in outs]
            if not rested or got!=exp:
                print("TIME",prob["name"],dict(zip(names,src)),"->",env,"rested",rested,"gt",gt,"got",got,"expect",exp); fails.append((env,"time",gt,got))
    if verbose: print("time: worst settle %d gt (bound %d)"%(worst,T_BOUND))
    return (not fails), fails
T_BOUND=40
if __name__=="__main__":
    probs={p["name"]:p for p in json.load(open(sys.argv[1]))}; prob=probs[sys.argv[2]]; sol=json.load(open(sys.argv[3]))
    ok,info=check(prob,sol,"-v" in sys.argv); print("PASS" if ok else "FAIL", prob["name"], "blocks", len(sol["blocks"]), "" if ok else info[:6])
