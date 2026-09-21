#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Devin Desktop 中文注入器 — 通过 CDP 把 translator.js 注入所有页面/webview target。

用法:
    python inject.py [--port 9222] [--dict dict.json] [--translator translator.js]

无第三方依赖: 内置极简 WebSocket 客户端。
日志: %TEMP%\\devin-zh-injector.log
"""
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import time
import urllib.parse
import urllib.request

PORT = 9222
HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(HERE, 'dict.json')
TRANSLATOR_PATH = os.path.join(HERE, 'translator.js')
LOG = os.path.join(os.environ.get('TEMP', HERE), 'devin-zh-injector.log')
LOG_MAX = 1024 * 1024
WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def trim_log():
    """日志超过 LOG_MAX 时只保留后半段, 避免无限增长。"""
    try:
        if os.path.getsize(LOG) > LOG_MAX:
            with open(LOG, 'rb') as f:
                f.seek(-(LOG_MAX // 2), os.SEEK_END)
                tail = f.read()
            with open(LOG, 'wb') as f:
                f.write(b'... [truncated]\n' + tail)
    except Exception:
        pass


def log(*a):
    line = time.strftime('%H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


# ---------------- 极简 WebSocket 客户端 ----------------
class WS:
    def __init__(self, url, timeout=10):
        assert url.startswith('ws://')
        rest = url[5:]
        hostport, _, path = rest.partition('/')
        host, _, port = hostport.partition(':')
        port = int(port or 80)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f'GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n'
               f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
        self.sock.sendall(req.encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('ws handshake failed')
            resp += chunk
        status = resp.split(b'\r\n', 1)[0].split(b' ', 2)
        if len(status) < 2 or status[1] != b'101':
            raise ConnectionError('ws handshake rejected: ' + resp.split(b'\r\n', 1)[0].decode('latin1'))
        hdrs = {}
        for h in resp.split(b'\r\n')[1:]:
            if b':' in h:
                k, v = h.split(b':', 1)
                hdrs[k.strip().lower()] = v.strip()
        expect = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest())
        if hdrs.get(b'sec-websocket-accept') != expect:
            raise ConnectionError('ws bad Sec-WebSocket-Accept')
        # 握手完成后再恢复阻塞: create_connection 的 timeout 会留在 socket 上,
        # 若不恢复, CDP 空闲期 recv 每 10s 抛 socket.timeout -> 误判断连 -> 重连风暴
        self.sock.settimeout(None)
        self.buf = b''

    def send(self, text):
        data = text.encode('utf-8')
        header = bytearray([0x81])  # FIN + text
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack('>H', n)
        else:
            header.append(0x80 | 127)
            header += struct.pack('>Q', n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def _recv_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('ws closed')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        # 返回一条完整消息(自动拼分片); 响应 ping
        msg = b''
        while True:
            h = self._recv_exact(2)
            fin = h[0] & 0x80
            opcode = h[0] & 0x0F
            ln = h[1] & 0x7F
            if ln == 126:
                ln = struct.unpack('>H', self._recv_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack('>Q', self._recv_exact(8))[0]
            if h[1] & 0x80:
                mask = self._recv_exact(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._recv_exact(ln)))
            else:
                payload = self._recv_exact(ln)
            if opcode == 9:  # ping -> pong
                header = bytearray([0x8A, 0x80 | len(payload)])
                m = os.urandom(4)
                header += m
                self.sock.sendall(bytes(header) + bytes(b ^ m[i % 4] for i, b in enumerate(payload)))
                continue
            if opcode == 8:
                raise ConnectionError('ws close frame')
            if opcode in (1, 2, 0):
                msg += payload
                if fin:
                    return msg.decode('utf-8', 'replace')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ---------------- CDP ----------------
class CDP:
    def __init__(self, ws_url):
        self.ws = WS(ws_url)
        self.next_id = 1

    def send_cmd(self, method, params=None, session_id=None):
        mid = self.next_id
        self.next_id += 1
        msg = {'id': mid, 'method': method, 'params': params or {}}
        if session_id:
            msg['sessionId'] = session_id
        self.ws.send(json.dumps(msg))
        return mid


def load_payload():
    try:
        d = json.load(open(DICT_PATH, encoding='utf-8'))
    except Exception as e:
        log('dict.json load failed:', e)
        d = {}
    if not isinstance(d, dict):
        log('dict.json root is not an object, payload disabled')
        d = {}
    dd = d.get('dict', d)
    if not isinstance(dd, dict):
        dd = {}
    rx = d.get('regex', [])
    if not isinstance(rx, list):
        rx = []
    tjs = open(TRANSLATOR_PATH, encoding='utf-8').read()
    return ('window.__ZH_DICT__=' + json.dumps(dd, ensure_ascii=False) + ';'
            + 'window.__ZH_REGEX__=' + json.dumps(rx, ensure_ascii=False) + ';\n' + tjs)


def http_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def run(port):
    payload = load_payload()
    log('payload ready,', len(payload), 'bytes')
    injected = set()
    first_fail = None
    while True:
        cdp = None
        try:
            ver = http_json(f'http://127.0.0.1:{port}/json/version')
            cdp = CDP(ver['webSocketDebuggerUrl'])
            cdp.send_cmd('Target.setAutoAttach', {
                'autoAttach': True, 'waitForDebuggerOnStart': False, 'flatten': True})
            log('connected, autoAttach on')
            first_fail = None
            while True:
                raw = cdp.ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                method = msg.get('method')
                if method == 'Target.detachedFromTarget':
                    injected.discard(msg.get('params', {}).get('sessionId'))
                    continue
                if method != 'Target.attachedToTarget':
                    continue
                p = msg.get('params', {})
                sid = p.get('sessionId')
                tinfo = p.get('targetInfo', {})
                ttype, turl = tinfo.get('type', ''), tinfo.get('url', '')
                if ttype not in ('page', 'iframe', 'webview') or sid in injected:
                    continue
                if 'devtools' in turl:
                    continue
                # http(s) target: 只放行 Devin 自有域名(Agent 界面来自 app.devin.ai),
                # 其余远程内容(如应用内网页预览/第三方页面)不注入, 避免误翻用户页面
                if turl.startswith(('http://', 'https://')):
                    host = urllib.parse.urlparse(turl).hostname or ''
                    if host != 'devin.ai' and not host.endswith('.devin.ai'):
                        continue
                injected.add(sid)
                # 未来导航自动注入 + 立即对当前文档注入
                cdp.send_cmd('Page.enable', session_id=sid)
                cdp.send_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': payload}, session_id=sid)
                cdp.send_cmd('Runtime.evaluate', {
                    'expression': payload, 'awaitPromise': False,
                    'returnByValue': True}, session_id=sid)
                log('injected into', ttype, turl[:100])
        except Exception as e:
            log('conn lost:', e, '- retry in 2s')
            injected.clear()
            # Devin 关闭后端口长期不可达: 僵尸进程每 2s 重试到天荒地老没意义,
            # 连续失败 10 分钟视为 Devin 已退出, 自动收场(下次走 bat 会重启注入器)
            if first_fail is None:
                first_fail = time.time()
            elif time.time() - first_fail > 600:
                log('debug port unreachable for 10min, exit')
                return
            time.sleep(2)
        finally:
            if cdp is not None:
                cdp.ws.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    port = PORT
    if '--port' in args:
        port = int(args[args.index('--port') + 1])
    if '--dict' in args:
        DICT_PATH = args[args.index('--dict') + 1]
    if '--translator' in args:
        TRANSLATOR_PATH = args[args.index('--translator') + 1]
    trim_log()
    log('=== injector start, port', port)
    try:
        run(port)
    except KeyboardInterrupt:
        pass
