import pandas as pd
import os
from html import unescape

path = os.path.join(os.path.dirname(__file__), 'historico.xlsx')
print('reading', path)
if not os.path.exists(path):
    print('historico.xlsx not found')
    raise SystemExit(1)
df = pd.read_excel(path, header=None)
print('total rows in excel:', len(df))
primes = set([2,3,5,7,11,13,17,19,23])
valid_count = 0
invalid_count = 0
from collections import Counter
even_counter = Counter()
for idx, row in df.iterrows():
    vals = []
    for v in row.tolist():
        if pd.isna(v):
            continue
        try:
            iv = int(v)
            vals.append(iv)
        except Exception:
            try:
                parts = str(v).split(',')
                for p in parts:
                    p = p.strip()
                    if p:
                        vals.append(int(p))
            except Exception:
                pass
        if len(vals) >= 15:
            break
    if len(vals) < 15:
        invalid_count += 1
        continue
    first15 = [int(x) for x in vals[:15]]
    valid = all(1 <= n <= 25 for n in first15)
    if not valid:
        invalid_count += 1
        continue
    valid_count += 1
    even_count = sum(1 for n in first15 if n % 2 == 0)
    even_counter[even_count] += 1

print('valid rows:', valid_count)
print('invalid rows:', invalid_count)
print('even distribution:')
for k in sorted(even_counter):
    print(k, 'pares ->', even_counter[k])
print('sum valid counts:', sum(even_counter.values()))
