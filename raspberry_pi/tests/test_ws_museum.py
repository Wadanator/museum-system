#!/usr/bin/env python3
"""
Museum WebSocket Comprehensive Diagnostic v2
============================================
Testuje presne tie scenáre ktoré používateľ popisuje:
  1. Navigácia na Logy → prázdne logy
  2. Stop scény → tlačidlo ostane červené
  3. Navigácia naspäť na Dashboard → "Odpojené"
  4. LiveView nereaguje

Spustenie:
  python3 test_ws_full.py
  python3 test_ws_full.py --url http://192.168.1.x:5000 --user admin --pass admin
"""

import argparse
import base64
import json
import sys
import time
import threading
import urllib.request
import urllib.error

# ── Deps ──────────────────────────────────────────────────────────────────────
try:
    import socketio
except ImportError:
    print("CHYBA: pip3 install python-socketio websocket-client --break-system-packages")
    sys.exit(1)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--url',  default='http://localhost:5000')
parser.add_argument('--user', default='admin')
parser.add_argument('--pass', default='admin', dest='password')
parser.add_argument('--scene', default=None)
args = parser.parse_args()

BASE_URL  = args.url.rstrip('/')
AUTH_HDR  = 'Basic ' + base64.b64encode(f'{args.user}:{args.password}'.encode()).decode()

# ── Colors ────────────────────────────────────────────────────────────────────
GRN='\033[92m'; RED='\033[91m'; YEL='\033[93m'; BLU='\033[94m'
CYN='\033[96m'; DIM='\033[2m';  BOL='\033[1m';  RST='\033[0m'

def col(t, c): return c + str(t) + RST

# ── Result tracking ───────────────────────────────────────────────────────────
results = {}; total = 0; section_fails = {}

def header(title):
    print(f'\n{BOL}{BLU}{"─"*64}{RST}')
    print(f'{BOL}{BLU}  {title}{RST}')
    print(f'{BOL}{BLU}{"─"*64}{RST}')

def result(tid, name, status, detail=''):
    global total
    total += 1
    results[tid] = status
    icons = {'PASS': col('✓ PASS', GRN), 'FAIL': col('✗ FAIL', RED),
             'WARN': col('⚠ WARN', YEL), 'INFO': col('  INFO', DIM),
             'SKIP': col('  SKIP', DIM)}
    print(f'  {icons.get(status, status)}  {name}')
    if detail:
        for line in detail.strip().split('\n'):
            print(f'        {col(line, DIM)}')

def summary():
    p = sum(1 for v in results.values() if v=='PASS')
    f = sum(1 for v in results.values() if v=='FAIL')
    w = sum(1 for v in results.values() if v=='WARN')
    s = sum(1 for v in results.values() if v=='SKIP')
    print(f'\n{BOL}{"═"*64}{RST}')
    print(f'{BOL}  VÝSLEDKY: {col(f"{p} PASS",GRN)}  {col(f"{f} FAIL",RED)}  '
          f'{col(f"{w} WARN",YEL)}  {col(f"{s} SKIP",DIM)}  / {total} celkom{RST}')
    print(f'{BOL}{"═"*64}{RST}\n')

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def http(method, path, timeout=10):
    url = BASE_URL + path
    req = urllib.request.Request(url, method=method,
        headers={'Authorization': AUTH_HDR, 'Content-Type': 'application/json'},
        data=b'{}' if method=='POST' else None)
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ms = int((time.time()-t0)*1000)
            return {'ok': True, 'status': r.status,
                    'data': json.loads(r.read()), 'ms': ms}
    except urllib.error.HTTPError as e:
        body = {}
        try: body = json.loads(e.read())
        except: pass
        return {'ok': False, 'status': e.code, 'data': body, 'ms': 0}
    except Exception as e:
        return {'ok': False, 'status': -1, 'data': None, 'ms': 0, 'err': str(e)}

def http_get(path):  return http('GET', path)
def http_post(path): return http('POST', path)

