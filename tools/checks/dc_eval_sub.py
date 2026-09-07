"""Independent DC evaluator, generalized: relation and threshold from JSON.
net JSON adds: "inputs": ["a","b","bin"], "relation": "a - b - bin == d - 2*bout", "decode_threshold": 3, outputs {"d":..., "bout":...}
"""
import json, sys, itertools
def level(src, env):
    if src is None: return 0
    if 'const' in src: return int(src['const'])
    if 'input' in src: return env[src['input']]
    if 'node' in src: return env[src['node']]
    raise ValueError(src)
def run(net):
    ins=net['inputs']; thr=int(net.get('decode_threshold',5)); rows=[]; ok_all=True
    for bits in itertools.product((0,1),repeat=len(ins)):
        env={k:int(net['encode'][k][str(v)]) for k,v in zip(ins,bits)}
        for n in net['nodes']:
            i=level(n['back'],env); j=max(level(s,env) for s in n.get('sides',[])) if n.get('sides') else 0
            env[n['name']]=0 if (i==0 or j>i) else (i-j if n['mode']=='subtract' else i)
        outs={k:level(v,env) for k,v in net['outputs'].items()}
        dec={k:int(v>=thr) for k,v in outs.items()}
        scope=dict(zip(ins,bits)); scope.update(dec)
        ok=bool(eval(net['relation'],{},scope)); ok_all&=ok
        rows.append((bits,{n['name']:env[n['name']] for n in net['nodes']},outs,dec,ok))
    return rows, ok_all
if __name__=='__main__':
    net=json.load(open(sys.argv[1],encoding='utf-8')); rows,ok=run(net)
    for r in rows: print(r)
    print('ALL PASS' if ok else 'FAIL')
