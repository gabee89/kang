import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from defense import Room,MAP,ROUTE_LENGTH,CATALOG,CELL_COUNT,MAX_UNITS
from elements import effectiveness
from leaderboard import Leaderboard
from test_defense import Socket

class CampaignTests(unittest.IsolatedAsyncioTestCase):
    async def room(self,count=3,mode='competitive'):
        r=Room('CAMP')
        for _ in range(count):r.add(None,Socket())
        r.game_mode=mode
        await r.begin()
        return r

    def action(self,r,p,**data):
        p.last_action=-100
        return r.action(p,data)

    def unit(self,id=100,dex=4,cell=0,**extra):
        return {'id':id,'dex':dex,'cell':cell,'power':1,'cooldown':0,'energy':0,'ivs':{'attack':1,'special':1,'speed':1},'xp':0,**extra}

    async def test_preparation_pauses_enemies_and_ignores_combat_speed(self):
        r=await self.room(1);p=r.players[1]
        r.speed=3
        await r.tick(1)
        self.assertEqual(r.stage,'prep');self.assertAlmostEqual(r.stage_left,9)
        self.assertEqual(r.seconds,0);self.assertEqual(p.enemies,[])
        await r.tick(9.01)
        self.assertEqual((r.wave,r.stage),(1,'combat'))

    async def test_mode_is_host_only_and_lobby_only(self):
        r=Room('MODE');p,_=r.add(None,Socket());q,_=r.add(None,Socket())
        self.assertIsNotNone(r.configure_mode(q,'coop'))
        self.assertIsNone(r.configure_mode(p,'coop'))
        self.assertIsNotNone(r.configure_mode(p,'forged'))
        await r.begin();self.assertIsNotNone(r.configure_mode(p,'competitive'))
        self.assertEqual(r.lobby_state()['gameMode'],'coop')

    async def test_three_trainers_share_one_boss_and_all_attack(self):
        r=await self.room();r.wave=9;r.start_round()
        self.assertEqual(r.stage,'boss');boss=r.shared_boss
        boss['hp']=boss['maxHp']=100000
        for p in r.players.values():p.units=[self.unit(dex=150)]
        with patch('defense.random.random',return_value=1):r.boss_step(.1)
        self.assertTrue(all(p.boss_damage>0 for p in r.players.values()))
        self.assertAlmostEqual(100000-boss['hp'],sum(p.boss_damage for p in r.players.values()))
        self.assertTrue(all(not p.enemies for p in r.players.values()))
        self.assertTrue(all(p.units[0]['cell']==0 for p in r.players.values()))

    async def test_boss_dot_ticks_once_not_per_participant(self):
        r=await self.room();r.wave=9;r.start_round();boss=r.shared_boss
        for p in r.players.values():p.units=[]
        before=boss['hp'];boss.update(burn=3,burnDps=100,burnOwner=1)
        r.boss_step(.2)
        self.assertAlmostEqual(before-boss['hp'],20)
        self.assertAlmostEqual(r.players[1].boss_damage,20)

    async def test_coop_transfer_cycle_preserves_enemy_and_defers_update(self):
        r=await self.room(mode='coop');r.start_round();r.spawned=48
        for p in r.players.values():p.units=[];p.enemies=[]
        p=r.players[1];r.spawn(p);enemy=p.enemies[0];enemy['progress']=ROUTE_LENGTH-.001
        hp=enemy['hp'];r.advance(.1)
        self.assertIs(r.players[2].enemies[0],enemy)
        self.assertEqual((enemy['progress'],enemy['hp'],r.team_hp),(0,hp,59))
        for source,destination in ((2,3),(3,1)):
            enemy['progress']=ROUTE_LENGTH-.001;r.advance(.1)
            self.assertIs(r.players[destination].enemies[0],enemy)
            self.assertEqual(enemy['progress'],0)
        self.assertEqual(enemy['passes'],3)
        self.assertIsNotNone(self.action(r,p,type='raid'))

    async def test_stack_caps_and_quick_merge_preserve_independent_iv_maxima(self):
        r=await self.room(1);p=r.players[1]
        p.units=[self.unit(id=100+i,cell=i,ivs={'attack':31 if i==0 else 2,'special':30 if i==1 else 1,'speed':29 if i==2 else 0}) for i in range(3)]
        self.assertIsNone(self.action(r,p,type='move',id=101,cell=0))
        self.assertIsNone(self.action(r,p,type='move',id=102,cell=0))
        self.assertEqual([u['cell'] for u in p.units],[0,0,0])
        self.assertFalse(r.can_place(p,4,0))
        self.assertFalse(r.can_place(p,7,0))
        self.assertIsNone(self.action(r,p,type='quick_merge'))
        self.assertEqual(len(p.units),1)
        self.assertEqual((p.units[0]['id'],p.units[0]['dex'],p.units[0]['cell']),(100,5,0))
        self.assertEqual(p.units[0]['ivs'],{'attack':31,'special':30,'speed':29})
        p.units=[self.unit(id=100+i,dex=6,cell=0) for i in range(2)]
        self.assertFalse(r.can_place(p,6,0))

    async def test_round_50_ends_and_scores_everyone_and_rematch_resets(self):
        r=await self.room(mode='coop');r.wave=49;r.start_round();r.shared_boss['hp']=0
        r.boss_step(.05)
        self.assertEqual(r.phase,'finished');self.assertTrue(r.result['completed'])
        self.assertEqual(len(r.result['scores']),3)
        self.assertTrue(all(p['score']>=35000 for p in r.result['scores']))
        r.phase='lobby';old=r.run_id;await r.begin()
        self.assertNotEqual(old,r.run_id);self.assertEqual((r.wave,r.stage,r.cleared),(0,'prep',0))

    def test_dual_type_effectiveness_and_gen_one_immunities(self):
        self.assertEqual(effectiveness('water',('rock','ground')),4)
        self.assertEqual(effectiveness('grass',('bug','grass')),.25)
        self.assertEqual(effectiveness('electric',('rock','ground')),0)
        self.assertEqual(effectiveness('ghost',('normal',)),0)
        self.assertEqual(effectiveness('psychic',('poison','flying')),2)

    async def test_rankings_are_server_results_idempotent_and_difficulty_separated(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Leaderboard(str(Path(folder)/'ranks.db'))
            await store.initialize();r=await self.room(1);r.finish()
            await store.record(r);await store.record(r)
            self.assertEqual(len(await store.top()),1)
            self.assertEqual(await store.top('normal'),[])
            reopened=Leaderboard(str(Path(folder)/'ranks.db'));await reopened.initialize()
            self.assertEqual((await reopened.top())[0]['score'],r.players[1].score)
            other=await self.room(3);other.finish();await store.record(other)
            self.assertEqual(len(await store.top()),1)

    async def test_evolution_and_merge_never_make_invalid_mixed_stacks(self):
        r=await self.room(1);p=r.players[1]
        p.units=[self.unit(id=100+i,cell=i%CELL_COUNT,enhance=0) for i in range(MAX_UNITS)]
        for i in range(3):p.units[i]['enhance']=1
        before=[dict(u) for u in p.units]
        self.assertIsNotNone(self.action(r,p,type='merge',id=100))
        self.assertEqual(p.units,before)
        for u in p.units:u['xp']=399
        r.gain_experience(p)
        self.assertTrue(all(u['dex']==4 for u in p.units))
        self.assertTrue(all(u['xp']==400 for u in p.units))

    async def test_final_boss_timeout_is_not_a_fifty_round_clear(self):
        r=await self.room(mode='coop');r.wave=49;r.start_round()
        for p in r.players.values():p.units=[]
        r.stage_left=0;r.boss_step(.1)
        self.assertEqual(r.phase,'finished')
        self.assertFalse(r.result['completed'])
        self.assertTrue(all(p['roundsCleared']==0 for p in r.result['scores']))


