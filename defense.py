"""Server-authoritative, independent-lane luck defense simulation."""
import math
import random
import secrets
import time
import json
from bisect import bisect_right
from pathlib import Path
from moves import profile
from individuals import roll_ivs, iv_factor, attack_interval, iv_grade
from elements import TYPES, effectiveness

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
    (131, '라프라스', None, 'ice', 2),
]
CATALOG = {d[0]: dict(zip(('dex', 'name', 'evolution', 'role', 'tier'), d)) for d in DEX}
for dex, data in CATALOG.items():
    data.update(profile(dex))
    data['ultimateMode']='melee' if data['ultimate']=='몸통박치기' else 'ranged'
    data['status'] = {'fire':'화상 · 강한 지속 피해', 'electric':'마비 · 잠시 정지', 'ice':'냉기 · 이동 -65%',
                      'water':'젖음 · 전기 피해 +25% / 이동 -35%', 'grass':'중독 · 최대 3중첩', 'ghost':'저주 · 받는 피해 +15%',
                      'psychic':'약점 노출 · 다음 공격 피해 +50%'}[data['role']]
for line in ((1,2,3),(4,5,6),(7,8,9),(92,93,94),(25,26),(129,130),(131,),(144,),(145,),(146,),(150,)):
    for stage,dex in enumerate(line):
        CATALOG[dex].update({'lineLength':len(line),'stage':stage+1,
                            'growthBonus':(1,1.3,1.9)[stage] if len(line)==3 else (1,1.8)[stage] if len(line)==2 else 1.2})
WAVE_LENGTH = 90
DIFFICULTIES = {'normal': .8, 'challenge': 1.25, 'extreme': 1.8}
MAP = json.loads((Path(__file__).parent / 'assets' / 'map.json').read_text(encoding='utf-8'))
CELL_COUNT = len(MAP['cells'])
MAX_UNITS = CELL_COUNT*3
ROUTE_LENGTH = sum(math.dist(a, b) for a, b in zip(MAP['route'], MAP['route'][1:]))
ROUTE_CUMULATIVE=[0]
for a,b in zip(MAP['route'],MAP['route'][1:]):
    ROUTE_CUMULATIVE.append(ROUTE_CUMULATIVE[-1]+math.dist(a,b))


def summon_odds(level=0):
    level=max(0,min(10,level))
    middle=3+level*1.4
    final=.7+level*.55
    legendary=.3+level*.15
    return {'base':100-middle-final-legendary,'middle':middle,'final':final,'legendary':legendary}


def luck_cost(level):
    return 100+level*90


def region_info(cell):
    return next((r for r in MAP.get('regions',[]) if r['id']==MAP['terrain'][cell]), {})


def terrain_multiplier(dex, cell, special=False):
    region,role=MAP['terrain'][cell],CATALOG[dex]['role']
    if region=='fire':return 1.25 if role=='fire' else 1.15
    if region=='electric' and special:return 1.3 if role=='electric' else 1.2
    return 1


def region_attack_interval(unit):
    speed=(1.2 if CATALOG[unit['dex']]['role']=='grass' else 1.15) if MAP['terrain'][unit['cell']]=='grass' else 1
    return attack_interval(unit,CATALOG)/speed


def energy_multiplier(unit):
    if MAP['terrain'][unit['cell']]!='water':return 1
    return 1.4 if CATALOG[unit['dex']]['role'] in ('water','ice') else 1.25


def critical_chance(unit):
    if MAP['terrain'][unit['cell']]!='ghost':return .15
    return .25 if CATALOG[unit['dex']]['role']=='ghost' else .20


def sell_value(unit):
    return (15, 30, 60, 120)[CATALOG[unit['dex']]['tier'] - 1] * unit['power'] * (1+unit.get('enhance',0))


