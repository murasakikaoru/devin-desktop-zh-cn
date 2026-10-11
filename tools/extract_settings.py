#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 windsurf-chat-client bundle 提取 localSettings 及相关设置页字符串。"""
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BUNDLE = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Devin', 'resources', 'app', 'out', 'vs', 'workbench', 'windsurf-chat-client', 'index.js')
d = open(BUNDLE, encoding='utf-8', errors='replace').read()


def balanced(s, start):
    """从 start 处的 { 找配对 }, 返回子串(含括号)"""
    depth = 0
    i = start
    instr = False
    while i < len(s):
        c = s[i]
        if instr:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
        i += 1
    return None


KV = re.compile(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"')

# 1) localSettings 命名空间
out = {}
i = d.find('"localSettings":{')
obj = balanced(d, d.find('{', i + 15))
for k, v in KV.findall(obj):
    if len(v) > 1:
        out[v] = k
print('localSettings strings:', len(out))

# 2) 设置页字面量(非 i18n key 的 children:"..." 渲染)
for pat in ['"Current plan"', '"Open editor settings"', '"Daily quota usage"',
            '"Weekly quota usage"', '"Extra usage balance"', '"Purchase extra usage',
            '"Search settings"', '"Marketplace extension', '"Marketplace gallery']:
    for m in re.finditer(re.escape(pat), d):
        pass
# 直接找 quota/plan/marketplace 相关字面量
for m in re.finditer(r'"((?:Daily|Weekly) quota usage|Extra usage balance|Current plan|Open editor settings|General editor preferences[^"]*|Purchase extra usage[^"]*|Quota resets[^"]*|Plan ends[^"]*|Resets? [^"]{0,40}|Marketplace extension[^"]*|Marketplace gallery[^"]*|Search settings|Base URL[^"]*|Available[^"]{0,30}options|Restart Devin[^"]*)"', d):
    out[m.group(1)] = '(literal)'
print('total:', len(out))
json.dump(sorted(out), open('settings-strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for v in sorted(out):
    print(' ', v[:90])
