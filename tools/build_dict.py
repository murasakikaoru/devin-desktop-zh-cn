#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 webapp-zh-*.json 人工翻译合并成 dict.json。

- dict: {en_text: zh_text} 精确匹配
- regex: 自动为含 {{var}} 的英文串生成 [pattern, replacement] —— {{x}} -> (.+?) 捕获组,
  中文译文里的 {{x}} 换成对应捕获组编号引用
"""
import glob
import json
import os
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return re.escape(s)


# 数字型占位符: 只匹配数字, 避免 'Permissions' 被 '{{count}}s' 的 (.+?)s$ 误吞
NUMERIC_VARS = {
    'count', 'seconds', 'minutes', 'hours', 'days', 'number', 'pullNumber',
    'issueNumber', 'stackNumber', 'sessionCount', 'totalCount', 'returnedCount',
    'filesProcessed', 'total', 'current', 'index', 'step', 'position',
    'queuePosition', 'level', 'tier', 'percent', 'thresholdPercent', 'max',
    'line', 'column', 'x', 'y', 'startX', 'startY', 'endX',
    'endY', 'passed', 'applicable', 'enabled', 'completed', 'retrieved',
    'evaluated', 'invoked', 'mapped', 'more', 'multiplier', 'credits',
}


def var_to_regex(en, zh):
    """'Added {{count}} secrets' -> ('^Added (\\d+) secrets$', '已添加 $1 个密钥')"""
    parts = re.split(r'\{\{(\w+)\}\}', en)
    # parts: [text, var, text, var, text...]
    pat = '^'
    zh_out = zh
    cap = 0
    for i, p in enumerate(parts):
        if i % 2 == 0:
            pat += esc(p)
        else:
            cap += 1
            # 占位符后面紧跟字母(如 '{{count}}s')时数字兜底, 否则 (.+?) 会吞掉边界
            pat += '(\\d[\\d.,]*)' if p in NUMERIC_VARS else '(.+?)'
            # 用哨兵占位: 先把所有 {{var}} 换掉, 再统一处理字面 $, 最后恢复成 $N
            zh_out = zh_out.replace('{{' + p + '}}', '\x00%d\x00' % cap)
    pat += '$'
    # JS replace 中 '$' 是特殊字符($N 反向引用/$$/$& 等): 译文里的字面 $ 必须写成 $$
    zh_out = zh_out.replace('$', '$$$$')
    zh_out = re.sub('\x00(\\d+)\x00', r'$\1', zh_out)
    return pat, zh_out


def norm_key(s):
    """去掉占位符与非单词字符后的归一化形式。

    若 en/zh 归一化后相同, 说明译文只是标点/空白级改写(如全角括号、
    连字符样式、{{a}}/{{b}} 恒等), 生成的正则不翻译任何内容却命中面过宽, 应跳过。
    """
    s = re.sub(r'\{\{\w+\}\}', '', s)
    return re.sub(r'[\W_]+', '', s)


def main():
    zh = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'webapp-zh-*.json'))):
        data = json.load(open(f, encoding='utf-8'))
        zh.update(data)
        print(os.path.basename(f), len(data))
    en_vals = set(open(os.path.join(HERE, 'webapp-visible-en.txt'), encoding='utf-8').read().splitlines())
    extra_files = glob.glob(os.path.join(HERE, 'webapp-zh-extra.json'))
    for f in extra_files:
        zh.update(json.load(open(f, encoding='utf-8')))

    d = {}
    rx = []
    skipped_tags = skipped_en = skipped_ident = 0
    for en, z in zh.items():
        if '<' in en and '>' in en:
            skipped_tags += 1  # Trans 组件拆分段, 渲染后不成整句, 跳过
            continue
        if '{{' in en:
            if norm_key(en) == norm_key(z):
                skipped_ident += 1  # 恒等/纯标点改写: 不产生翻译却过宽命中, 跳过
                continue
            en_vars = re.findall(r'\{\{(\w+)\}\}', en)
            zh_vars = set(re.findall(r'\{\{(\w+)\}\}', z))
            missing = [v for v in en_vars if v not in zh_vars]
            if missing:
                print('WARN unused vars %s: %s -> %s' % (missing, en[:60], z[:60]))
            extra = [v for v in zh_vars if v not in en_vars]
            if extra:
                print('WARN zh-only vars %s: %s -> %s' % (extra, en[:60], z[:60]))
            pat, zh_out = var_to_regex(en, z)
            # 完全由捕获组组成的正则(如 ^(.+?)$)会命中任意文本, 必须跳过
            body = pat.strip('^$').replace('(.+?)', '').replace('(\\d[\\d.,]*)', '')
            if not body:
                print('WARN all-wildcard pattern skipped: %s -> %s' % (en[:60], z[:60]))
                skipped_ident += 1
                continue
            rx.append((pat, zh_out))
            continue
        d[en] = z
        if en not in en_vals:
            skipped_en += 1
    out = {'dict': d, 'regex': rx}
    # dict.json 输出到上级目录（运行时目录，与 inject.py 同级）
    json.dump(out, open(os.path.join(HERE, '..', 'dict.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    # 报表: 可见集里还没翻译的
    untranslated = [v for v in en_vals if v not in zh]
    open(os.path.join(HERE, 'untranslated.txt'), 'w', encoding='utf-8').write('\n'.join(sorted(untranslated)))
    print(f'dict={len(d)} regex={len(rx)} skipped_tagged={skipped_tags} skipped_ident={skipped_ident} not_in_visible={skipped_en}')
    print(f'untranslated visible strings: {len(untranslated)} -> untranslated.txt')


if __name__ == '__main__':
    main()
