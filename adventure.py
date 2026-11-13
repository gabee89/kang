"""Server-owned choices, objectives and bounded composition bonuses."""
import random
import math
from collections import Counter

CHOICE_ROUNDS={5,15,25,35,45}
CHOICE_SECONDS=18
BONUS_CAPS={'damage':.45,'energy':.40,'speed':.25,'crit':.45,'combinedDamage':1.8,'combinedEnergy':1.8}
CARDS={
 'fire':dict(name='불꽃의 가호',icon='🔥',description='불 공격 피해 +15%',grade='희귀',cap=2),
 'electric':dict(name='번개의 축복',icon='⚡',description='전기 게이지 충전 +15%',grade='희귀',cap=2),
 'ice':dict(name='얼음의 지배자',icon='❄',description='얼음 공격 피해 +12%',grade='희귀',cap=2),
 'grass':dict(name='자연의 힘',icon='🌿',description='풀 공격 속도 +12%',grade='희귀',cap=2),
 'income':dict(name='행운의 손길',icon='🪙',description='처치 코인 +10%',grade='희귀',cap=2),
 'gold':dict(name='황금의 계약',icon='💰',description='즉시 150코인',grade='일반',cap=2),
 'critical':dict(name='치명적 집중',icon='🎯',description='치명타 확률 +5%p',grade='영웅',cap=2),
 'ultimate':dict(name='필살기 전문가',icon='✨',description='필살기 피해 +12%',grade='영웅',cap=2),
 'evolution':dict(name='진화의 축복',icon='🧬',description='합성·진화 시 30코인 · 라운드당 2회',grade='희귀',cap=1),
 'defense':dict(name='굳건한 방어',icon='🛡',description='즉시 생명 2 회복 · 시작 상한 적용',grade='일반',cap=2),
}
SYNERGIES={
 'overload':dict(name='과부하',icon='🔥⚡',roles=('fire','electric'),effect='해당 속성 필살 피해 +8%'),
 'frost':dict(name='빙결 협공',icon='💧❄',roles=('water','ice'),effect='해당 속성 게이지 충전 +12%'),
 'curse':dict(name='생명의 저주',icon='🌿👻',roles=('grass','ghost'),effect='해당 속성 직접 피해 +8%'),
 'focus':dict(name='정신 집중',icon='🔮⚡',roles=('psychic','electric'),effect='해당 속성 치명타 +5%p'),
}
MISSIONS={
 'hunter':dict(name='사냥꾼',description='이번 구간 적 30마리 처치',target=30,reward=100),
 'flawless':dict(name='완벽한 방어',description='생명 손실 없이 연속 2라운드 방어',target=2,reward=120),
 'collector':dict(name='속성 수집가',description='서로 다른 속성 4종 동시 보유',target=4,reward=100),
 'evolution':dict(name='진화 전문가',description='합성·진화 3회',target=3,reward=120),
 'boss':dict(name='보스 사냥꾼',description='공동 보스 체력의 10% 이상 기여',target=1,reward=150),
}
SUPPORTS={'attack':dict(name='공격 지원',cost=80),'defense':dict(name='긴급 방어',cost=120),'energy':dict(name='필살기 지원',cost=100)}
SUPPORT_COOLDOWN=20

def new_progress():
    return dict(cards={},offer=[],choiceRound=0,mission=None,legendary=0,evolutions=0,missions=0,
                supports=0,damageTaken=0,evolutionPaid=0,rewardSeq=0,lastReward=None,incomeRemainder=0,
                supportReady=0,attackUntil=0,wardUntil=0,energyLock=0,defenseUses=0)

def refresh_traits(p):
    from defense import CATALOG
    p.traits=Counter(CATALOG[u['dex']]['role'] for u in p.units)

def synergy_state(p):
    refresh_traits(p)
    return [dict(id=id,**data,counts=[p.traits[r] for r in data['roles']],
                 active=all(p.traits[r]>=2 for r in data['roles'])) for id,data in SYNERGIES.items()]

