#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查候选字符串文件里哪些没被 dict.json 覆盖（精确键或 regex 命中）。"""
import json, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', 'dict.json'), encoding='utf-8'))
DICT = set(D['dict'].keys())
REGEX = [(re.compile(p), r) for p, r in D['regex']]

cands = [l.rstrip('\n') for l in open(sys.argv[1], encoding='utf-8')]
miss = []
for s in cands:
    s = s.strip()
    if not s or s in DICT:
        continue
    if any(p.match(s) for p, _ in REGEX):
        continue
    miss.append(s)

# 进一步过滤: 必须像 UI 文案——含空格+常见功能词 or 问号结尾 or 标题式
UI_HINT = re.compile(r"(?<![a-z])(the|to|and|or|for|with|your|you|a|an|is|are|in|of|on|will|can|not|new|all|no|yes|select|choose|click|press|open|save|create|delete|edit|view|show|hide|add|remove|enable|disable|update|install|manage|settings?|account|session|workspace|file|folder|project|branch|commit|search|sign|log|connect|run|stop|start|close|cancel|confirm|apply|retry|learn|more|help|about|copilot|agent|devin)\b", re.I)
real = [s for s in miss if (' ' in s and UI_HINT.search(s)) or s.endswith('?') or s.endswith('…')]

print('candidates:', len(cands), '| uncovered:', len(miss), '| plausible-UI:', len(real))
for s in real:
    print(' -', s)
