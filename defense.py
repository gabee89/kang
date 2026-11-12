"""Server-authoritative, independent-lane luck defense simulation."""
import math
import random
import secrets
import time

# id, Korean name, evolution, role, tier
DEX = [
    (1, '이상해씨', 2, 'grass', 1), (2, '이상해풀', 3, 'grass', 2), (3, '이상해꽃', None, 'grass', 3),
    (4, '파이리', 5, 'fire', 1), (5, '리자드', 6, 'fire', 2), (6, '리자몽', None, 'fire', 3),
    (7, '꼬부기', 8, 'water', 1), (8, '어니부기', 9, 'water', 2), (9, '거북왕', None, 'water', 3),
    (25, '피카츄', 26, 'electric', 2), (26, '라이츄', None, 'electric', 3),
    (92, '고오스', 93, 'ghost', 1), (93, '고우스트', 94, 'ghost', 2), (94, '팬텀', None, 'ghost', 3),
    (129, '잉어킹', 130, 'water', 1), (130, '갸라도스', None, 'water', 3),
    (144, '프리져', None, 'ice', 4), (145, '썬더', None, 'electric', 4),
    (146, '파이어', None, 'fire', 4), (150, '뮤츠', None, 'psychic', 4),
]
CATALOG = {d[0]: dict(zip(('dex', 'name', 'evolution', 'role', 'tier'), d)) for d in DEX}
MAX_UNITS = 12
WAVE_LENGTH = 24


class Player:
    def __init__(self, slot, token, ws):
        self.slot, self.token, self.ws = slot, token, ws
        self.last_seen = time.monotonic()
        self.hp, self.gold, self.level, self.kills = 20, 160, 0, 0
        self.units, self.enemies, self.effects = [], [], []
        self.eliminated_at = None
        self.last_action = -100
        self.raid_ready = 0

    def public(self):
        return {'id': self.slot, 'name': f'트레이너 {self.slot}', 'hp': self.hp,
                'gold': self.gold, 'level': self.level, 'kills': self.kills,
                'connected': self.ws is not None and not self.ws.closed,
                'alive': self.hp > 0, 'eliminatedAt': self.eliminated_at,
                'raidReady': round(self.raid_ready, 1),
                'units': [{k: v for k, v in u.items() if k != 'cooldown'} for u in self.units],
                'enemies': [{k: v for k, v in e.items() if k != 'slow'} for e in self.enemies],
                'effects': self.effects}


