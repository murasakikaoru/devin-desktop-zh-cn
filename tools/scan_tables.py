#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 bundle 中所有 JSON.parse(字面量) 大表，用于定位 i18next 资源表（混淆后变量名会变化）。"""
import re, json, codecs, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BUNDLE = os.environ.get('DEVIN_BUNDLE') or os.path.join(
    os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Devin',
    'resources', 'app', 'out', 'vs', 'workbench', 'windsurf-chat-client', 'index.js')
d = open(BUNDLE, encoding='utf-8', errors='replace').read()

def extract_at(i):
    j = d.find('JSON.parse(', i) + len('JSON.parse(')
    q = d[j]
    if q not in "'\"":
        return None
    k = j + 1
    esc = False
    while True:
        c = d[k]
        if esc:
            esc = False
        elif c == '\\':
            esc = True
        elif c == q:
            break
        k += 1
    try:
        raw = d[j + 1:k]
        dec = codecs.decode(raw.encode('utf-8'), 'unicode_escape')
        if isinstance(dec, bytes):
            dec = dec.decode('utf-8', 'replace')
        return json.loads(dec)
    except Exception:
        return None

def count(o):
    return sum(count(v) if isinstance(v, dict) else 1 for v in o.values())

big = []
for m in re.finditer(r'JSON\.parse\(', d):
    o = extract_at(m.start())
    if isinstance(o, dict):
        n = count(o)
        if n > 200:
            big.append((m.start(), n, len(o), o))
big.sort(key=lambda x: -x[1])
print('big tables (>200 leaves):', [(s, n, ns) for s, n, ns, _ in big[:10]])

if big:
    out = sys.argv[1] if len(sys.argv) > 1 else 'webapp-en.json'
    json.dump(big[0][3], open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('saved', out)