def modifiers(p,u,special=False):
    from defense import CATALOG
    role=CATALOG[u['dex']]['role'];cards=p.progress['cards'];counts=getattr(p,'traits',{})
    active=lambda id:role in SYNERGIES[id]['roles'] and all(counts.get(r,0)>=2 for r in SYNERGIES[id]['roles'])
    damage=(.15*cards.get('fire',0) if role=='fire' else .12*cards.get('ice',0) if role=='ice' else 0)
    damage+=.12*cards.get('ultimate',0) if special else 0
    damage+=.1 if p.progress['attackUntil']>getattr(p,'room_seconds',0) else 0
    damage+=.08 if special and active('overload') else 0
    dot=1+min(BONUS_CAPS['damage'],damage)
    damage+=.08 if active('curse') else 0
    energy=(.15*cards.get('electric',0) if role=='electric' else 0)+(.12 if active('frost') else 0)
    speed=.12*cards.get('grass',0) if role=='grass' else 0
    crit=.05*cards.get('critical',0)+(.05 if active('focus') else 0)
    return dict(damage=1+min(BONUS_CAPS['damage'],damage),dot=dot,energy=1+min(BONUS_CAPS['energy'],energy),
                speed=1+min(BONUS_CAPS['speed'],speed),crit=crit)

def public_progress(p):
    return dict(cards=[dict(id=id,count=n,**CARDS[id]) for id,n in p.progress['cards'].items()],
                choices=[dict(id=id,**CARDS[id]) for id in p.progress['offer']],
                choiceRound=p.progress['choiceRound'],mission=p.progress['mission'],synergies=synergy_state(p),
                support=dict(readyIn=round(max(0,p.progress['supportReady']-getattr(p,'room_seconds',0)),1),
                    attackLeft=round(max(0,p.progress['attackUntil']-getattr(p,'room_seconds',0)),1),
                    ward=p.progress['wardUntil']>getattr(p,'room_seconds',0),defenseUses=p.progress['defenseUses']),
                stats={k:p.progress[k] for k in ('legendary','evolutions','missions','supports')},
                lastReward=p.progress['lastReward'])

def kill_reward(p,base):
    bonus=base*.1*p.progress['cards'].get('income',0)+p.progress['incomeRemainder']
    whole=math.floor(bonus+1e-9);p.progress['incomeRemainder']=bonus-whole
    return base+whole


