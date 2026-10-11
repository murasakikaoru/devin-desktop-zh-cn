import os
import json, io, sys, codecs
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BUNDLE = os.environ.get('DEVIN_BUNDLE') or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Devin', 'resources', 'app', 'out', 'vs', 'workbench', 'windsurf-chat-client', 'index.js')
d = open(BUNDLE, encoding='utf-8').read()

def extract(var):
    i = d.find('var ' + var + '=JSON.parse(')
    if i < 0:
        return None
    j = d.find('JSON.parse(', i) + len('JSON.parse(')
    q = d[j]
    assert q in "'\""
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
    raw = d[j+1:k]
    # decode JS string-literal escapes (\', \\, \n, \uXXXX, etc.)
    decoded = codecs.decode(raw.encode('utf-8'), 'unicode_escape')
    if isinstance(decoded, bytes):
        decoded = decoded.decode('utf-8', 'replace')
    return json.loads(decoded)

def count(o):
    return sum(count(v) if isinstance(v, dict) else 1 for v in o.values())

for var, out in [('UK', 'webapp-en.json'), ('UX', 'webapp-review-en.json')]:
    obj = extract(var)
    if obj is None:
        print(var, 'not found')
        continue
    print(var, '-> top namespaces:', len(obj), '| leaf strings:', count(obj))
    json.dump(obj, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('saved', out)
