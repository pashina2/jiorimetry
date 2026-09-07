"""Independent DC evaluator for mixed-primitive networks (comparator / torch / repeater / wire max / const).
JSON: {"data": ["a","b","k"], "encode": {"a": {"0":0,"1":3}, ...}, "decode_threshold": 3,
       "ops": {"ADD": {"ctrl": {"s1": 0, "s0": 0}, "relation": "a + b + k == r + 2*f"}, ...},
       "nodes": [ {"name":..,"type":"comparator","mode":"subtract","back":src,"sides":[src,..]},
                  {"name":..,"type":"torch","input":src},  {"name":..,"type":"repeater","input":src},
                  {"name":..,"type":"wire","sources":[src,..],"loss":0} ],
       "outputs": {"r": src, "f": src}}
src = {"const":k} | {"input":"a"} | {"ctrl":"s1"} | {"node":"c1"} | null
"""
import json, sys, itertools
def lv(src, env):
    if src is None: return 0
    for key in ('const','input','ctrl','node'):
        if key in src: return int(src[key]) if key=='const' else env[src[key]]
    raise ValueError(src)
def evaluate(net, env):
    for n in net['nodes']:
        t=n.get('type','comparator')
        if t=='comparator':
            i=lv(n['back'],env); j=max((lv(s,env) for s in n.get('sides',[])), default=0)
            v=0 if (i==0 or j>i) else (i-j if n['mode']=='subtract' else i)
        elif t=='torch': v=15 if lv(n['input'],env)==0 else 0
        elif t=='repeater': v=15 if lv(n['input'],env)>0 else 0
        elif t=='wire': v=max(0, max((lv(s,env) for s in n['sources']), default=0)-int(n.get('loss',0)))
        else: raise ValueError(t)
        env[n['name']]=v
    return env
def run(net):
    data=net['data']; thr=int(net['decode_threshold']); rows=[]; npass=0; total=0
    for op,spec in net['ops'].items():
        for bits in itertools.product((0,1),repeat=len(data)):
            env={k:int(net['encode'][k][str(v)]) for k,v in zip(data,bits)}; env.update({k:int(v) for k,v in spec['ctrl'].items()})
            evaluate(net, env)
            outs={k:lv(v,env) for k,v in net['outputs'].items()}; dec={k:int(v>=thr) for k,v in outs.items()}
            scope=dict(zip(data,bits)); scope.update(dec); ok=bool(eval(spec['relation'],{},scope))
            total+=1; npass+=ok; rows.append((op,bits,outs,dec,ok))
    return rows, npass, total
if __name__=='__main__':
    net=json.load(open(sys.argv[1],encoding='utf-8')); rows,p,t=run(net)
    for r in rows:
        if not r[4] or '-v' in sys.argv: print(r)
    print('PASS %d/%d'%(p,t))