# ── Socket helper ─────────────────────────────────────────────────────────────
class Sock:
    """Wrapper okolo python-socketio Client."""
    def __init__(self, label='sock'):
        self.label = label
        self.sio   = socketio.Client(logger=False, engineio_logger=False)
        self.events   = {}          # name → [{ts, data}]
        self.connected = False
        self.connect_ts = None
        self.sid = None
        self._lock = threading.Lock()
        self._register()

    def _store(self, ev, data):
        with self._lock:
            self.events.setdefault(ev, []).append({'ts': time.time(), 'data': data})

    def _register(self):
        @self.sio.event
        def connect():
            with self._lock:
                self.connected = True
                self.connect_ts = time.time()
                self.sid = self.sio.get_sid()
            self._store('connect', None)

        @self.sio.event
        def disconnect():
            with self._lock:
                self.connected = False
            self._store('disconnect', None)

        @self.sio.event
        def connect_error(data):
            self._store('connect_error', data)

        for ev in ['log_history','stats_update','status_update',
                   'new_log','scene_progress','logs_cleared']:
            self.sio.on(ev, lambda d, e=ev: self._store(e, d))

    def connect(self, timeout=8):
        try:
            self.sio.connect(BASE_URL, auth={'token': AUTH_HDR},
                transports=['websocket','polling'], wait_timeout=timeout)
            deadline = time.time() + timeout
            while not self.connected and time.time() < deadline:
                time.sleep(0.05)
            return self.connected
        except Exception:
            return False

    def disconnect(self):
        try: self.sio.disconnect()
        except: pass
        time.sleep(0.3)

    def emit(self, ev, data=None):
        try:
            self.sio.emit(ev) if data is None else self.sio.emit(ev, data)
        except Exception as e:
            self._store('emit_error', str(e))

    def wait(self, ev, timeout=5, after=None):
        """Čaká na event a vráti data alebo None."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for e in self.events.get(ev, []):
                    if after is None or e['ts'] >= after:
                        return e['data']
            time.sleep(0.05)
        return None

    def count_after(self, ev, ts):
        with self._lock:
            return sum(1 for e in self.events.get(ev, []) if e['ts'] >= ts)

    def last(self, ev):
        with self._lock:
            evs = self.events.get(ev, [])
            return evs[-1]['data'] if evs else None

    def last_ts(self, ev):
        with self._lock:
            evs = self.events.get(ev, [])
            return evs[-1]['ts'] if evs else None

    def all_after(self, ev, ts):
        with self._lock:
            return [e for e in self.events.get(ev, []) if e['ts'] >= ts]

# ══════════════════════════════════════════════════════════════════════════════
print(f'\n{BOL}{"═"*64}')
print(f'  Museum WebSocket Comprehensive Diagnostic v2')
print(f'  Backend: {BASE_URL}')
print(f'{"═"*64}{RST}')

# ── FÁZA 0: Backend dostupnosť ────────────────────────────────────────────────
header('FÁZA 0 │ Backend & Konfigurácia')

r = http_get('/api/status')
if not r['ok']:
    result('backend', 'Backend dostupný', 'FAIL',
           f"HTTP {r['status']} – spusti backend pred testom")
    sys.exit(1)

d = r['data']
ROOM_ID = d.get('room_id', 'Unknown')
result('backend', 'Backend dostupný', 'PASS',
       f"room_id={ROOM_ID}  mqtt={d.get('mqtt_connected')}  [{r['ms']}ms]")

r2 = http_get('/api/scenes')
scenes = r2['data'] if r2['ok'] and isinstance(r2['data'], list) else []
SCENE = args.scene
if not SCENE:
    SCENE = scenes[0]['name'] if scenes else None
    # Pokús sa nájsť krátku test scénu
    for s in scenes:
        if 'test' in s['name'].lower():
            SCENE = s['name']
            break

result('scenes', f'Scény ({len(scenes)} nájdených)', 'PASS' if scenes else 'WARN',
       f"Testovacia scéna: {SCENE}")

r3 = http_get('/api/config/main_scene')
MAIN_SCENE = r3['data'].get('json_file_name', '?') if r3['ok'] else '?'
result('main-scene', f'Hlavná scéna: {MAIN_SCENE}', 'PASS' if r3['ok'] else 'WARN')

# ── FÁZA 1: Základné Socket.IO spojenie ───────────────────────────────────────
header('FÁZA 1 │ Základné Socket.IO Spojenie')

sock = Sock('primary')
t0 = time.time()
connected = sock.connect(timeout=10)
conn_ms = int((time.time()-t0)*1000)

if not connected:
    result('connect', 'Pripojenie', 'FAIL',
           'Nedá sa pripojiť. Skontroluj:\n'
           '  • Backend beží na ' + BASE_URL + '\n'
           '  • pip3 install websocket-client')
    summary()
    sys.exit(1)

result('connect', 'Socket.IO connect()', 'PASS', f'Pripojené za {conn_ms}ms  SID={sock.sid}')
time.sleep(1.5)  # Čakaj na server eventy

# ── FÁZA 2: Server → Client pri CONNECT ──────────────────────────────────────
header('FÁZA 2 │ Server posiela dáta pri CONNECT\n'
       '        (root cause #1: toto musí fungovať aj po navigácii)')

for ev, name, field in [
    ('log_history',   'log_history doručený',   None),
    ('status_update', 'status_update doručený',  'scene_running'),
    ('stats_update',  'stats_update doručený',   'total_scenes_played'),
]:
    d = sock.last(ev)
    ts = sock.last_ts(ev)
    if d is not None:
        delay_ms = int((ts - sock.connect_ts)*1000) if sock.connect_ts else '?'
        extra = f'{field}={d.get(field)}  ' if field and isinstance(d, dict) else ''
        count = f'{len(d)} záznamov  ' if isinstance(d, list) else ''
        result(f'init-{ev}', name, 'PASS',
               f'{count}{extra}delay od connect: {delay_ms}ms')
    else:
        result(f'init-{ev}', name, 'FAIL',
               f'Server NEPOSLAL {ev} po connect!\n'
               f'→ Navigácia na stránku nenačíta dáta bez F5\n'
               f'→ Fix: dashboard.py handle_connect() musí emitovať {ev}')

# Všetky 3 naraz
all3 = [sock.last_ts(e) for e in ['log_history','status_update','stats_update']
        if sock.last_ts(e)]
if len(all3) == 3:
    spread = int((max(all3)-min(all3))*1000)
    st = 'PASS' if spread < 500 else 'WARN'
    result('init-timing', f'Všetky 3 eventy timing (spread={spread}ms)', st,
           'OK – server ich poslal takmer súčasne' if spread<500
           else f'POZOR – spread {spread}ms môže spôsobiť race condition')

# ── FÁZA 3: Client → Server REQUEST eventy ───────────────────────────────────
header('FÁZA 3 │ request_* Eventy (klient → server)\n'
       '        (root cause: ak toto nefunguje, navigácia vždy zobrazí prázdne dáta)')

print(f'\n  {DIM}Testuje sa: klient emituje request_*, server musí odpovedať emit-om{RST}')
print(f'  {DIM}Toto simuluje správanie React komponentu pri mount-nutí{RST}\n')

req_results = {}
for req_ev, resp_ev, label in [
    ('request_logs',   'log_history',   'LogsView mount → request_logs → log_history'),
    ('request_status', 'status_update', 'Dashboard mount → request_status → status_update'),
    ('request_stats',  'stats_update',  'StatsView mount → request_stats → stats_update'),
]:
    sent_ts = time.time()
    sock.emit(req_ev)
    data = sock.wait(resp_ev, timeout=4, after=sent_ts)
    elapsed = int((time.time()-sent_ts)*1000)

    if data is not None:
        resp_ts = sock.last_ts(resp_ev)
        resp_ms = int((resp_ts - sent_ts)*1000) if resp_ts else '?'
        result(f'req-{req_ev}', label, 'PASS', f'Odpoveď za {resp_ms}ms')
        req_results[req_ev] = 'ok'
    else:
        result(f'req-{req_ev}', label, 'FAIL',
               f'Žiadna odpoveď do 4s!\n'
               f'→ Toto JE root cause prázdnych Logov a "Odpojené" na Dashboard-e\n'
               f'→ Keď React naviguje na stránku, komponent emituje {req_ev}\n'
               f'→ Ak server neodpovie, stránka ostane prázdna (nie prázdna socket-om, '
               f'ale tým, že handler nefunguje)\n'
               f'→ Fix: dashboard.py handler pre "{req_ev}" musí volať emit("{resp_ev}", ...)\n'
               f'→ Skontroluj: je {req_ev} handler registrovaný PRED socket.run()?')
        req_results[req_ev] = 'fail'
    time.sleep(0.2)

# Detailná diagnostika ak request_* nefunguje
if any(v == 'fail' for v in req_results.values()):
    print(f'\n  {YEL}⚠ DIAGNOSTIKA request_* failure:{RST}')
    print(f'  {DIM}Možné príčiny:{RST}')
    print(f'  {DIM}  A) Handler nie je zaregistrovaný (@socketio.on nie je volaný){RST}')
    print(f'  {DIM}  B) emit() v handleri zlyháva (import issue alebo kontext){RST}')
    print(f'  {DIM}  C) Autentifikácia blokuje event (auth check na každý event){RST}')
    print(f'  {DIM}  D) Threading issue (handler beží ale emit sa nedoručí){RST}')

    # Test či server aspoň prijíma event (overíme cez nový log)
    print(f'\n  {DIM}Testujem či server handler vôbec beží...{RST}')
    before_logs = len(sock.events.get('new_log', []))
    sock.emit('request_logs')
    time.sleep(1)
    after_logs = len(sock.events.get('new_log', []))
    if after_logs > before_logs:
        result('req-handler-runs', 'Handler beží (nové logy)', 'WARN',
               'Handler beží ale emit() log_history nefunguje → threading/context bug')
    else:
        result('req-handler-runs', 'Handler beží?', 'WARN',
               'Nedá sa overiť zo strany klienta')

# ── FÁZA 4: Simulácia React SPA Navigácie ────────────────────────────────────
header('FÁZA 4 │ Simulácia React SPA Navigácie\n'
       '        (PRESNE čo sa deje keď user naviguje medzi stránkami)')

print(f'\n  {DIM}Toto simuluje: Dashboard → kliknutie na Logy → kliknutie na Dashboard{RST}\n')

# 4A: "Navigácia" = komponent sa unmount-ne a mount-ne znova
# V React socket NEODPOJUJE pri navigácii! Zostane connected.
# Ale komponent znova emituje request_* aby dostal aktuálne dáta.

print(f'  {DIM}KROK 1: Simulácia → komponent Logy sa mount-ne (socket zostáva connected){RST}')
logs_request_ts = time.time()
sock.emit('request_logs')
logs_data = sock.wait('log_history', timeout=4, after=logs_request_ts)

if logs_data is not None:
    result('nav-logs-mount', 'LogsView mount – logy dostupné', 'PASS',
           f'{len(logs_data) if isinstance(logs_data, list) else "?"} záznamov\n'
           f'→ Navigácia na Logy bude fungovať bez F5 ✓')
else:
    result('nav-logs-mount', 'LogsView mount – logy dostupné', 'FAIL',
           'request_logs neodpovedá → Logy budú prázdne po navigácii!\n'
           '→ Presne tento bug user popisuje')

time.sleep(0.3)
print(f'  {DIM}KROK 2: Simulácia → komponent Dashboard sa mount-ne{RST}')
dash_request_ts = time.time()
sock.emit('request_status')
status_data = sock.wait('status_update', timeout=4, after=dash_request_ts)

if status_data is not None:
    rid = status_data.get('room_id', '?')
    result('nav-dash-mount', 'Dashboard mount – status dostupný', 'PASS',
           f'room_id={rid}  scene_running={status_data.get("scene_running")}\n'
           f'→ Dashboard zobrazí správny stav bez F5 ✓')
else:
    result('nav-dash-mount', 'Dashboard mount – status dostupný', 'FAIL',
           'request_status neodpovedá!\n'
           '→ Dashboard ukáže "Odpojené" a prázdne room_id po navigácii\n'
           '→ Presne tento bug user popisuje')

# ── FÁZA 5: Skutočná Reconnect Simulácia (F5 ekvivalent) ─────────────────────
header('FÁZA 5 │ Skutočný Reconnect (F5 ekvivalent)\n'
       '        (nový socket objekt = čo sa deje pri F5)')

sock2 = Sock('reconnect')
print(f'  {DIM}Odpájam starý socket, vytváram nový (= F5 v prehliadači)...{RST}')
sock.disconnect()
time.sleep(0.5)
reconn_ts = time.time()
ok = sock2.connect(timeout=8)

if not ok:
    result('reconn', 'Reconnect (F5)', 'FAIL', 'Nedá sa pripojiť')
else:
    result('reconn', 'Reconnect (F5)', 'PASS')
    time.sleep(2)

    for ev, name in [
        ('log_history',   'log_history po F5 (Logy funkčné)'),
        ('status_update', 'status_update po F5 (Dashboard funkčný)'),
        ('stats_update',  'stats_update po F5 (Stats funkčné)'),
    ]:
        d = sock2.wait(ev, timeout=1, after=reconn_ts)
        if d is not None:
            result(f'reconn-{ev}', name, 'PASS', 'Server poslal dáta pri connect ✓')
        else:
            result(f'reconn-{ev}', name, 'FAIL',
                   f'Server neposlal {ev} pri reconnect\n'
                   f'→ Toto spôsobuje prázdne dáta po F5')

sock = sock2  # Ďalej používame nový socket

# ── FÁZA 6: Scéna Lifecycle – Broadcast Diagnostika ──────────────────────────
header('FÁZA 6 │ Scéna Lifecycle – Broadcast Analýza\n'
       '        (Stop button bug + LiveView bug)')

if not SCENE:
    for tid in ['scene-start','scene-running-broadcast','scene-progress',
                'scene-stop','scene-stop-broadcast','btn-fix']:
        result(tid, f'Scene test ({tid})', 'SKIP', 'Žiadna scéna')
else:
    print(f'  {DIM}Testovaná scéna: {SCENE}{RST}')

    # Zastav prípadne bežiacu scénu
    http_post('/api/stop_scene')
    time.sleep(1.5)

    # ── 6A: START scény ──
    pre_start = time.time()
    r = http_post(f'/api/run_scene/{SCENE}')

    if r['ok']:
        result('scene-start', f'POST /run_scene/{SCENE}', 'PASS', f'[{r["ms"]}ms]')
    elif r['status'] == 400:
        result('scene-start', f'POST /run_scene/{SCENE}', 'WARN',
               f'HTTP 400 – scéna možno beží [{r["ms"]}ms]')
    else:
        result('scene-start', f'POST /run_scene/{SCENE}', 'FAIL',
               f'HTTP {r["status"]}')

    # Čakaj na status_update s scene_running=True
    su_start = sock.wait('status_update', timeout=6, after=pre_start)
    n_start = sock.count_after('status_update', pre_start)

    if su_start and isinstance(su_start, dict) and su_start.get('scene_running'):
        result('scene-running-broadcast', 'status_update po START (scene_running=True)', 'PASS',
               f'{n_start}x status_update prijatý ✓')
    elif n_start > 0:
        last_su = sock.last('status_update')
        result('scene-running-broadcast', 'status_update po START', 'WARN',
               f'{n_start}x status_update ale scene_running='
               f'{last_su.get("scene_running") if last_su else "?"}')
    else:
        result('scene-running-broadcast', 'status_update po START', 'FAIL',
               'Žiadny status_update po štarte!\n'
               '→ UI nebude vedieť že scéna beží\n'
               '→ Fix: main.py _initiate_scene_start() → broadcast_status()')

    # ── 6B: scene_progress (LiveView) ──
    prog = sock.wait('scene_progress', timeout=5, after=pre_start)
    prog_count = sock.count_after('scene_progress', pre_start)

    if prog_count > 0:
        result('scene-progress', f'scene_progress eventy ({prog_count}x)', 'PASS',
               f'LiveView bude sledovať stavy v reálnom čase ✓\n'
               f'activeState={prog.get("activeState") if prog else "?"}')
    else:
        result('scene-progress', 'scene_progress eventy', 'WARN',
               'Žiadny scene_progress – scéna nemá stavy alebo skončila rýchlo\n'
               '→ LiveView nebude zobrazovať aktívny stav\n'
               '→ Skontroluj: state_machine.on_state_change je napojený na socketio.emit')

    # ── 6C: STOP scény – najdôležitejší test ──
    print(f'\n  {DIM}Čakám 2s pred STOP-om...{RST}')
    time.sleep(2)

    # KĽÚČOVÝ MOMENT: zaznamenám čas tesne pred STOP
    pre_stop = time.time()
    r2 = http_post('/api/stop_scene')
    stop_ms = r2['ms']

    if r2['ok']:
        result('scene-stop', 'POST /stop_scene', 'PASS', f'HTTP 200 [{stop_ms}ms]')
    else:
        result('scene-stop', 'POST /stop_scene', 'FAIL', f'HTTP {r2["status"]}')

    # KRITICKÝ TEST: Príde status_update s scene_running=False po STOP?
    su_stop = sock.wait('status_update', timeout=8, after=pre_stop)
    n_stop  = sock.count_after('status_update', pre_stop)
    time.sleep(1)
    n_stop2 = sock.count_after('status_update', pre_stop)
    last_su = sock.last('status_update')

    if n_stop2 > 0:
        sr = last_su.get('scene_running') if isinstance(last_su, dict) else '?'
        if sr == False:
            result('scene-stop-broadcast', 'status_update po STOP (scene_running=False)', 'PASS',
                   f'{n_stop2}x status_update  scene_running=False ✓\n'
                   f'→ Stop tlačidlo sa zmení automaticky bez F5 ✓')
            result('btn-fix', 'Stop button bug – OPRAVENÝ?', 'PASS',
                   'UI dostane status_update → tlačidlo sa zmení na zelené ✓')
        else:
            result('scene-stop-broadcast', 'status_update po STOP', 'WARN',
                   f'{n_stop2}x status_update ale scene_running={sr}\n'
                   f'→ Stav nie je False aj keď scéna je zastavená')
            result('btn-fix', 'Stop button bug', 'FAIL',
                   f'scene_running={sr} v status_update po STOP')
    else:
        result('scene-stop-broadcast', 'status_update po STOP (scene_running=False)', 'FAIL',
               f'ŽIADNY status_update {int((time.time()-pre_stop)*1000)}ms po STOP!\n'
               f'→ TOTO JE BUG: tlačidlo ostane červené bez F5\n'
               f'→ Analýza kde by mal emit prísť:\n'
               f'  PATH 1: scenes.py finally → dashboard.socketio.emit() [HTTP thread]\n'
               f'  PATH 2: _run_scene_logic finally → broadcast_status() [Scene thread]\n'
               f'  PATH 3: main.py stop_scene() → broadcast_status() [HTTP thread]')
        result('btn-fix', 'Stop button bug – stále prítomný', 'FAIL',
               'Emit sa nedoručil klientovi')

    # ── 6D: Overenie HTTP /api/status po STOP ──
    r3 = http_get('/api/status')
    if r3['ok']:
        sr_http = r3['data'].get('scene_running')
        if sr_http == False:
            result('scene-stop-http', '/api/status po STOP (scene_running=False)', 'PASS',
                   'Backend správne vracia scene_running=False cez REST ✓')
        else:
            result('scene-stop-http', '/api/status po STOP', 'FAIL',
                   f'scene_running={sr_http} cez REST – backend state bug!')
    else:
        result('scene-stop-http', '/api/status po STOP', 'FAIL', f'HTTP {r3["status"]}')

# ── FÁZA 7: Multi-client Broadcast Test ──────────────────────────────────────
header('FÁZA 7 │ Multi-Client Broadcast\n'
       '        (overenie že broadcast ide ku VŠETKÝM klientom)')

print(f'  {DIM}Simuluje: user má otvorený dashboard na 2 zariadeniach{RST}')
sock3 = Sock('client2')
c2_ok = sock3.connect(timeout=8)

if not c2_ok:
    result('multi-connect', '2. klient', 'WARN', 'Nedá sa pripojiť 2. klient')
else:
    result('multi-connect', '2. klient pripojený', 'PASS', f'SID={sock3.sid}')
    time.sleep(1)

    if SCENE:
        http_post('/api/stop_scene')
        time.sleep(1)

        broadcast_ts = time.time()
        http_post(f'/api/run_scene/{SCENE}')

        su1 = sock.wait('status_update', timeout=5, after=broadcast_ts)
        su2 = sock3.wait('status_update', timeout=5, after=broadcast_ts)

        if su1 and su2:
            result('multi-broadcast-start', 'START broadcast ku obom klientom', 'PASS',
                   'Oba klienti dostali status_update ✓')
        elif su1:
            result('multi-broadcast-start', 'START broadcast ku obom klientom', 'FAIL',
                   'Len 1. klient dostal broadcast – 2. klient nie!\n'
                   '→ Možný bug v namespace alebo room targeting')
        elif su2:
            result('multi-broadcast-start', 'START broadcast ku obom klientom', 'FAIL',
                   'Len 2. klient dostal broadcast – 1. klient nie!')
        else:
            result('multi-broadcast-start', 'START broadcast ku obom klientom', 'FAIL',
                   'Žiadny klient nedostal broadcast')

        time.sleep(2)
        http_post('/api/stop_scene')
        time.sleep(3)

        stop_ts = time.time()
        r_stop = http_post('/api/stop_scene')

        if r_stop['ok']:
            su1s = sock.wait('status_update', timeout=5, after=stop_ts)
            su2s = sock3.wait('status_update', timeout=5, after=stop_ts)
            if su1s and su2s:
                result('multi-broadcast-stop', 'STOP broadcast ku obom klientom', 'PASS',
                       'Oba klienti dostali status_update po STOP ✓')
            else:
                missing = []
                if not su1s: missing.append('1. klient')
                if not su2s: missing.append('2. klient')
                result('multi-broadcast-stop', 'STOP broadcast ku obom klientom', 'FAIL',
                       f'Chýba u: {", ".join(missing)}')

    sock3.disconnect()

# ── FÁZA 8: Broadcast z rôznych kontextov ────────────────────────────────────
header('FÁZA 8 │ Emit Kontext Diagnostika\n'
       '        (identifikuje kde presne zlyhávajú emity)')

print(f'  {DIM}Testuje 3 rôzne cesty ako server emituje klientom:{RST}')
print(f'  {DIM}  A) emit() v Socket event handleri (request_* odpovede){RST}')
print(f'  {DIM}  B) socketio.emit() z HTTP route (scenes.py finally){RST}')
print(f'  {DIM}  C) socketio.emit() z background thread (scene_progress){RST}\n')

# PATH A: Socket event handler emit
ts_a = time.time()
sock.emit('request_status')
d_a = sock.wait('status_update', timeout=3, after=ts_a)
result('emit-path-a', 'PATH A: emit() zo socket event handlera', 
       'PASS' if d_a is not None else 'FAIL',
       'Funguje ✓' if d_a is not None else
       'NEFUNGUJE – socket event handler emit() nefunguje\n'
       '→ Toto je root cause prázdnych Logov a "Odpojené" na Dashboard-e!\n'
       '→ Skontroluj: from flask_socketio import emit je importovaný\n'
       '→ Skontroluj: handler funkcie sú v správnom scope')

# PATH B: HTTP route emit (cez /api/status - len read, ale overíme že REST funguje)
ts_b = time.time()
r_b = http_get('/api/stats')
result('emit-path-b-rest', 'PATH B: REST endpoint dostupný', 
       'PASS' if r_b['ok'] else 'FAIL',
       f'HTTP {r_b["status"]}')

# PATH C: Background thread - overíme cez scene_progress
if SCENE and prog_count > 0:
    result('emit-path-c', 'PATH C: Background thread emit (scene_progress)', 'PASS',
           f'{prog_count}x scene_progress prijatý ✓')
elif SCENE:
    result('emit-path-c', 'PATH C: Background thread emit (scene_progress)', 'WARN',
           'scene_progress neprijatý\n'
           '→ LiveView nebude fungovať\n'
           '→ Skontroluj: state_machine.on_state_change callback je nastavený')
else:
    result('emit-path-c', 'PATH C: Background thread emit', 'SKIP', 'Žiadna scéna')

# ── FÁZA 9: Dátová konzistencia ───────────────────────────────────────────────
header('FÁZA 9 │ Dátová Konzistencia\n'
       '        (overenie formátu dát ktoré UI očakáva)')

su = sock.last('status_update')
if su and isinstance(su, dict):
    missing_su = [f for f in ['room_id','scene_running','mqtt_connected'] if f not in su]
    if not missing_su:
        rid = su.get('room_id')
        valid = rid and rid not in ['-','Unknown',None,'']
        st = 'PASS' if valid else 'WARN'
        result('data-status', 'status_update polia', st,
               f"room_id='{rid}'  scene_running={su.get('scene_running')}  "
               f"mqtt={su.get('mqtt_connected')}"
               + ('' if valid else '\n→ room_id je neplatné'))
    else:
        result('data-status', 'status_update polia', 'FAIL',
               f'Chýbajú polia: {", ".join(missing_su)}\n'
               f'→ Dashboard nebude zobrazovať správne dáta')
else:
    result('data-status', 'status_update polia', 'SKIP', 'Žiadny status_update')

lh = sock.last('log_history')
if lh and isinstance(lh, list) and len(lh) > 0:
    s = lh[0]
    missing_lh = [f for f in ['timestamp','level','message'] if f not in s]
    if not missing_lh:
        result('data-logs', 'log_history záznamy', 'PASS',
               f'[{s.get("level")}] {str(s.get("message",""))[:60]}')
    else:
        result('data-logs', 'log_history záznamy', 'FAIL',
               f'Chýbajú polia: {", ".join(missing_lh)}\n→ LogsView nefunguje')
elif lh is not None:
    result('data-logs', 'log_history záznamy', 'WARN', 'Prázdny buffer (normálne pri čerstvom štarte)')
else:
    result('data-logs', 'log_history záznamy', 'SKIP', 'Žiadny log_history')

st_data = sock.last('stats_update')
if st_data and isinstance(st_data, dict):
    missing_st = [f for f in ['total_scenes_played','connected_devices'] if f not in st_data]
    if not missing_st:
        result('data-stats', 'stats_update polia', 'PASS',
               f"total_scenes={st_data.get('total_scenes_played')}  "
               f"devices={len(st_data.get('connected_devices',{}))}")
    else:
        result('data-stats', 'stats_update polia', 'FAIL',
               f'Chýbajú: {", ".join(missing_st)}')
else:
    result('data-stats', 'stats_update polia', 'SKIP', 'Žiadny stats_update')

# ── Cleanup ───────────────────────────────────────────────────────────────────
sock.disconnect()
http_post('/api/stop_scene')

# ══════════════════════════════════════════════════════════════════════════════
summary()

# ── Root cause analýza ────────────────────────────────────────────────────────
fails = {k for k, v in results.items() if v == 'FAIL'}
warns = {k for k, v in results.items() if v == 'WARN'}

if not fails:
    print(f'{col("  ✓ Všetky kritické testy prešli!", GRN)}\n')
    sys.exit(0)

print(f'{BOL}{RED}  ╔══ ROOT CAUSE ANALÝZA ══╗{RST}')

# BUG 1: request_* nefunguje (prázdne Logy, Odpojené Dashboard)
req_fails = {'req-request_logs', 'req-request_status', 'req-request_stats',
             'nav-logs-mount', 'nav-dash-mount', 'emit-path-a'} & fails
if req_fails:
    print(f'\n  {RED}● BUG #1 [KRITICKÝ]: Prázdne Logy + "Odpojené" po navigácii{RST}')
    print(f'    {BOL}Príčina:{RST} Server neodpovedá na request_* eventy')
    print(f'    {CYN}Súbor:  raspberry_pi/Web/dashboard.py{RST}')
    print(f'    {CYN}Miesto: _setup_socketio_handlers() → request_logs, request_status, request_stats handlery{RST}')
    print(f'    Overiť: sú handlery zaregistrované? emitujú správne?')
    print(f'    {GRN}Oprava: Skontroluj či "from flask_socketio import emit" je na začiatku súboru{RST}')
    print(f'    {GRN}        a či handler funkcie sú vo vnútri _setup_socketio_handlers(){RST}')

# BUG 2: Stop broadcast nefunguje (červené tlačidlo)
stop_fails = {'scene-stop-broadcast', 'btn-fix'} & fails
if stop_fails:
    print(f'\n  {RED}● BUG #2 [KRITICKÝ]: Tlačidlo ostane červené bez F5{RST}')
    print(f'    {BOL}Príčina:{RST} status_update nie je emitovaný po stop_scene()')
    print(f'    {CYN}Súbor:  raspberry_pi/main.py → stop_scene(){RST}')
    print(f'    {GRN}Oprava: Pridaj na koniec stop_scene():{RST}')
    print(f'    {GRN}          if self.web_dashboard:{RST}')
    print(f'    {GRN}              self.web_dashboard.broadcast_status(){RST}')
    print(f'    {GRN}        a keď transitioned=False tiež:{RST}')
    print(f'    {GRN}          if not transitioned:{RST}')
    print(f'    {GRN}              if self.web_dashboard:{RST}')
    print(f'    {GRN}                  self.web_dashboard.broadcast_status(){RST}')
    print(f'    {GRN}              return True{RST}')

# BUG 3: scene_progress nefunguje (LiveView)
if 'scene-progress' in warns:
    print(f'\n  {YEL}● WARN #3: LiveView nereaguje (scene_progress){RST}')
    print(f'    {BOL}Príčina:{RST} scene_progress event sa neeimituje počas behu scény')
    print(f'    {CYN}Súbor:  raspberry_pi/main.py → _run_scene_logic(){RST}')
    print(f'    Overiť: je nastavený state_machine.on_state_change = notify_web?')
    print(f'    Overiť: má scéna {SCENE!r} viacero stavov (transitions)?')

# Spoločný problém
if len({'req-request_logs','req-request_status','req-request_stats'} & fails) >= 2 and stop_fails:
    print(f'\n  {BOL}══ SPOLOČNÝ ROOT CAUSE ══{RST}')
    print(f'  Všetky bugy majú spoločné jadro:')
    print(f'  {YEL}socketio.emit() / emit() nie sú volané z správneho kontextu{RST}')
    print(f'  alebo flask-socketio nie je správne nakonfigurované pre threaded mode.')
    print(f'  Skontroluj verziu: pip3 show flask-socketio python-socketio')
    print(f'  Odporúčaná: flask-socketio>=5.3 python-socketio>=5.9')

print()