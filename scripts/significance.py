"""Bootstrap 95% CIs and exact McNemar tests for the MT-Bench run (960 records).
Usage: python scripts/significance.py <dir with results_2026*.json>
"""
import json,glob,sys,random
from math import comb
R={}
for f in sorted(glob.glob(sys.argv[1]+'/results_2026*.json')):
    if 'analysis' in f: continue
    for x in json.load(open(f)):
        if x['prompt_id'].startswith('mt-'): R.setdefault(x['method'],{})[x['prompt_id']]=x
ms=sorted(R); ids=sorted(set.intersection(*[set(R[m]) for m in ms])); print(len(ids),'prompts, methods',len(ms))
A={m:[1 if R[m][i]['apr'] else 0 for i in ids] for m in ms}
RAS={m:[R[m][i]['ras'] for i in ids] for m in ms}
random.seed(0)
def boot(v,n=10000):
    s=sorted(sum(random.choices(v,k=len(v)))/len(v) for _ in range(n)); return s[int(.025*n)],s[int(.975*n)]
def mcn(a,b):
    n10=sum(1 for x,y in zip(a,b) if x and not y); n01=sum(1 for x,y in zip(a,b) if y and not x); n=n10+n01
    if n==0: return n10,n01,1.0
    p=sum(comb(n,k) for k in range(0,min(n10,n01)+1))/2**n*2
    return n10,n01,min(1.0,p)
print('\nmethod  APR  95%CI  meanRAS')
for m in sorted(ms,key=lambda m:-sum(A[m])):
    lo,hi=boot(A[m]); print(f'{m:22s} {100*sum(A[m])/80:5.1f}  [{100*lo:.1f},{100*hi:.1f}]  {sum(RAS[m])/80:.3f}')
print('\nEFA vs other (exact McNemar): efa-only-wins, other-only-wins, p')
for m in ms:
    if m=='efa': continue
    print(f'{m:22s}',*mcn(A['efa'],A[m]))
