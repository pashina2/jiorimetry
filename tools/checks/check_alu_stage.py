"""Resume check: load a placed ALU stage layout and run all 32 rows (r and f) on capcell.Bench.
usage: python check_alu_stage.py alu_stage_T6_30of32.json  (from this directory; needs bench_sweep.py beside it)
Pins: a=(4,1,4)+(8,1,5), b=(0,1,4), k=(0,1,2)  levels 0/3;  P=(0,1,0)+(0,1,8) 0/15;  Wn=(4,1,10) 15=ADD/AND, 0=SUB/OR.
Reads: r = wire (6,2,9) power; f = comparator F (8,1,2) stored output. Decode: bit = level >= 3."""
import sys, json, itertools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_sweep as BS
OPS={"ADD":(0,15,"a + b + k == r + 2*f"),"SUB":(0,0,"a - b - k == r - 2*f"),"AND":(15,15,"r == (a and b) and f == 0"),"OR":(15,0,"r == (a or b) and f == 0")}
def run(lay,a,b,k,P,Wn):
    pins={(0,1,2):{"power":3*k},(0,1,4):{"power":3*b},(4,1,4):{"power":3*a},(8,1,5):{"power":3*a},(0,1,0):{"power":P},(0,1,8):{"power":P},(4,1,10):{"power":Wn}}
    bench=BS.build(lay,pins); rnd,conv=bench.dc_solve()
    return int(bench.blocks[(6,2,9)][1]['power']), bench.cmp_out.get((8,1,2)), conv
if __name__=="__main__":
    lay=json.load(open(sys.argv[1],encoding="utf-8")); n=0
    for op,(P,Wn,rel) in OPS.items():
        for a,b,k in itertools.product((0,1),repeat=3):
            r,f,conv=run(lay,a,b,k,P,Wn); dr,df=int(r>=3),int(f>=3)
            ok=conv and bool(eval(rel,{},{"a":a,"b":b,"k":k,"r":dr,"f":df})) and r in (0,3) and f in (0,3); n+=ok
            if not ok: print("FAIL",op,(a,b,k),"r",r,"f",f,"conv",conv)
    print("PASS %d/32"%n)
