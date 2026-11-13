"""Fifty-round state machine and shared boss encounters. Combat remains authoritative."""
import secrets

PREPARATION=8
FINAL_ROUND=50

class Campaign:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.game_mode='competitive'
        self.reset_campaign()

    def reset_campaign(self):
        self.stage='prep'
        self.stage_left=PREPARATION
        self.round_time=0
        self.cleared=0
        self.shared_boss=None
        self.transfers=[]
        self.team_hp=0
        self.run_id=secrets.token_hex(16)
        self.ranking_saved=False
        self.ranking_pending=False
        self.ranking_retry=0
        self.completed=False

    async def begin(self):
        if self.phase!='lobby' or not self.connected():
            return False
        self.reset_campaign()
        self.team_hp=20*len(self.connected())
        return await super().begin()

    def configure_mode(self,player,value):
        if self.phase!='lobby' or self.host!=player.token:
            return '대기실에서 방장만 모드를 선택할 수 있어요.'
        if value not in ('competitive','coop'):
            return '지원하지 않는 모드입니다.'
        self.game_mode=value

    def lobby_state(self):
        return {**super().lobby_state(),'gameMode':self.game_mode}

    def start_round(self):
        self.wave+=1
        self.spawned=0
        self.round_time=0
        self.stage='boss' if self.wave%10==0 else 'combat'
        self.stage_left=75 if self.stage=='boss' else 90
        for p in self.players.values():
            p.effects=[]
            if p.hp>0:
                p.gold+=35+self.wave*2
        if self.stage=='boss':
            alive=[p for p in self.players.values() if p.hp>0]
            if not alive:return
            self.spawn(alive[0],boss=True,boss_rank='boss')
            boss=alive[0].enemies.pop()
            boss.update(progress=0,flank=False,types=('dragon','flying'),weakness=None)
            # Scale with the round and participants, never with current DPS.
            from defense import DIFFICULTIES
            boss['hp']=boss['maxHp']=(3500+self.wave**2*35)*len(alive)*DIFFICULTIES[self.difficulty]
            self.shared_boss=boss
            for p in self.players.values():
                p.boss_round_damage=0
                p.enemies.clear()
                for u in p.units:u['cooldown']=0

    def complete_round(self,success=True):
        success=success and any(p.hp>0 for p in self.players.values())
        if success:self.cleared=self.wave
        for p in self.players.values():
            p.effects=[]
            if success and p.hp>0:p.rounds_cleared=self.wave
        if self.wave>=FINAL_ROUND:
            self.completed=success
            self.finish()
        else:
            self.stage='prep'
            self.stage_left=PREPARATION
            self.shared_boss=None

    def leak(self,p,e):
        if self.game_mode=='coop' and self.participants>1:
            self.team_hp=max(0,self.team_hp-1)
            alive=sorted((v for v in self.players.values() if v.hp>0),key=lambda v:v.slot)
            if alive and self.team_hp>0:
                target=next((v for v in alive if v.slot>p.slot),alive[0])
                e.update(progress=0,flank=False,passes=e.get('passes',0)+1)
                # Deferred until everyone has simulated: no double movement this tick.
                self.transfers.append((target,e))
            if self.team_hp<=0:
                for v in self.players.values():v.hp=0
        else:
            p.hp=max(0,p.hp-(8 if e.get('bossRank')=='boss' else 4 if e['boss'] else 2 if e['raid'] else 1))
            if self.participants==1:self.team_hp=p.hp

    def boss_step(self,dt):
        boss=self.shared_boss
        if not boss:return
        for p in self.players.values():
            if p.hp<=0:continue
            p.enemies=[boss]
            self.simulate(p,dt,advance_enemies=False)
            p.enemies=[]
        self.status_tick(boss,dt)
        for key in ('slow','stun','paraImmune','curse','wet','expose'):
            boss[key]=max(0,boss.get(key,0)-dt)
        if boss['hp']<=0:
            for p in self.players.values():
                if p.hp>0:
                    p.gold+=150+self.wave*8
                    p.kills+=1
                    self.gain_experience(p)
            self.complete_round()
        elif self.stage_left<=0:
            if self.game_mode=='coop' and self.participants>1:
                self.team_hp=max(0,self.team_hp-8*len([p for p in self.players.values() if p.hp>0]))
                if not self.team_hp:
                    for p in self.players.values():p.hp=0
            else:
                for p in self.players.values():p.hp=max(0,p.hp-8)
            self.complete_round(success=False)

    def advance(self,dt):
        # Preparation uses real time even when the host selects 3x combat.
        if self.stage=='prep':
            self.stage_left=max(0,self.stage_left-dt/self.speed)
            if self.stage_left<=1e-8:self.start_round()
        else:
            self.seconds+=dt
            self.round_time+=dt
            self.stage_left=max(0,self.stage_left-dt)
            if self.stage=='boss':
                self.boss_step(dt)
            else:
                total=min(18+self.wave*2,48)
                wanted=min(total,int(self.round_time/.48)+1)
                while self.spawned<wanted:
                    for p in self.players.values():
                        if p.hp>0:self.spawn(p,boss=self.wave%5==0 and self.spawned==0,golden=self.wave%3==0 and self.spawned==4)
                    self.spawned+=1
                self.transfers=[]
                for p in self.players.values():
                    if p.hp>0:self.simulate(p,dt)
                for p,e in self.transfers:
                    if p.hp>0 and self.team_hp>0:p.enemies.append(e)
                if self.spawned>=total and not any(p.enemies for p in self.players.values()):
                    self.complete_round()
                elif self.stage_left<=0:
                    # Do not silently erase recycled co-op enemies at the round deadline.
                    if self.game_mode=='coop' and self.participants>1:
                        self.team_hp=max(0,self.team_hp-sum(len(p.enemies) for p in self.players.values()))
                        if not self.team_hp:
                            for p in self.players.values():p.hp=0
                    else:
                        for p in self.players.values():p.hp=max(0,p.hp-len(p.enemies))
                    for p in self.players.values():p.enemies=[]
                    self.complete_round()
        alive=[p for p in self.players.values() if p.hp>0]
        if self.phase=='playing' and (not alive or self.game_mode=='competitive' and self.participants>1 and len(alive)==1):
            self.finish()

    def finish(self):
        if self.phase=='finished':return
        super().finish()
        for p in self.players.values():
            p.score=p.kills*100+p.rounds_cleared*500+int(p.boss_damage/10)+p.hp*50+(10000 if self.completed and p.hp>0 else 0)
        ranked=sorted(self.players.values(),key=lambda p:(p.score,p.hp,p.kills),reverse=True)
        # Original survival winner is retained for competitive early elimination.
        if self.completed and self.game_mode=='competitive' and self.participants>1:
            self.winner=ranked[0].slot if len(ranked)<2 or ranked[0].score>ranked[1].score else None
        self.result.update(winner=self.winner,completed=self.completed,gameMode=self.game_mode,runId=self.run_id,
                           difficulty=self.difficulty,scores=[p.public() for p in ranked])

