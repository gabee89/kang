"""땅따먹기 LUCK RUSH - 3인 실시간 대전 서버 (Python / aiohttp)."""
import asyncio
import json
import logging
import math
import os
import random
import secrets
import string
import time
from collections import deque
from pathlib import Path
from aiohttp import web, WSMsgType

ROOT = Path(__file__).resolve().parent
COLS, ROWS = 46, 30
SIZE = COLS * ROWS
GOAL = 55
DURATION = 180
PAUSE_RECONNECT = 30
ROOMS = {}
MAX_ROOMS = 60  # Simple abuse protection for a small public demo service
PEOPLE = {
    1: ('박선옥', '#5ef3bf'),
    2: ('김영관', '#ffbf73'),
    3: ('강병갑', '#9babff'),
}
SPAWNS = {1: (9, 15), 2: (35, 7), 3: (35, 23)}
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
UPGRADES = {
    'speed': ('👟', '발 빠른 개척자', '이동속도 +15%'),
    'damage': ('💎', '공격 강화', '자동 공격 피해 +1'),
    'rapid': ('⚡', '연사 속도', '발사 간격 -13%'),
    'multi': ('🪄', '쌍둥이 탄환', '동시 발사 +1'),
    'luck': ('🍀', '행운 충전', '행운 +12%'),
    'heal': ('💗', '회복의 기회', '최대 생명 +1 / 생명 회복'),
    'shield': ('🛡️', '행운의 보호막', '보호막 +1'),
    'pulse': ('💥', '광역 펄스', '펄스 사거리 +1 / 재사용 -1초'),
    'capture': ('🏰', '영토 확장', '점령 시 추가 칸 획득'),
}


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


