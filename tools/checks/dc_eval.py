"""Independent DC evaluator for a comparator network.
Network JSON: {"inputs": {"a": {...alphabet...}}, "nodes": [{"name": "c1", "mode": "subtract"|"compare",
  "back": <src>, "sides": [<src>, <src>]}], "outputs": {"sum": <src>, "cout": <src>},
  "decode": {"sum": "level >= 10", "cout": "level >= 10"}, "encode": {"a": {"0": 0, "1": 15}, ...}}
<src> = {"const": k} | {"input": "a"} | {"node": "c1"} | null. Levels 0..15.
compare: 0 if back==0 or max(sides)>back else back; subtract: back-max(sides) with the same zero rules.
"""
import json, sys, itertools
def level(src, env):
    if src is None: return 0
    if 'const' in src: return int(src['const'])
    if 'input' in src: return env[src['input']]
    if 'node' in src: return env[src['node']]
    raise ValueError(src)
def run(net):
    order=[n['name'] for n in net['nodes']]
    rows=[]; ok_all=True
    for a,b,cin in itertools.product((0,1),repeat=3):
        env={'a':int(net['encode']['a'][str(a)]),'b':int(net['encode']['b'][str(b)]),'cin':int(net['encode']['cin'][str(cin)])}
        for n in net['nodes']:
            i=level(n['back'],env); j=max(level(s,env) for s in n.get('sides',[])) if n.get('sides') else 0
            v=0 if (i==0 or j>i) else (i-j if n['mode']=='subtract' else i)
            env[n['name']]=v
        s=level(net['outputs']['sum'],env); c=level(net['outputs']['cout'],env)
        ds=int(eval(net['decode']['sum'],{},{'level':s})); dc=int(eval(net['decode']['cout'],{},{'level':c}))
        ok=(a+b+cin==ds+2*dc); ok_all&=ok
        rows.append((a,b,cin,{k:env[k] for k in order},s,c,ds,dc,ok))
    return rows, ok_all
if __name__=='__main__':
    net=json.load(open(sys.argv[1],encoding='utf-8')); rows,ok=run(net)
    for r in rows: print(r)
    print('ALL PASS' if ok else 'FAIL')
