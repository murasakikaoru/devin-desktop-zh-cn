#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首次运行环境准备（幂等，可反复执行）:
1. ~/.devin/argv.json 写入 "locale": "zh-cn"（启用语言包）
2. 若语言包扩展未安装，调用 Devin.exe --install-extension 安装 vsix
用法: python setup.py [Devin.exe 路径]
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEVIN_DIR = os.path.join(os.environ.get('USERPROFILE', ''), '.devin')
ARGV = os.path.join(DEVIN_DIR, 'argv.json')
EXT_DIR = os.path.join(DEVIN_DIR, 'extensions')
VSIX = os.path.join(HERE, 'devin-language-pack-zh-hans-1.0.0.vsix')
PACK_MARK = 'devin-language-pack-zh-hans'


def _strip_jsonc(text):
    """剥离 JSONC 注释（// 行注释、/* */ 块注释），保留字符串字面量原样。
    Devin/VS Code 的 argv.json 允许注释，裸 json.load 会失败。"""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == '\\':
                if i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] not in '\r\n':
                i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            end = text.find('*/', i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def ensure_locale():
    cfg = {}
    if os.path.exists(ARGV):
        try:
            cfg = json.loads(_strip_jsonc(open(ARGV, encoding='utf-8-sig').read()))
        except Exception:
            # 文件损坏时先备份再覆写, 避免静默丢失原有配置
            try:
                shutil.copy2(ARGV, ARGV + '.bak')
                print('[devin-zh] argv.json 解析失败，已备份为 argv.json.bak')
            except Exception:
                pass
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    if cfg.get('locale') != 'zh-cn':
        cfg['locale'] = 'zh-cn'
        os.makedirs(DEVIN_DIR, exist_ok=True)
        with open(ARGV, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print('[devin-zh] argv.json 已设置 locale=zh-cn')


def ensure_language_pack(devin_exe):
    if os.path.isdir(EXT_DIR) and any(PACK_MARK in d for d in os.listdir(EXT_DIR)):
        return
    if not os.path.exists(VSIX):
        print('[devin-zh] 缺少语言包:', VSIX)
        return
    if not devin_exe or not os.path.exists(devin_exe):
        print('[devin-zh] 未找到 Devin.exe，跳过语言包安装（可稍后双击 vsix 手动安装）')
        return
    print('[devin-zh] 正在安装语言包扩展…')
    try:
        subprocess.run([devin_exe, '--install-extension', VSIX],
                       timeout=180, capture_output=True)
        print('[devin-zh] 语言包安装完成')
    except Exception as e:
        print('[devin-zh] 语言包安装失败:', e, '（不影响 Agent 界面汉化）')


if __name__ == '__main__':
    ensure_locale()
    ensure_language_pack(sys.argv[1] if len(sys.argv) > 1 else None)