def attack_damage(unit, level=0, special=False):
    d = CATALOG[unit['dex']]
    return (8 * 2.3 ** (d['tier']-1) * unit['power'] * (1+.18*level) * d['damageMultiplier']
            * terrain_multiplier(unit['dex'],unit['cell'],special) * (1+.4*unit.get('enhance',0))
            * d['growthBonus'] * (1+.15*unit.get('evolutions',0))
            * iv_factor(unit,'special' if special and d['ultimate']!='몸통박치기' or not special and d['mode']=='ranged' else 'attack')
            * (d['ultimatePower'] if special else d['movePower']))


def experience_need(unit):
    d=CATALOG[unit['dex']]
    if not d['evolution']:
        return 0
    return 650 if d['lineLength']==2 else 400 if d['stage']==1 else 1000


def weakness_multiplier(enemy,mode):
    weakness=enemy.get('weakness')
    return (1.6 if weakness==mode else .55) if weakness in ('melee','ranged') and mode in ('melee','ranged') else 1


class Player:
    def __init__(self, slot, token, ws):
        self.slot, self.token, self.ws = slot, token, ws
        self.name=f'트레이너 {slot}'
        self.last_seen = time.monotonic()
        self.hp, self.gold, self.level, self.kills = 20, 160, 0, 0
        self.units, self.enemies, self.effects = [], [], []
        self.eliminated_at = None
        self.last_action = -100
        self.raid_ready = 0
        self.luck_level = 0
        self.boss_damage=0
        self.boss_round_damage=0
        self.damage=0
        self.rounds_cleared=0
        self.score=0

    def public(self, weather=None):
        weather=weather or {}
        return {'id': self.slot, 'name': self.name, 'hp': self.hp,
                'score':self.score,'bossDamage':round(self.boss_damage),'bossRoundDamage':round(self.boss_round_damage),'damage':round(self.damage),'roundsCleared':self.rounds_cleared,
                'gold': self.gold, 'level': self.level, 'kills': self.kills,
                'connected': self.ws is not None and not self.ws.closed,
                'alive': self.hp > 0, 'eliminatedAt': self.eliminated_at,
                'raidReady': round(self.raid_ready, 1),
                'luckLevel':self.luck_level,'luckCost':luck_cost(self.luck_level),
                'summonOdds':summon_odds(self.luck_level),
                'units': [{**{k: v for k, v in u.items() if k != 'cooldown'}, 'sellValue': sell_value(u),
                           'attackDamage':round(attack_damage(u,self.level)*weather.get(CATALOG[u['dex']]['role'],1),1),
                           'ultimateDamage':round(attack_damage(u,self.level,True)*weather.get(CATALOG[u['dex']]['role'],1),1),
                           'attackInterval':round(region_attack_interval(u),3),'ivGrade':iv_grade(u),
                           'region':region_info(u['cell']),'criticalChance':critical_chance(u),
                           'xpNeed':experience_need(u)} for u in self.units],
                'enemies': [{k: v for k, v in e.items() if k not in ('burnDps','poisonDps','paraImmune')} for e in self.enemies],
                'effects': self.effects}


