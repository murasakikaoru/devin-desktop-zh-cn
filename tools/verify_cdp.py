#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证: 通过 CDP 读测试页内容, 确认翻译生效且保护区不被误翻。"""
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from inject import WS  # 复用内置 ws 客户端

PORT = sys.argv[1] if len(sys.argv) > 1 else '9222'
targets = json.loads(urllib.request.urlopen('http://127.0.0.1:%s/json' % PORT).read().decode())
page = next(t for t in targets if t.get('type') == 'page' and 'test-page' in t.get('url', ''))
print('target:', page['url'])

EXPR = r"""JSON.stringify({
  text: document.body.innerText,
  ph: document.querySelector('input').placeholder,
  title: document.querySelector('input').title,
  ver: window.__devinZhVersion || null,
  protected: {
    agentMsg: document.querySelector('[data-message-author="devin"] span').textContent,
    userMsg: document.querySelector('[data-message-author="user"]').textContent,
    rowToolLabel: document.querySelector('[data-transcript-row-key="r1"] .tool-label').textContent,
    rowSpan: document.querySelector('[data-transcript-row-key="r3"] span').textContent,
    plan: document.querySelector('[data-testid="transcript-plan-content"] p').textContent,
    extName: document.querySelector('.extension-list-item .name').textContent,
    extDesc: document.querySelector('.extension-list-item .description').textContent,
    listRow: document.querySelector('.monaco-tl-row span').textContent,
    dynRow: (document.querySelector('#dynamic [data-transcript-row-key]')||{}).innerText || null,
    mktCard: (document.querySelector('[class*="grid-cols-["] > div')||{}).innerText || null,
    permLabel: Array.from(document.querySelectorAll('body > span')).map(e=>e.textContent).join('|'),
    agentDesc: (document.querySelector('.agent-list span')||{}).textContent || null
  },
  settings: Array.from(document.querySelectorAll('.settings-page > *')).map(e=>e.textContent||e.getAttribute('aria-label')).join('|')
})"""

ws = WS(page['webSocketDebuggerUrl'])
ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {
    'expression': EXPR,
    'returnByValue': True}}))
while True:
    msg = json.loads(ws.recv())
    if msg.get('id') == 1:
        v = msg['result'].get('result', {}).get('value')
        print(json.dumps(json.loads(v), ensure_ascii=False, indent=1))
        break
ws.close()
