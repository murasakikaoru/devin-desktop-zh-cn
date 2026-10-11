#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确提取 UI 文案: label:"..."/title:"..."/placeholder/ariaLabel/description/message/tooltip/
children:"..."/header/subtitle/emptyText/confirmText/cancelText 等 prop 字符串值 + t("...") 调用。
用法: python scan_props.py <bundle.js> <out.txt>
"""
import re, sys, io, codecs
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

d = open(sys.argv[1], encoding='utf-8', errors='replace').read()
OUT = sys.argv[2]

PROPS = ('label', 'title', 'placeholder', 'description', 'message', 'ariaLabel', 'aria-label',
         'tooltip', 'header', 'subtitle', 'text', 'emptyText', 'confirmText', 'cancelText',
         'okText', 'children', 'tooltipText', 'helperText', 'hint', 'caption', 'badge',
         'displayName', 'buttonLabel', 'dialogTitle', 'successMessage', 'errorMessage',
         'loadingText', 'searchPlaceholder', 'inputPlaceholder', 'emptyTitle', 'emptyMessage',
         'confirmLabel', 'cancelLabel', 'primaryText', 'secondaryText', 'notFoundText')

pat = re.compile(r'''(?:''' + '|'.join(PROPS) + r''')\s*:\s*(['"`])((?:(?!\1).|\\.){2,160}?)\1''')
out = set()
for m in pat.finditer(d):
    s = m.group(2)
    if '\\' in s:
        try:
            s = s.encode('utf-8').decode('unicode_escape')
        except Exception:
            continue
    s = s.strip()
    if not s or not re.search(r'[a-zA-Z]', s):
        continue
    if re.search(r'[/\\]|https?:|\.(js|css|json|png|svg|map|ts)\b', s):
        continue
    if re.fullmatch(r'[a-z][a-zA-Z0-9.-]*', s):  # 单词键名/类名
        continue
    if '{{' in s or '${' in s:  # 含插值先跳过(单独处理)
        out.add('VAR::' + s)
        continue
    out.add(s)

# t("...") i18next 调用
for m in re.finditer(r'''\bt\(\s*(['"])((?:(?!\1).|\\.){2,160}?)\1\s*[,\)]''', d):
    s = m.group(2)
    if re.search(r'[a-zA-Z]', s) and ' ' in s and '/' not in s:
        out.add(s)

res = sorted(out)
open(OUT, 'w', encoding='utf-8').write('\n'.join(res) + '\n')
print(len(res), 'prop strings ->', OUT)
