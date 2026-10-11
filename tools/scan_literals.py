#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取 bundle 里疑似 UI 文案的字符串字面量。
用法: python scan_literals.py <bundle.js> <out.txt>
启发式: 含字母、可读英文形态、排除路径/URL/键名/标识符。
"""
import re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BUNDLE = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else None

d = open(BUNDLE, encoding='utf-8', errors='replace').read()

# 状态机抓单双引号字符串字面量（大文件上比回溯正则快几个数量级）
strs = set()
i, n = 0, len(d)
while i < n:
    c = d[i]
    if c in "'\"":
        j = i + 1
        buf = []
        while j < n:
            cj = d[j]
            if cj == '\\':
                buf.append(d[j:j + 2])
                j += 2
                continue
            if cj == c or cj == '\n':
                break
            buf.append(cj)
            j += 1
        if j < n and d[j] == c:
            s = ''.join(buf)
            if '\\' in s:
                try:
                    s = s.encode('utf-8').decode('unicode_escape')
                except Exception:
                    s = None
            if s is not None:
                strs.add(s)
            i = j + 1
        else:
            i += 1
    else:
        i += 1

def is_ui(s):
    if len(s) < 4 or len(s) > 160:
        return False
    if not re.search(r'[a-zA-Z]', s):
        return False
    # 必须含空格或整体是单词短语（多词优先）
    if ' ' not in s:
        # 单词型: 全大写缩写、驼峰、snake 都过滤，只留自然单词
        if not re.fullmatch(r'[A-Z][a-z]+|[a-z]+[A-Z][a-zA-Z]*|[A-Z]{2,}', s):
            return False
        return bool(re.fullmatch(r'[A-Z][a-z]{3,}|[A-Z]{2,}', s)) and s.lower() not in KEYWORDS
    # 路径/URL/协议/键名
    if re.search(r'[/\\]|https?:|\.js|\.css|\.json|\.png|\.svg|\.map|\$\{|#\{', s):
        return False
    if re.match(r'^[a-z][a-zA-Z]*\.[a-z][a-zA-Z.]+$', s):  # a.b.c 键
        return False
    if re.match(r'^[a-z]+\s+[a-z]+\s+[a-z]+', s) and s.islower() and 'the' not in s and 'to' not in s:
        pass  # 保留，可能是文案
    # 必须大部分是可读字符
    if sum(c.isalnum() or c in ' .,!?;:\'()[]{}-+/%&@#$_<>"“”‘’—–·×…' for c in s) < len(s) * 0.9:
        return False
    # 驼峰/键名形态过滤
    if re.fullmatch(r'[a-z]+[A-Z][a-zA-Z0-9]*(\s+\S+)?', s):
        return False
    return True

KEYWORDS = {'true','false','null','undefined','function','return','typeof','instanceof'}
ui = sorted(s for s in strs if is_ui(s))
if OUT:
    open(OUT, 'w', encoding='utf-8').write('\n'.join(ui) + '\n')
    print(len(ui), 'candidates ->', OUT)
else:
    print(len(ui))