class Room:
    def __init__(self, room_code):
        self.code, self.players, self.host = room_code, {}, None
        self.phase, self.seconds, self.wave = 'lobby', 0, 0
        self.winner, self.result = None, None
        self.created = self.last_active = time.monotonic()
        self.last_broadcast, self.seq, self.uid, self.spawned = 0, 0, 0, 0
        self.participants = 0

    def connected(self):
        return [p for p in self.players.values() if p.ws is not None and not p.ws.closed]

    def lobby_state(self):
        return {'type': 'room', 'code': self.code, 'phase': self.phase,
                'hostSlot': next((p.slot for p in self.players.values() if p.token == self.host), None),
                'slots': [self.players[s].public() if s in self.players else None for s in (1, 2, 3)]}

    async def send_to(self, player, data):
        if player.ws is not None and not player.ws.closed:
            try:
                await player.ws.send_json(data)
            except (ConnectionResetError, RuntimeError):
                pass

    async def all(self, data):
        import asyncio
        await asyncio.gather(*(self.send_to(p, data) for p in self.connected()), return_exceptions=True)

    async def announce(self, message, kind='info'):
        await self.all({'type': 'event', 'message': message, 'kind': kind})

    async def broadcast_room(self):
        await self.all(self.lobby_state())

    def add(self, requested_slot, ws, existing_token=None):
        for p in self.players.values():
            if existing_token and secrets.compare_digest(p.token, existing_token):
                if p.ws is not None and not p.ws.closed:
                    return None, '이미 다른 창에서 접속 중입니다.'
                p.ws, p.last_seen = ws, time.monotonic()
                self.last_active = p.last_seen
                if self.host is None:
                    self.host = p.token
                return p, None
        if self.phase != 'lobby':
            return None, '진행 중인 경기는 기존 참가자만 재접속할 수 있어요.'
        if len(self.players) >= 3:
            return None, '최대 3명이 참가할 수 있어요.'
        slot = next(s for s in (1, 2, 3) if s not in self.players)
        p = Player(slot, secrets.token_urlsafe(28), ws)
        self.players[slot] = p
        if self.host is None:
            self.host = p.token
        self.last_active = time.monotonic()
        return p, None

    def remove(self, player):
        player.ws = None
        player.last_seen = self.last_active = time.monotonic()
        if self.host == player.token:
            self.host = next((p.token for p in self.connected()), None)

    async def begin(self):
        if self.phase != 'lobby' or not self.connected():
            return False
        self.players = {p.slot: p for p in self.connected()}
        self.phase, self.seconds, self.wave, self.spawned = 'playing', 0, 0, 0
        self.winner = self.result = None
        self.participants = len(self.players)
        for p in self.players.values():
            p.__init__(p.slot, p.token, p.ws)
            self.summon(p, free=True)
            self.summon(p, free=True)
        await self.broadcast_room()
        await self.snapshot()
        return True

    def summon(self, p, free=False):
        if len(p.units) >= MAX_UNITS:
            return '배치 공간이 가득 찼어요. 같은 포켓몬 3마리를 합성하세요.'
        if not free and p.gold < 40:
            return '소환에는 40코인이 필요해요.'
        if not free:
            p.gold -= 40
        tier = random.choices((1, 2, 3, 4), weights=(70, 23, 6, 1))[0]
        dex = random.choice([d for d in CATALOG.values() if d['tier'] == tier])
        cell = next(i for i in range(MAX_UNITS) if all(u['cell'] != i for u in p.units))
        self.uid += 1
        p.units.append({'id': self.uid, 'dex': dex['dex'], 'cell': cell, 'power': 1, 'cooldown': 0})

    def action(self, p, data):
        if self.phase != 'playing' or p.hp <= 0:
            return '생존 중인 경기에서만 사용할 수 있어요.'
        now = time.monotonic()
        if now - p.last_action < .12:
            return None
        p.last_action = now
        typ = data['type']
        if typ == 'summon':
            return self.summon(p)
        if typ == 'upgrade':
            cost = 70 + p.level * 40
            if p.level >= 10 or p.gold < cost:
                return '강화 한도에 도달했거나 코인이 부족해요.'
            p.gold -= cost
            p.level += 1
        elif typ in ('merge', 'move'):
            u = next((u for u in p.units if u['id'] == data.get('id')), None)
            if u is None:
                return '포켓몬을 선택해 주세요.'
            if typ == 'move':
                cell = data.get('cell')
                if type(cell) is not int or not 0 <= cell < MAX_UNITS:
                    return '잘못된 배치 위치입니다.'
                other = next((v for v in p.units if v['cell'] == cell), None)
                if other:
                    other['cell'] = u['cell']
                u['cell'] = cell
                return None
            same = [v for v in p.units if v['dex'] == u['dex'] and v['power'] == u['power']]
            if len(same) < 3:
                return '같은 포켓몬·같은 강화 단계 3마리가 필요해요.'
            if u['power'] >= 8:
                return '최대 합성 단계입니다.'
            for v in [v for v in same if v is not u][:2]:
                p.units.remove(v)
            evolution = CATALOG[u['dex']]['evolution']
            if evolution:
                u['dex'] = evolution
            else:
                u['power'] *= 2
        elif typ == 'raid':
            targets = [v for v in self.players.values() if v is not p and v.hp > 0]
            if not targets:
                return '공격할 생존 상대가 없어요.'
            if p.gold < 80 or p.raid_ready > 0:
                return '습격에는 80코인과 15초 재사용 대기가 필요해요.'
            if any(len(v.enemies) >= 90 for v in targets):
                return '상대 필드에 적이 너무 많아요.'
            p.gold -= 80
            p.raid_ready = 15
            for target in targets:
                self.spawn(target, raid=True)

    def spawn(self, p, raid=False, boss=False):
        self.uid += 1
        hp = (22 + self.wave ** 1.55 * 9) * (5 if boss else 1.8 if raid else 1)
        p.enemies.append({'id': self.uid, 'progress': 0, 'hp': hp, 'maxHp': hp,
                          'boss': boss, 'raid': raid, 'slow': 0})

    @staticmethod
    def position(progress):
        # Clockwise rectangular route around a 4x3 placement grid.
        t = min(31.99, progress)
        if t < 10:
            return t, 0
        if t < 16:
            return 10, t - 10
        if t < 26:
            return 26 - t, 6
        return 0, 32 - t

    def simulate(self, p, dt):
        p.effects = []
        p.raid_ready = max(0, p.raid_ready - dt)
        for u in p.units:
            u['cooldown'] -= dt
            if u['cooldown'] > 0:
                continue
            d = CATALOG[u['dex']]
            x, y = 2 + u['cell'] % 4 * 2, 1.5 + u['cell'] // 4 * 1.5
            targets = sorted((e for e in p.enemies if e['hp'] > 0 and math.dist((x, y), self.position(e['progress'])) <= 4.4),
                             key=lambda e: e['progress'], reverse=True)
            if not targets:
                continue
            u['cooldown'] = .7 if d['role'] == 'electric' else 1.0
            damage = (8 * 2.3 ** (d['tier'] - 1)) * u['power'] * (1 + .18 * p.level)
            critical = random.random() < .15
            if critical:
                damage *= 2
            hit = targets[:3] if d['role'] in ('fire', 'electric', 'psychic') else targets[:1]
            for e in hit:
                e['hp'] -= damage
                if d['role'] in ('water', 'ice', 'grass'):
                    e['slow'] = 1.4
                p.effects.append({'unit': u['id'], 'progress': e['progress'], 'role': d['role'], 'critical': critical})
        for e in p.enemies[:]:
            if e['hp'] <= 0:
                p.enemies.remove(e)
                p.gold += 16 if e['boss'] else 5
                p.kills += 1
                continue
            e['slow'] = max(0, e['slow'] - dt)
            e['progress'] += dt * (1.25 + min(.85, self.wave * .025)) * (.55 if e['slow'] else 1)
            if e['progress'] >= 32:
                p.enemies.remove(e)
                p.hp = max(0, p.hp - (5 if e['boss'] else 2 if e['raid'] else 1))
        if p.hp <= 0:
            p.eliminated_at = self.seconds
            p.enemies.clear()

    async def snapshot(self):
        self.seq += 1
        await self.all({'type': 'state', 'seq': self.seq, 'phase': self.phase, 'wave': self.wave,
                        'seconds': round(self.seconds, 1), 'nextWave': round(WAVE_LENGTH - self.seconds % WAVE_LENGTH, 1),
                        'players': [p.public() for p in self.players.values()], 'result': self.result})

    def finish(self):
        self.phase = 'finished'
        ranked = sorted(self.players.values(), key=lambda p: (p.hp > 0, p.eliminated_at if p.eliminated_at is not None else self.seconds), reverse=True)
        best = ranked[0]
        tied = [p for p in ranked if p.hp == 0 and p.eliminated_at == best.eliminated_at]
        self.winner = best.slot if self.participants > 1 and (best.hp > 0 or len(tied) == 1) else None
        self.result = {'winner': self.winner, 'solo': self.participants == 1, 'wave': self.wave,
                       'seconds': round(self.seconds, 1), 'scores': [p.public() for p in ranked]}

    async def tick(self, dt):
        now = time.monotonic()
        changed = False
        for slot, p in list(self.players.items()):
            if p.ws is None and now - p.last_seen > 30:
                if self.phase == 'lobby':
                    del self.players[slot]
                    changed = True
                elif self.phase == 'playing' and p.hp > 0:
                    p.hp, p.eliminated_at = 0, self.seconds
                    p.enemies.clear()
        if changed:
            await self.broadcast_room()
        if self.phase == 'playing':
            self.seconds += dt
            wave = int(self.seconds // WAVE_LENGTH) + 1
            if wave != self.wave:
                self.wave, self.spawned = wave, 0
                for p in self.players.values():
                    if p.hp > 0:
                        p.gold += 35 + wave * 2
            wanted = min(12 + self.wave * 2, 35, int((self.seconds % WAVE_LENGTH) / .65) + 1)
            while self.spawned < wanted:
                for p in self.players.values():
                    if p.hp > 0:
                        self.spawn(p, boss=self.wave % 5 == 0 and self.spawned == 0)
                self.spawned += 1
            for p in self.players.values():
                if p.hp > 0:
                    self.simulate(p, dt)
            alive = [p for p in self.players.values() if p.hp > 0]
            if not alive or (self.participants > 1 and len(alive) == 1):
                self.finish()
        if self.phase != 'lobby' and now - self.last_broadcast >= .1:
            self.last_broadcast = now
            await self.snapshot()