def valid(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def ix(x, y):
    return y * COLS + x


def code():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        candidate = ''.join(secrets.choice(alphabet) for _ in range(5))
        if candidate not in ROOMS:
            return candidate


def clean_input_dir(dx, dy):
    try:
        dx = float(dx)
        dy = float(dy)
        if not math.isfinite(dx) or not math.isfinite(dy):
            return 0, 0
    except (TypeError, ValueError):
        return 0, 0
    if abs(dx) >= abs(dy):
        return (1 if dx > .25 else -1 if dx < -.25 else 0), 0
    return 0, (1 if dy > .25 else -1 if dy < -.25 else 0)


class Player:
    def __init__(self, slot, token, ws):
        self.slot = slot
        self.token = token
        self.ws = ws
        self.x, self.y = SPAWNS[slot]
        self.dx = self.dy = 0
        self.trail = []
        self.hp = self.max_hp = 3
        self.shield = 0
        self.speed = 7.8
        self.damage = 2
        self.shots = 1
        self.fire_rate = .55
        self.fire_timer = .2
        self.step_timer = 0
        self.luck = 8
        self.pulse_range = 5
        self.pulse_cd = 11
        self.pulse_ready = 0
        self.capture = 0
        self.invuln = 0
        self.stun = 0
        self.level = 1
        self.xp = 0
        self.next_xp = 8
        self.kills = 0
        self.claims = 0
        self.score = 0
        self.best = 0
        self.options = None
        self.rerolls = 0
        self.last_seen = time.monotonic()

    def public(self):
        return {
            'id': self.slot, 'name': PEOPLE[self.slot][0], 'x': self.x, 'y': self.y,
            'hp': self.hp, 'maxHp': self.max_hp, 'shield': self.shield,
            'score': round(self.score, 2), 'best': round(self.best, 2),
            'level': self.level, 'xp': self.xp, 'nextXp': self.next_xp,
            'luck': self.luck, 'kills': self.kills, 'claims': self.claims,
            'pulseReady': round(self.pulse_ready, 1), 'pulseCd': round(self.pulse_cd, 1),
            'connected': self.ws is not None and not self.ws.closed,
            'upgrading': self.options is not None, 'invuln': self.invuln > 0,
            'stun': self.stun > 0,
        }


class Room:
    def __init__(self, room_code):
        self.code = room_code
        self.players = {}
        self.host = None
        self.phase = 'lobby'
        self.board = [0] * SIZE
        self.enemies = []
        self.bullets = []
        self.seconds = 0
        self.spawn_timer = 0
        self.last_broadcast = 0
        self.winner = None
        self.seq = 0
        self.created = time.monotonic()
        self.last_active = self.created
        self.waiting_since = None
        self.events = deque(maxlen=15)

    def connected(self):
        return [p for p in self.players.values() if p.ws is not None and not p.ws.closed]

    def lobby_state(self):
        return {
            'type': 'room', 'code': self.code, 'phase': self.phase,
            'host': self.host, 'slots': [self.players[s].public() if s in self.players else None for s in (1, 2, 3)],
            'seconds': round(self.seconds, 1), 'winner': self.winner,
            'waiting': self.waiting_since is not None,
        }

    async def send_to(self, player, data):
        if player.ws is not None and not player.ws.closed:
            try:
                await player.ws.send_json(data)
            except (ConnectionResetError, RuntimeError):
                pass

    async def all(self, data):
        await asyncio.gather(*(self.send_to(p, data) for p in self.connected()), return_exceptions=True)

    async def announce(self, message, kind='info'):
        await self.all({'type': 'event', 'message': message[:160], 'kind': kind})

    async def broadcast_room(self):
        await self.all(self.lobby_state())

    def add(self, requested_slot, ws, existing_token=None):
        # A private random session token allows a temporarily disconnected player to rejoin the exact same slot.
        for p in self.players.values():
            if existing_token and secrets.compare_digest(p.token, existing_token):
                if p.ws and not p.ws.closed:
                    return None, '이미 다른 기기에서 접속 중입니다.'
                p.ws = ws
                p.last_seen = time.monotonic()
                self.last_active = p.last_seen
                self.waiting_since = None if all(x.ws and not x.ws.closed for x in self.players.values()) else self.waiting_since
                return p, None
        if self.phase != 'lobby':
            return None, '이미 경기가 시작됐습니다. 기존 참가자만 재접속할 수 있어요.'
        try:
            slot = int(requested_slot)
        except (ValueError, TypeError):
            slot = 0
        if slot in self.players:
            return None, '그 캐릭터는 이미 다른 참가자가 선택했어요.'
        if len(self.players) >= 3:
            return None, '방이 가득 찼습니다. 최대 3명까지 참여할 수 있어요.'
        if slot not in PEOPLE:
            slot = next(s for s in PEOPLE if s not in self.players)
        p = Player(slot, secrets.token_urlsafe(28), ws)
        self.players[slot] = p
        if self.host is None:
            self.host = p.token
        self.last_active = time.monotonic()
        return p, None

    def remove(self, player):
        if player.token not in [p.token for p in self.players.values()]:
            return
        player.ws = None
        player.dx = player.dy = 0
        player.last_seen = time.monotonic()
        self.last_active = player.last_seen
        if self.phase == 'lobby':
            # Keep a short window for recovery from mobile network switches.
            pass
        elif self.phase == 'playing' and self.waiting_since is None:
            self.waiting_since = self.last_active

    async def begin(self):
        if self.phase != 'lobby' or len(self.players) != 3 or len(self.connected()) != 3:
            return False
        self.phase = 'playing'
        self.seconds = 0
        self.winner = None
        self.waiting_since = None
        self.board = [0] * SIZE
        self.enemies = []
        self.bullets = []
        self.spawn_timer = 0
        self.events.clear()
        for s, p in self.players.items():
            p.__init__(s, p.token, p.ws)
            x, y = SPAWNS[s]
            for yy in range(y - 2, y + 3):
                for xx in range(x - 2, x + 3):
                    self.board[ix(xx, yy)] = s
        self.recalc()
        for _ in range(5):
            self.spawn_enemy()
        await self.announce('⚔️ 3인 실시간 점령전 시작! 상대 영토도 빼앗으세요.', 'good')
        await self.broadcast_room()
        await self.snapshot()
        return True

    def recalc(self):
        counts = [0, 0, 0, 0]
        for b in self.board:
            if 1 <= b <= 3:
                counts[b] += 1
        for p in self.players.values():
            p.score = counts[p.slot] * 100 / SIZE
            p.best = max(p.best, p.score)

    def clear_trail(self, p):
        for t in p.trail:
            if self.board[t] == p.slot + 3:
                self.board[t] = 0
        p.trail.clear()

    def respawn(self, p):
        own = [i for i, owner in enumerate(self.board) if owner == p.slot]
        if not own:
            x, y = SPAWNS[p.slot]
            for yy in range(max(0, y - 1), min(ROWS, y + 2)):
                for xx in range(max(0, x - 1), min(COLS, x + 2)):
                    self.board[ix(xx, yy)] = p.slot
            own = [ix(x, y)]
        best = min(own, key=lambda k: (k % COLS - p.x) ** 2 + (k // COLS - p.y) ** 2)
        p.x = best % COLS
        p.y = best // COLS
        p.dx = p.dy = 0
        p.stun = .5
        p.invuln = 1.7

    def damage(self, p, by=None, from_enemy=False):
        if p.invuln > 0:
            return
        if p.shield:
            p.shield -= 1
            p.invuln = .8
            return
        self.clear_trail(p)
        p.hp -= 1
        self.respawn(p)
        if p.hp <= 0:
            # No permanent elimination: everybody can fight for the full match.
            p.hp = p.max_hp
            p.stun = 3
            for i, val in enumerate(self.board):
                if val == p.slot and random.random() < .22:
                    self.board[i] = 0
            self.recalc()
        name = PEOPLE[p.slot][0]
        message = f'✂️ {name}의 점령선이 끊겼어요!' if not from_enemy else f'💔 {name}이(가) 몬스터에게 맞았어요!'
        asyncio.create_task(self.announce(message, 'danger'))
        if by is not None and by is not p:
            self.gain_xp(by, 3)

    def step_actor(self, p):
        if p.stun > 0 or p.options is not None or not (p.dx or p.dy):
            return
        nx, ny = p.x + p.dx, p.y + p.dy
        if not valid(nx, ny):
            return
        t = ix(nx, ny)
        value = self.board[t]
        if 4 <= value <= 6 and value != p.slot + 3:
            enemy = self.players.get(value - 3)
            if enemy:
                self.damage(enemy, by=p)
                value = self.board[t]
                if value == enemy.slot + 3:
                    return  # 상대에게 보호막/무적 상태가 있어 점령선을 자르지 못함
        if value == p.slot + 3:
            # Returning over your own open line fails; unlike a closed loop to owned land.
            if len(p.trail) >= 5:
                self.damage(p)
            return
        p.x, p.y = nx, ny
        if value == p.slot:
            if p.trail:
                self.capture(p)
        else:
            self.board[t] = p.slot + 3
            p.trail.append(t)
            if len(p.trail) > SIZE // 2:
                self.damage(p)

    def capture(self, p):
        if not p.trail:
            return
        previous = self.board.copy()
        for i in p.trail:
            self.board[i] = p.slot
        seen = bytearray(SIZE)
        regions = []
        for k in range(SIZE):
            if seen[k] or self.board[k] == p.slot:
                continue
            group = []
            q = deque((k,))
            seen[k] = 1
            while q:
                n = q.popleft()
                group.append(n)
                x, y = n % COLS, n // COLS
                for dx, dy in DIRS:
                    xx, yy = x + dx, y + dy
                    if valid(xx, yy):
                        pos = ix(xx, yy)
                        if not seen[pos] and self.board[pos] != p.slot:
                            seen[pos] = 1
                            q.append(pos)
            regions.append(group)
        if len(regions) >= 2:
            outside = max(range(len(regions)), key=lambda i: len(regions[i]))
            for i, group in enumerate(regions):
                if i != outside:
                    for t in group:
                        self.board[t] = p.slot
        if p.capture:
            edge = set()
            for j, val in enumerate(self.board):
                if val != p.slot:
                    continue
                x, y = j % COLS, j // COLS
                for dx, dy in DIRS:
                    xx, yy = x + dx, y + dy
                    if valid(xx, yy):
                        new_t = ix(xx, yy)
                        if self.board[new_t] != p.slot:
                            edge.add(new_t)
            for e in edge:
                if random.random() < p.capture * .07:
                    self.board[e] = p.slot
        gained = 0
        stolen = 0
        for i, value in enumerate(self.board):
            if value == p.slot and previous[i] != p.slot:
                gained += 1
                if previous[i] in (1, 2, 3):
                    stolen += 1
        p.trail.clear()
        p.claims += 1
        # If a rival's active trail was enclosed, its line is cut.
        for other in self.players.values():
            if other is not p and any(self.board[i] != other.slot + 3 for i in other.trail):
                self.damage(other, by=p)
        self.recalc()
        if gained:
            self.gain_xp(p, 2 + gained // 12 + stolen // 8)
            self.roll(p)
            msg = f'🏰 {PEOPLE[p.slot][0]} +{gained}칸 점령' + (f' · 상대 땅 {stolen}칸 탈환!' if stolen else '!')
            asyncio.create_task(self.announce(msg, 'good'))
        self.check_winner()

    def gain_xp(self, p, amount):
        p.xp += amount
        if p.options is not None:
            return
        if p.xp >= p.next_xp:
            p.xp -= p.next_xp
            p.level += 1
            p.next_xp = 8 + (p.level - 1) * 5
            # Only the leveling player selects cards; other online players continue moving.
            selection = random.sample(list(UPGRADES), 3)
            p.options = []
            for key in selection:
                r = random.random()
                tier = 'epic' if r < .07 + p.luck / 400 else 'rare' if r < .30 + p.luck / 280 else 'common'
                icon, name, desc = UPGRADES[key]
                p.options.append({'id': key, 'icon': icon, 'name': name, 'desc': desc, 'tier': tier})
            asyncio.create_task(self.send_to(p, {'type': 'upgrade', 'cards': p.options}))

    def apply_upgrade(self, p, identifier):
        if not p.options:
            return False
        card = next((a for a in p.options if a['id'] == identifier), None)
        if card is None:
            return False
        amount = {'common': 1, 'rare': 2, 'epic': 3}[card['tier']]
        choice = card['id']
        p.options = None
        if choice == 'speed':
            p.speed = min(12, p.speed * (1 + .15 * amount))
        elif choice == 'damage':
            p.damage += amount
        elif choice == 'rapid':
            p.fire_rate = max(.2, p.fire_rate * (1 - .13 * amount))
        elif choice == 'multi':
            p.shots = min(4, p.shots + amount)
        elif choice == 'luck':
            p.luck = min(85, p.luck + 12 * amount)
        elif choice == 'heal':
            p.max_hp = min(9, p.max_hp + amount)
            p.hp = min(p.max_hp, p.hp + amount + 1)
        elif choice == 'shield':
            p.shield += amount
        elif choice == 'pulse':
            p.pulse_range = min(11, p.pulse_range + amount)
            p.pulse_cd = max(4, p.pulse_cd - amount)
        elif choice == 'capture':
            p.capture = min(6, p.capture + amount)
        if p.xp >= p.next_xp:
            self.gain_xp(p, 0)
        return True

    def roll(self, p):
        roll = clamp(random.randint(1, 6) + (1 if random.random() < p.luck / 100 else 0), 1, 6)
        if roll == 1:
            p.xp += 2
        elif roll == 2:
            p.xp += 4
        elif roll == 3:
            p.hp = min(p.max_hp, p.hp + 1)
        elif roll == 4:
            p.shield += 1
        elif roll == 5:
            p.xp += 6
        else:
            p.hp = min(p.max_hp, p.hp + 1)
            p.shield += 1
            p.xp += 7
        if p.options is None:
            self.gain_xp(p, 0)
        asyncio.create_task(self.send_to(p, {'type': 'event', 'message': f'🎲 주사위 {roll}! 랜덤 보너스 획득', 'kind': 'gold'}))

    def spawn_enemy(self):
        if len(self.enemies) >= 26:
            return
        for _ in range(40):
            x, y = random.uniform(1, COLS - 2), random.uniform(1, ROWS - 2)
            if self.board[ix(int(x), int(y))] == 0:
                self.enemies.append({'x': x, 'y': y, 'hp': 2 + int(self.seconds // 50), 't': random.uniform(0, 5)})
                break

    def pulse(self, p):
        if p.pulse_ready > 0 or self.phase != 'playing' or self.waiting_since is not None:
            return
        p.pulse_ready = p.pulse_cd
        killed = 0
        for e in self.enemies[:]:
            if math.hypot(e['x'] - p.x - .5, e['y'] - p.y - .5) < p.pulse_range:
                self.kill_enemy(e, p)
                killed += 1
        asyncio.create_task(self.all({'type': 'effect', 'kind': 'pulse', 'id': p.slot, 'range': p.pulse_range}))
        asyncio.create_task(self.send_to(p, {'type': 'event', 'message': f'💥 펄스! 몬스터 {killed}마리 처치', 'kind': 'good'}))

    def kill_enemy(self, e, p):
        if e in self.enemies:
            self.enemies.remove(e)
            p.kills += 1
            self.gain_xp(p, 1)

    def update_enemies(self, dt):
        for e in self.enemies[:]:
            if not self.players:
                continue
            target = min(self.players.values(), key=lambda p: math.hypot(e['x'] - p.x - .5, e['y'] - p.y - .5))
            d = math.hypot(e['x'] - target.x - .5, e['y'] - target.y - .5)
            if d > .001:
                rate = (.95 + .26 * int(self.seconds // 50)) * dt
                e['x'] = clamp(e['x'] + (target.x + .5 - e['x']) / d * rate, .25, COLS - .25)
                e['y'] = clamp(e['y'] + (target.y + .5 - e['y']) / d * rate, .25, ROWS - .25)
            e['t'] += dt
            for p in self.players.values():
                if math.hypot(e['x'] - p.x - .5, e['y'] - p.y - .5) < .62:
                    self.damage(p, from_enemy=True)
                    break
        for p in self.players.values():
            p.fire_timer -= dt
            if p.fire_timer > 0 or p.options is not None:
                continue
            p.fire_timer = p.fire_rate
            targets = sorted(self.enemies, key=lambda e: (e['x'] - p.x - .5) ** 2 + (e['y'] - p.y - .5) ** 2)
            for e in targets[:p.shots]:
                dx, dy = e['x'] - p.x - .5, e['y'] - p.y - .5
                d = math.hypot(dx, dy)
                if .01 < d < 9:
                    self.bullets.append({'x': p.x + .5, 'y': p.y + .5,
                                         'vx': dx / d * 12, 'vy': dy / d * 12,
                                         'life': .9, 'owner': p.slot, 'damage': p.damage})
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['vx'] * dt
            bullet['y'] += bullet['vy'] * dt
            bullet['life'] -= dt
            hit = next((e for e in self.enemies if math.hypot(e['x'] - bullet['x'], e['y'] - bullet['y']) < .45), None)
            if hit is not None:
                hit['hp'] -= bullet['damage']
                if hit['hp'] <= 0:
                    self.kill_enemy(hit, self.players[bullet['owner']])
                bullet['life'] = 0
            if bullet['life'] <= 0 or not (0 < bullet['x'] < COLS and 0 < bullet['y'] < ROWS):
                self.bullets.remove(bullet)

    def check_winner(self):
        if self.phase != 'playing':
            return
        leader = next((p for p in self.players.values() if p.score >= GOAL), None)
        if leader:
            self.finish(leader.slot, 'dominance')

    def finish(self, winner=None, reason='time'):
        if self.phase != 'playing':
            return
        self.phase = 'finished'
        self.winner = winner if winner is not None else max(self.players.values(), key=lambda p: (p.score, p.kills)).slot
        self.waiting_since = None
        asyncio.create_task(self.all({'type': 'finished', 'winner': self.winner, 'reason': reason,
                                       'scores': [p.public() for p in sorted(self.players.values(), key=lambda p: -p.score)]}))
        asyncio.create_task(self.broadcast_room())

    async def snapshot(self):
        self.seq += 1
        data = {
            'type': 'state', 'seq': self.seq,
            'phase': self.phase, 'seconds': round(self.seconds, 1), 'remain': max(0, math.ceil(DURATION - self.seconds)),
            'board': ''.join(str(v) for v in self.board),
            'players': [p.public() for p in self.players.values()],
            'enemies': [[round(e['x'], 2), round(e['y'], 2)] for e in self.enemies],
            'bullets': [[round(b['x'], 2), round(b['y'], 2), b['owner']] for b in self.bullets],
            'pausedForReconnect': self.waiting_since is not None,
            'reconnectLeft': max(0, math.ceil(PAUSE_RECONNECT - (time.monotonic() - self.waiting_since))) if self.waiting_since else 0,
        }
        await self.all(data)

    async def tick(self, dt):
        now = time.monotonic()
        # Clear abandoned lobby seats after 30 seconds and promote host automatically.
        if self.phase == 'lobby':
            changed = False
            for slot, p in list(self.players.items()):
                if p.ws is None and now - p.last_seen > PAUSE_RECONNECT:
                    del self.players[slot]
                    changed = True
            if changed:
                if self.host not in [p.token for p in self.players.values()]:
                    self.host = next((p.token for p in self.players.values()), None)
                await self.broadcast_room()
        if self.phase != 'playing':
            return
        if any(not p.ws or p.ws.closed for p in self.players.values()):
            if self.waiting_since is None:
                self.waiting_since = now
            if now - self.waiting_since >= PAUSE_RECONNECT:
                active = [p for p in self.players.values() if p.ws and not p.ws.closed]
                winner = max(active, key=lambda p: p.score).slot if active else None
                self.finish(winner, 'disconnect')
            if now - self.last_broadcast >= .25:
                await self.snapshot()
                self.last_broadcast = now
            return
        self.waiting_since = None
        self.seconds += dt
        for p in self.players.values():
            p.stun = max(0, p.stun - dt)
            p.invuln = max(0, p.invuln - dt)
            p.pulse_ready = max(0, p.pulse_ready - dt)
            p.step_timer = min(2.0, p.step_timer + dt * p.speed)
            iterations = 0
            while p.step_timer >= 1 and iterations < 3:
                p.step_timer -= 1
                self.step_actor(p)
                iterations += 1
                if self.phase != 'playing':
                    break
        if self.phase == 'playing':
            self.spawn_timer += dt
            if self.spawn_timer >= max(.55, 1.4 - self.seconds / 350):
                self.spawn_timer = 0
                self.spawn_enemy()
            self.update_enemies(dt)
            if self.seconds >= DURATION:
                self.recalc()
                self.finish(reason='time')
        if now - self.last_broadcast > .1:
            self.last_broadcast = now
            await self.snapshot()


async def api_create(request):
    if len(ROOMS) >= MAX_ROOMS:
        return web.json_response({'error': '게임방이 너무 많습니다. 잠시 후 다시 시도해 주세요.'}, status=429)
    new = Room(code())
    ROOMS[new.code] = new
    return web.json_response({'code': new.code})


async def api_health(request):
    return web.json_response({'ok': True, 'rooms': len(ROOMS)})


async def api_room_status(request):
    room = ROOMS.get(request.match_info.get('code','').upper())
    if not room:
        return web.json_response({'error': '방을 찾을 수 없습니다.'}, status=404)
    return web.json_response({'code': room.code, 'phase': room.phase,
                              'occupied': [p.slot for p in room.players.values()]})


async def websocket_handler(request):
    room_id = request.query.get('room', '').strip().upper()
    room = ROOMS.get(room_id)
    if room is None:
        return web.json_response({'error': '방이 없거나 종료됐습니다. 방 코드를 확인하세요.'}, status=404)
    ws = web.WebSocketResponse(heartbeat=18, max_msg_size=4096, receive_timeout=70)
    await ws.prepare(request)
    participant = None
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                if msg.type == WSMsgType.ERROR:
                    break
                continue
            try:
                payload = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            typ = payload.get('type')
            if typ == 'join' and participant is None:
                token = payload.get('token')
                token = token if isinstance(token, str) and len(token) < 150 else None
                p, err = room.add(payload.get('slot'), ws, token)
                if err:
                    await ws.send_json({'type': 'error', 'message': err})
                    await ws.close()
                    break
                participant = p
                await ws.send_json({'type': 'joined', 'code': room.code, 'slot': p.slot,
                                    'token': p.token, 'isHost': room.host == p.token})
                await room.broadcast_room()
                if room.phase == 'playing':
                    await room.snapshot()
                    if p.options:
                        await room.send_to(p, {'type': 'upgrade', 'cards': p.options})
                    if room.waiting_since is None:
                        await room.announce('✅ 세 명 모두 다시 연결되었습니다.', 'good')
                continue
            if participant is None:
                await ws.send_json({'type': 'error', 'message': '먼저 입장해 주세요.'})
                continue
            if typ == 'input':
                participant.dx, participant.dy = clean_input_dir(payload.get('x', 0), payload.get('y', 0))
            elif typ == 'start':
                if room.host != participant.token:
                    await room.send_to(participant, {'type': 'error', 'message': '방장만 시작할 수 있어요.'})
                elif not await room.begin():
                    await room.send_to(participant, {'type': 'error', 'message': '3명이 모두 접속해야 시작할 수 있어요.'})
            elif typ == 'pulse':
                room.pulse(participant)
            elif typ == 'upgrade':
                name = payload.get('id')
                if isinstance(name, str):
                    if room.apply_upgrade(participant, name):
                        await room.send_to(participant, {'type': 'upgrade_done'})
            elif typ == 'rematch':
                if room.host == participant.token and room.phase == 'finished' and len(room.connected()) == 3:
                    room.phase = 'lobby'
                    await room.begin()
                else:
                    await room.send_to(participant, {'type': 'error', 'message': '세 명 모두 연결된 상태에서 방장만 재대결을 시작할 수 있어요.'})
            elif typ == 'leave':
                break
    except (ConnectionResetError, asyncio.TimeoutError):
        pass
    finally:
        if participant and participant.ws is ws:
            room.remove(participant)
            await room.broadcast_room()
            if room.phase == 'playing':
                await room.announce('📡 한 명이 연결을 잃었습니다. 30초간 재접속을 기다립니다.', 'danger')
        await ws.close()
    return ws


async def ticker(app):
    last = time.monotonic()
    try:
        while True:
            await asyncio.sleep(.05)
            now = time.monotonic()
            dt = min(.12, now - last)
            last = now
            for key, room in list(ROOMS.items()):
                try:
                    await room.tick(dt)
                    idle = now - room.last_active
                    if (room.phase in ('finished', 'lobby') and not room.connected() and idle > 180) or idle > 7200:
                        ROOMS.pop(key, None)
                except Exception:
                    logging.exception('room %s tick failed', key)
    except asyncio.CancelledError:
        pass


async def on_startup(app):
    app['ticker'] = asyncio.create_task(ticker(app))


async def on_cleanup(app):
    app['ticker'].cancel()
    await asyncio.gather(app['ticker'], return_exceptions=True)


async def serve_index(request):
    return web.FileResponse(ROOT / 'index.html')


def create_app():
    app = web.Application(client_max_size=1024 * 64)
    app.router.add_post('/api/rooms', api_create)
    app.router.add_get('/api/rooms/{code}', api_room_status)
    app.router.add_get('/api/health', api_health)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', serve_index)
    app.router.add_static('/assets', ROOT / 'assets', show_index=False)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    web.run_app(create_app(), host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))