class BattleRoom:
    def __init__(self, room_code):
        self.code, self.players, self.host = room_code, {}, None
        self.phase, self.seconds, self.wave = 'lobby', 0, 0
        self.winner, self.result = None, None
        self.created = self.last_active = time.monotonic()
        self.last_broadcast, self.seq, self.uid, self.spawned = 0, 0, 0, 0
        self.participants = 0
        self.effect_seq = 0
        self.speed = 1
        self.difficulty = 'challenge'

    def connected(self):
        return [p for p in self.players.values() if p.ws is not None and not p.ws.closed]

    def lobby_state(self):
        return {'type': 'room', 'code': self.code, 'phase': self.phase,
                'hostSlot': next((p.slot for p in self.players.values() if p.token == self.host), None),
            'difficulty': self.difficulty,
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
        self.speed = 1
        self.participants = len(self.players)
        for p in self.players.values():
            name=p.name
            p.__init__(p.slot, p.token, p.ws)
            p.name=name
            self.summon(p, free=True)
            self.summon(p, free=True)
        await self.broadcast_room()
        await self.snapshot()
        return True

    def configure(self, player, value):
        if self.phase != 'lobby' or self.host != player.token:
            return '대기실에서 방장만 난이도를 변경할 수 있어요.'
        if not isinstance(value, str) or value not in DIFFICULTIES:
            return '지원하지 않는 난이도입니다.'
        self.difficulty = value
        return None

    @staticmethod
    def stack_limit(dex):
        return 3 if CATALOG[dex]['evolution'] else 2

    def summon_cell(self,p,dex):
        # Fill a matching stack before opening another cell, including moved units.
        matching=sorted({u['cell'] for u in p.units if u['dex']==dex})
        for cell in matching:
            if self.can_place(p,dex,cell):return cell
        return next((i for i in range(CELL_COUNT) if not any(u['cell']==i for u in p.units)),None)

    def can_place(self,p,dex,cell,exclude=None):
        occupants=[u for u in p.units if u['cell']==cell and u is not exclude]
        return not occupants or all(u['dex']==dex for u in occupants) and len(occupants)<self.stack_limit(dex)

    def merge_unit(self,p,u):
        evolution=CATALOG[u['dex']]['evolution']
        required=3 if evolution else 2
        same=sorted((v for v in p.units if v['dex']==u['dex'] and v['power']==u['power'] and v.get('enhance',0)==u.get('enhance',0)),key=lambda v:(v['cell'],v['id']))
        if len(same)<required:return f'같은 포켓몬·강화 단계 {required}마리가 필요해요.'
        if u.get('enhance',0)>=10:return '최대 합성 단계입니다.'
        materials=sorted((v for v in same if v is not u),key=lambda v:(v['cell']!=u['cell'],v['cell'],v['id']))[:required-1]
        next_dex=evolution or u['dex']
        remaining=[v for v in p.units if v is not u and all(v is not m for m in materials)]
        def fits(cell):
            occupants=[v for v in remaining if v['cell']==cell]
            return not occupants or all(v['dex']==next_dex for v in occupants) and len(occupants)<self.stack_limit(next_dex)
        destination=next((cell for cell in [u['cell'],*range(CELL_COUNT)] if fits(cell)),None)
        if destination is None:return '진화체를 놓을 공간이 필요해요. 먼저 판매하거나 칸을 비워주세요.'
        if any(v.get('ivs') for v in [u,*materials]):
            u['ivs']={key:max(v.get('ivs',{}).get(key,0) for v in [u,*materials]) for key in ('attack','special','speed')}
        u['xp']=sum(v.get('xp',0) for v in [u,*materials])
        for v in materials:p.units.remove(v)
        previous=u['dex']
        if evolution:
            u['dex']=evolution
            u['evolutions']=u.get('evolutions',0)+1
        else:u['enhance']=u.get('enhance',0)+1
        u['energy'],u['cooldown']=0,.5
        u['cell']=destination
        self.effect(p,u,'evolve',[],move=CATALOG[u['dex']]['name'],fromDex=previous,enhanced=not bool(evolution))

    def summon(self, p, free=False):
        if len(p.units) >= MAX_UNITS:
            return f'{MAX_UNITS}칸이 가득 찼어요. 합성하거나 선택한 포켓몬을 판매해 공간을 확보하세요.'
        if not free and p.gold < 40:
            return '소환에는 40코인이 필요해요.'
        odds=summon_odds(p.luck_level)
        group = random.choices(tuple(odds),weights=tuple(odds.values()))[0]
        if group=='base':
            dex_id=random.choices((1,4,7,92,129,25,131),weights=(18,18,18,16,16,10,4))[0]
        else:
            dex_id=random.choice({'middle':(2,5,8,93),'final':(3,6,9,26,94,130),'legendary':(144,145,146,150)}[group])
        dex=CATALOG[dex_id]
        cell=self.summon_cell(p,dex_id)
        if cell is None:
            return '같은 포켓몬 중첩 또는 빈 칸이 필요해요. 합성·판매로 공간을 확보하세요.'
        if not free:p.gold-=40
        self.uid += 1
        p.units.append({'id': self.uid, 'dex': dex['dex'], 'cell': cell, 'power': 1, 'cooldown': 0, 'energy': 0,
                        'enhance':0,'ivs':roll_ivs(),'xp':0,'evolutions':0,'source':group})

    def action(self, p, data):
        if self.phase != 'playing' or p.hp <= 0:
            return '생존 중인 경기에서만 사용할 수 있어요.'
        now = time.monotonic()
        if now - p.last_action < .12:
            return None
        p.last_action = now
        typ = data['type']
        if typ == 'speed':
            if self.host != p.token:
                return '방장만 배속을 변경할 수 있어요.'
            value = data.get('value')
            if type(value) is not int or value not in (1, 2, 3):
                return '배속은 1, 2, 3배만 가능합니다.'
            self.speed = value
            return None
        if typ == 'sell':
            unit = next((u for u in p.units if u['id'] == data.get('id')), None)
            if unit is None:
                return '판매할 포켓몬을 선택해 주세요.'
            p.gold += sell_value(unit)
            p.units.remove(unit)
            return None
        if typ == 'summon':
            return self.summon(p)
        if typ == 'luck':
            cost=luck_cost(p.luck_level)
            if p.luck_level>=10:
                return '소환 행운이 최대 단계입니다.'
            if p.gold<cost:
                return f'소환 행운 강화에 {cost}코인이 필요해요.'
            p.gold-=cost
            p.luck_level+=1
            return None
        if typ == 'upgrade':
            cost = 70 + p.level * 40
            if p.level >= 10 or p.gold < cost:
                return '강화 한도에 도달했거나 코인이 부족해요.'
            p.gold -= cost
            p.level += 1
        elif typ=='quick_merge':
            for u in sorted(p.units,key=lambda v:(v['cell'],v['id'])):
                needed=3 if CATALOG[u['dex']]['evolution'] else 2
                if u.get('enhance',0)<10 and sum(v['dex']==u['dex'] and v['power']==u['power'] and v.get('enhance',0)==u.get('enhance',0) for v in p.units)>=needed:
                    return self.merge_unit(p,u)
            return '합성할 동일 포켓몬이 부족해요.'
        elif typ in ('merge','move'):
            u=next((v for v in p.units if v['id']==data.get('id')),None)
            if u is None:return '포켓몬을 선택해 주세요.'
            if typ=='merge':return self.merge_unit(p,u)
            cell=data.get('cell')
            if type(cell) is not int or not 0<=cell<CELL_COUNT:return '잘못된 배치 위치입니다.'
            if self.can_place(p,u['dex'],cell,u):
                u['cell']=cell
                return None
            other=[v for v in p.units if v['cell']==cell]
            if len(other)==1 and self.can_place(p,other[0]['dex'],u['cell'],u):
                other[0]['cell'],u['cell']=u['cell'],cell
                return None
            return '동일 포켓몬만 3마리까지, 최종형은 2마리까지 중첩할 수 있어요.'
        elif typ == 'raid':
            if self.game_mode=='coop' or self.stage!='combat':return '경쟁전 일반 라운드에서만 습격할 수 있어요.'
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

    def spawn(self, p, raid=False, boss=False, golden=False, boss_rank=None):
        self.uid += 1
        if boss and boss_rank is None:
            boss_rank = 'boss' if self.wave % 10 == 0 else 'elite'
        plan=self.encounter_plan()
        dex = 149 if boss_rank == 'boss' else 95 if boss else plan['dex']
        name = {19:'꼬렛',41:'주뱃',46:'파라스',74:'꼬마돌',23:'아보',48:'콘팡',66:'알통몬',111:'뿔카노',52:'황금 나옹',95:'중간보스 롱스톤',149:'보스 망나뇽'}[dex]
        if golden and not boss:name='황금 '+name
        variant = 'boss' if boss else ('runner' if self.spawned % 4 == 1 else
                   'armored' if self.wave >= 2 and self.spawned % 4 == 2 else
                   'shielded' if self.wave >= 3 and self.spawned % 4 == 3 else 'normal')
        growth = 1.035 ** max(0,self.wave-1)
        hp = (65 + self.wave ** 1.65 * 14) * growth * DIFFICULTIES[self.difficulty] * (10 if boss_rank == 'boss' else 5 if boss else 1.8 if raid else 1)
        hp *= .7 if variant == 'runner' else 1.4 if variant == 'armored' else 1
        flank = plan['entry']=='shortcut' and not boss
        weakness = ('melee' if self.wave%10 else 'ranged') if boss else (
            'melee' if self.wave>=3 and self.spawned%5==2 else 'ranged' if self.wave>=3 and self.spawned%5==4 else None)
        p.enemies.append({'id': self.uid, 'progress': MAP.get('flankProgress',12.5) if flank else 0, 'flank':flank, 'hp': hp, 'maxHp': hp,
                          'weakness':weakness,'types':TYPES[dex],
                          'boss': boss, 'bossRank': boss_rank, 'dex': dex, 'name': name,
                          'variant': variant, 'shield': hp * .5 if variant == 'shielded' else 0,
                          'raid': raid, 'golden': golden, 'slow': 0, 'slowFactor':1,
                          'burn':0, 'burnDps':0, 'poison':0, 'poisonDps':0, 'poisonStacks':0, 'poisonBase':0,
                          'stun':0, 'paraImmune':0, 'curse':0, 'wet':0, 'expose':0})

    @staticmethod
    def position(progress):
        if progress <= 0:
            return tuple(MAP['route'][0])
        if progress >= ROUTE_LENGTH:
            return tuple(MAP['route'][-1])
        t = progress
        i=min(len(MAP['route'])-2,max(0,bisect_right(ROUTE_CUMULATIVE,t)-1))
        a,b=MAP['route'][i:i+2]
        fraction=(t-ROUTE_CUMULATIVE[i])/(ROUTE_CUMULATIVE[i+1]-ROUTE_CUMULATIVE[i])
        return a[0]+(b[0]-a[0])*fraction,a[1]+(b[1]-a[1])*fraction

    @staticmethod
    def path_speed(progress):
        return next((z['speed'] for z in MAP['zones'] if z['start'] <= progress < z['end']), 1)

    def gain_experience(self,p):
        # One point per kill for each deployed unit; never controlled by the client.
        for u in p.units:
            u['xp']=u.get('xp',0)+1
            need=experience_need(u)
            if need and u['xp']>=need:
                old=u['dex']
                next_dex=CATALOG[old]['evolution']
                destination=u['cell'] if self.can_place(p,next_dex,u['cell'],u) else self.summon_cell(p,next_dex)
                if destination is None:
                    continue
                u['cell']=destination
                u['xp']-=need
                u['dex']=CATALOG[old]['evolution']
                u['evolutions']=u.get('evolutions',0)+1
                u['cooldown']=.5
                u['energy']=0
                self.effect(p,u,'evolve',[],move=CATALOG[u['dex']]['name'],fromDex=old,reason='experience')

    def effect(self, p, u, kind, targets, **extra):
        self.effect_seq += 1
        d = CATALOG[u['dex']]
        p.effects.append({'id': self.effect_seq, 'kind': kind, 'unit': u['id'], 'cell': u['cell'],
                          'dex': u['dex'], 'role': d['role'], 'mode': d['mode'], 'style': d['style'],
                          'created': self.seconds, 'targets': [e['progress'] for e in targets],
                          'victims': [e['id'] for e in targets], **extra})
        p.effects = p.effects[-80:]

    @staticmethod
    def hurt(e, damage, mode=None):
        dealt = damage * weakness_multiplier(e,mode) * (.7 if e.get('variant') == 'armored' else 1) * (1.15 if e.get('curse',0)>0 else 1)
        blocked = min(e.get('shield',0), dealt)
        e['shield'] = max(0, e.get('shield',0) - blocked)
        e['hp'] -= dealt - blocked

    @staticmethod
    def inflict(e, role, damage, special=False, mode=None):
        if role in ('water','ice'):
            factor = max(.65 if e.get('boss') else .35, .35 if role == 'ice' else .65)
            e['slowFactor'] = min(e.get('slowFactor',1), factor) if e.get('slow',0)>0 else factor
            e['slow'] = max(e.get('slow',0), 3 if special else 1.8)
            if role=='water':
                e['wet'] = 5 if special else 3
        elif role=='fire':
            e['burn'] = max(e.get('burn',0), 5 if special else 3)
            if damage*.12>=e.get('burnDps',0):
                e['burnMode']=mode
            e['burnDps'] = max(e.get('burnDps',0), damage*.12)
        elif role=='grass':
            e['poison'] = 5
            e['poisonStacks'] = min(3,e.get('poisonStacks',0)+(2 if special else 1))
            if damage*.06>=e.get('poisonBase',0):
                e['poisonMode']=mode
            e['poisonBase'] = max(e.get('poisonBase',0),damage*.06)
            e['poisonDps'] = e['poisonBase']*e['poisonStacks']
        elif role=='electric':
            if e.get('paraImmune',0)<=0 and (special or random.random()<.3):
                e['stun'] = (.4 if special else .15) if e.get('boss') else (1.3 if special else .55)
                e['paraImmune'] = 4 if e.get('boss') else 3
        elif role == 'ghost':
            e['curse'] = max(e.get('curse',0), 5 if special else 2)
        elif role=='psychic':
            e['expose'] = 5 if special else 3

    def simulate(self, p, dt, advance_enemies=True):
        p.effects = [f for f in p.effects if self.seconds - f['created'] < 1.7]
        p.raid_ready = max(0, p.raid_ready - dt)
        for u in p.units:
            u['energy'] = min(100, u.get('energy', 0) + dt * 7 * energy_multiplier(u))
            u['cooldown'] -= dt
            d = CATALOG[u['dex']]
            x, y = MAP['cells'][u['cell']]
            special = u['energy'] >= 100
            if u['cooldown'] > 0 and not special:
                continue
            attack_range = d['ultimateRange'] if special else d['range']
            targets = sorted((e for e in p.enemies if e['hp'] > 0 and (self.stage=='boss' or math.dist((x, y), self.position(e['progress'])) <= attack_range)),
                             key=lambda e: e['progress'], reverse=True)
            if not targets:
                continue
            u['cooldown'] = region_attack_interval(u)
            damage = attack_damage(u,p.level,special)*self.damage_bonuses().get(d['role'],1)
            critical = random.random() < critical_chance(u)
            if critical:
                damage *= 2
            if special:
                u['energy'] = 0
                hit = targets[:8]
            else:
                u['energy'] = min(100, u['energy'] + 18 * energy_multiplier(u))
                hit = targets[:3] if d['mode'] == 'ranged' and d['role'] in ('fire', 'electric', 'psychic') else targets[:1]
            for e in hit:
                bonus = (1.25 if d['role']=='electric' and e.get('wet',0)>0 else 1) * (1.5 if e.get('expose',0)>0 else 1)
                mode=d['ultimateMode'] if special else d['mode']
                multiplier=effectiveness(d['role'],e.get('types',()))
                before=max(0,e['hp'])
                self.hurt(e, damage * bonus * multiplier,mode)
                dealt=before-max(0,e['hp'])
                p.damage+=dealt
                if self.stage=='boss':
                    p.boss_damage+=dealt
                    p.boss_round_damage+=dealt
                if e.get('expose',0)>0:
                    e['expose'] = 0
                if multiplier>0:
                    burn=e.get('burnDps',0);poison=e.get('poisonBase',0)
                    self.inflict(e, d['role'], damage*multiplier, special,mode)
                    if d['role']=='fire' and damage*multiplier*.12>=burn:e['burnOwner']=p.slot
                    if d['role']=='grass' and damage*multiplier*.06>=poison:e['poisonOwner']=p.slot
            self.effect(p, u, 'ultimate' if special else 'attack', hit,
                        move=d['ultimate'] if special else d['move'], damage=round(damage), critical=critical)
        if not advance_enemies:return
        for e in p.enemies[:]:
            self.status_tick(e,dt)
            if e['hp'] <= 0:
                p.enemies.remove(e)
                p.gold += (60 if e.get('bossRank') == 'boss' else 25 if e['boss'] else 5) + (25 if e.get('golden') else 0)
                p.kills += 1
                self.gain_experience(p)
                continue
            e['slow'] = max(0, e['slow'] - dt)
            immobilized = e.get('stun',0)>0
            for key in ('stun','paraImmune','curse','wet','expose'):
                e[key] = max(0,e.get(key,0)-dt)
            speed = .85 * (1.7 + min(1.3, self.wave * .035)) * (1.55 if e.get('variant') == 'runner' else .8 if e.get('variant') == 'armored' else 1)
            e['progress'] += dt * speed * (0 if immobilized else e.get('slowFactor',.65) if e['slow'] else 1) * self.path_speed(e['progress'])
            if e['progress'] >= ROUTE_LENGTH:
                p.enemies.remove(e)
                self.leak(p,e)
        if p.hp <= 0:
            p.eliminated_at = self.seconds
            p.enemies.clear()

    def status_tick(self,e,dt):
        for key in ('burn','poison'):
            remaining=e.get(key,0)
            if remaining<=0:continue
            before=max(0,e['hp'])
            self.hurt(e,e.get(key+'Dps',0)*min(dt,remaining),e.get(key+'Mode'))
            dealt=before-max(0,e['hp'])
            owner=self.players.get(e.get(key+'Owner'))
            if owner:
                owner.damage+=dealt
                if self.stage=='boss':
                    owner.boss_damage+=dealt
                    owner.boss_round_damage+=dealt
            e[key]=max(0,remaining-dt)
            if e[key]==0:
                e[key+'Dps']=0
                if key=='poison':e['poisonStacks']=e['poisonBase']=0

    async def snapshot(self):
        from rounds import damage_bonuses
        weather=damage_bonuses(self.next_plan) if self.stage=='prep' else self.damage_bonuses()
        self.seq += 1
        await self.all({'type': 'state', 'seq': self.seq, 'phase': self.phase, 'wave': self.wave,
                        'speed': self.speed, 'capacity': MAX_UNITS,
                        'difficulty': self.difficulty,'gameMode':self.game_mode,'stage':self.stage,
                        'roundPlan':self.next_plan if self.stage=='prep' else self.active_plan,
                        'stageLeft':round(self.stage_left,1),'teamHp':self.team_hp,'cleared':self.cleared,'boss':self.shared_boss,
                        'seconds': round(self.seconds, 1), 'nextWave': round(self.stage_left,1),
                        'players': [p.public(weather) for p in self.players.values()], 'result': self.result})

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
            # Fixed substeps keep combat fair at every speed; disconnect timeout uses wall time above.
            scaled = dt * self.speed
            while scaled > 1e-9 and self.phase == 'playing':
                step = min(.05, scaled)
                self.advance(step)
                scaled -= step
        if self.phase != 'lobby' and now - self.last_broadcast >= .1:
            self.last_broadcast = now
            await self.snapshot()



from campaign import Campaign
class Room(Campaign,BattleRoom):
    pass