class Adventure:
    def __init__(self,*args,**kwargs):
        self.adventure_event={'id':0};super().__init__(*args,**kwargs)

    async def begin(self):
        if self.phase=='lobby':self.adventure_event={'id':0}
        return await super().begin()

    def reward(self,p,coins,message):
        p.gold+=coins;p.progress['rewardSeq']+=1
        p.progress['lastReward']=dict(id=p.progress['rewardSeq'],coins=coins,message=message)

    def check_mission(self,p):
        m=p.progress['mission']
        if not m or m['status']!='active':return
        key=m['kind']
        if key=='hunter':value=p.kills-m['startKills']
        elif key=='collector':refresh_traits(p);value=len(p.traits)
        elif key=='evolution':value=p.progress['evolutions']-m['startEvolutions']
        else:value=m['progress']
        m['progress']=min(m['target'],value)
        if value>=m['target']:
            m['status']='completed';p.progress['missions']+=1
            self.reward(p,m['reward'],'미션 성공 · '+m['name'])

    def start_round(self):
        for p in self.players.values():
            if p.progress['offer']:self.choose_card(p,random.choice(p.progress['offer']))
        super().start_round()
        for p in self.players.values():
            p.progress['evolutionPaid']=0
            if p.hp<=0:continue
            if self.wave in (1,11,21,31,41):
                old=p.progress['mission']
                if old and old['status']=='active':old['status']='expired'
                kind=random.choice(tuple(MISSIONS));data=MISSIONS[kind]
                p.progress['mission']=dict(kind=kind,key=f'{self.run_id}:{p.slot}:{self.wave}',**data,
                    progress=0,status='active',until=self.wave+9,startKills=p.kills,
                    startEvolutions=p.progress['evolutions'])
            p.progress['roundHits']=p.progress['damageTaken']
            self.check_mission(p)

    def choose_card(self,p,id):
        if self.phase!='playing' or self.stage!='prep' or p.hp<=0:return '정비 중에만 카드를 선택할 수 있어요.'
        if not isinstance(id,str) or id not in p.progress['offer']:return '선택할 수 없는 카드입니다.'
        if p.progress['choiceRound']!=self.wave:return '카드 선택 시간이 지났어요.'
        counts=p.progress['cards'];data=CARDS[id]
        if counts.get(id,0)>=data['cap']:return '최대 중첩입니다.'
        counts[id]=counts.get(id,0)+1;p.progress['offer']=[]
        if id=='gold':self.reward(p,150,'황금의 계약')
        elif id=='defense':
            if self.game_mode=='coop' and self.participants>1:self.team_hp=min(20*self.participants,self.team_hp+2)
            else:p.hp=min(20,p.hp+2)
        if id!='gold':self.reward(p,0,'운명의 선택 · '+data['name'])
        return None

    def complete_round(self,success=True):
        for p in self.players.values():
            m=p.progress['mission']
            if m and m['status']=='active' and m['kind']=='boss' and self.shared_boss and p.boss_round_damage>=self.shared_boss['maxHp']*.1:
                m['progress']=1
            if m and m['status']=='active' and m['kind']=='flawless':
                m['progress']=m['progress']+1 if success and p.hp>0 and p.progress['damageTaken']==p.progress.get('roundHits',0) else 0
            self.check_mission(p)
            if m and m['status']=='active' and self.wave>=m['until']:m['status']='expired'
        super().complete_round(success)
        if success and self.phase=='playing' and self.wave in CHOICE_ROUNDS:
            for p in self.players.values():
                if p.hp<=0:continue
                pool=[id for id,data in CARDS.items() if p.progress['cards'].get(id,0)<data['cap']]
                p.progress['offer']=random.sample(pool,min(3,len(pool)));p.progress['choiceRound']=self.wave
            self.stage_left=CHOICE_SECONDS

    def evolution_event(self,p,count):
        if not count:return
        p.progress['evolutions']+=count
        if p.progress['cards'].get('evolution'):
            paid=min(count,2-p.progress['evolutionPaid'])
            if paid>0:p.progress['evolutionPaid']+=paid;self.reward(p,30*paid,'진화의 축복')
        self.check_mission(p)

    def merge_unit(self,p,u):
        error=super().merge_unit(p,u)
        if error is None:self.evolution_event(p,1)
        return error

    def gain_experience(self,p):
        before={u['id']:u['dex'] for u in p.units};super().gain_experience(p)
        self.evolution_event(p,sum(before.get(u['id'])!=u['dex'] for u in p.units))

    def summon(self,p,free=False):
        error=super().summon(p,free)
        if error is None:
            if p.units[-1].get('source')=='legendary':p.progress['legendary']+=1
            self.check_mission(p)
        return error

    def simulate(self,p,dt,advance_enemies=True):
        p.room_seconds=self.seconds;refresh_traits(p);super().simulate(p,dt,advance_enemies)
        self.check_mission(p)

    def leak(self,p,e):
        from defense import MAP,ROUTE_LENGTH
        coop=self.game_mode=='coop' and self.participants>1
        amount=self.protect_damage(p,1 if coop else 8 if e.get('bossRank')=='boss' else 4 if e['boss'] else 2 if e['raid'] else 1)
        if coop:
            before=self.team_hp;self.team_hp=max(0,self.team_hp-amount)
            for target in self.players.values():target.progress['damageTaken']+=before-self.team_hp
            alive=sorted((v for v in self.players.values() if v.hp>0),key=lambda v:v.slot)
            if alive and self.team_hp>0:
                target=next((v for v in alive if v.slot>p.slot),alive[0]);entry=self.encounter_plan()['entry']=='shortcut'
                progress=(ROUTE_LENGTH-MAP['flankProgress'] if e.get('direction',1)==-1 else MAP['flankProgress']) if entry else 0
                e.update(progress=progress,flank=entry,passes=e.get('passes',0)+1);self.transfers.append((target,e))
            if self.team_hp<=0:
                for target in self.players.values():target.hp=0
        else:
            before=p.hp;p.hp=max(0,p.hp-amount);p.progress['damageTaken']+=before-p.hp
            if self.participants==1:self.team_hp=p.hp

    def protect_damage(self,p,amount):
        if p.progress['wardUntil']>self.seconds:
            p.progress['wardUntil']=0;return max(0,amount-1)
        return amount

    def support_skill(self,p,kind,target_id):
        if self.game_mode!='coop' or self.participants<2:return '다른 팀원이 있는 협동전에서만 지원할 수 있어요.'
        if self.phase!='playing' or self.stage not in ('combat','boss') or p.hp<=0:return '생존 중인 전투에서만 지원할 수 있어요.'
        if not isinstance(kind,str) or kind not in SUPPORTS or type(target_id) is not int:return '지원 종류나 대상이 올바르지 않아요.'
        target=self.players.get(target_id)
        if target is None or target is p or target.hp<=0 or target.ws is None or target.ws.closed:return '접속 중인 다른 생존 팀원을 선택하세요.'
        if p.progress['supportReady']>self.seconds:return '지원 재사용 대기 중입니다.'
        if p.gold<SUPPORTS[kind]['cost']:return '지원 코인이 부족합니다.'
        if kind=='attack' and target.progress['attackUntil']>self.seconds:return '이미 공격 지원을 받고 있어요.'
        if kind=='defense' and (target.progress['wardUntil']>self.seconds or p.progress['defenseUses']>=3):return '방어 지원은 중복 불가 · 경기당 3회입니다.'
        if kind=='energy' and target.progress['energyLock']>self.seconds:return '대상이 필살기 지원 재사용 대기 중입니다.'
        if kind=='energy' and not any(u.get('energy',0)<100 for u in target.units):return '충전할 포켓몬이 없어요.'
        p.gold-=SUPPORTS[kind]['cost'];p.progress['supportReady']=self.seconds+SUPPORT_COOLDOWN;p.progress['supports']+=1
        if kind=='attack':target.progress['attackUntil']=self.seconds+10
        elif kind=='defense':target.progress['wardUntil']=self.seconds+30;p.progress['defenseUses']+=1
        else:
            target.progress['energyLock']=self.seconds+15
            for u in target.units:u['energy']=min(100,u.get('energy',0)+30)
        self.reward(target,0,p.name+' → '+SUPPORTS[kind]['name'])
        self.reward(p,0,target.name+'에게 '+SUPPORTS[kind]['name'])
        return None

    def boss_step(self,dt):
        boss=self.shared_boss
        if not boss:return
        if boss['hp']>0:
            ratio=boss['hp']/boss['maxHp'];boss.setdefault('patternPhase',1)
            if ratio<=.70 and not boss.get('shieldTriggered'):
                boss.update(shieldTriggered=True,shield=boss['maxHp']*.08,patternPhase=2)
                self.boss_notice('shield','보스 보호막 등장')
            if ratio<=.35 and boss['patternPhase']<3:
                boss['patternPhase']=3;self.boss_notice('enrage','보스 광폭화 · 제한시간 소모 +15%')
            if boss['patternPhase']==3:self.stage_left=max(0,self.stage_left-dt*.15)
        boss['exposed']=max(0,boss.get('exposed',0)-dt);shield=boss.get('shield',0)
        super().boss_step(dt)
        if shield>0 and boss.get('shield',0)<=0 and boss['hp']>0:
            boss['exposed']=2.5;self.boss_notice('break','보호막 파괴! 2.5초간 피해 +15%')
        if boss['hp']<=0:self.boss_notice('victory','공동 보스 격파!')

    def boss_notice(self,kind,message):
        self.adventure_event=dict(id=self.adventure_event['id']+1,kind=kind,message=message)

    def finish(self):
        if self.phase=='finished':return
        for p in self.players.values():
            m=p.progress['mission']
            if m and m['status']=='active':m['status']='expired'
        super().finish()
        awards={p.slot:[] for p in self.players.values()}
        def title(id,name,icon,metric):
            values={p.slot:metric(p) for p in self.players.values()};best=max(values.values(),default=0)
            if best>0:
                for slot,value in values.items():
                    if value==best:awards[slot].append(dict(id=id,name=name,icon=icon))
        title('boss','보스 사냥꾼','🐲',lambda p:p.boss_damage)
        title('legendary','전설 소환왕','🌟',lambda p:p.progress['legendary'])
        title('evolution','진화의 달인','🧬',lambda p:p.progress['evolutions'])
        title('support','지원왕','🤝',lambda p:p.progress['supports'])
        title('survival','생존왕','🛡',lambda p:p.rounds_cleared*100+p.hp if p.rounds_cleared else 0)
        contribution=lambda p:p.kills*2+p.damage/100+p.boss_damage/50+p.progress['supports']*50+p.progress['missions']*60+p.rounds_cleared*20
        ranked=sorted(self.players.values(),key=lambda p:(-contribution(p),-p.score,p.slot))
        mvp=ranked[0].slot if ranked and contribution(ranked[0])>0 else None
        if mvp:awards[mvp].insert(0,dict(id='mvp',name='MVP',icon='🏆'))
        self.result.update(mvpSlot=mvp,awards={str(k):v for k,v in awards.items()},
            contribution={str(p.slot):round(contribution(p),1) for p in self.players.values()})

    def action(self,p,data):
        if data.get('type')=='choose_card':return self.choose_card(p,data.get('id'))
        if data.get('type')=='support':return self.support_skill(p,data.get('skill'),data.get('target'))
        error=super().action(p,data)
        self.check_mission(p)
        return error

    async def snapshot(self):
        for p in self.players.values():p.room_seconds=self.seconds
        await super().snapshot()

