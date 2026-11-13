import unittest
from unittest.mock import patch
from defense import Room, MAX_UNITS, WAVE_LENGTH, attack_damage, CATALOG, CELL_COUNT
from test_defense import Socket,near


class UpgradeTests(unittest.IsolatedAsyncioTestCase):
    async def room(self, count=1):
        room=Room('CHECK')
        for _ in range(count):
            room.add(None,Socket())
        await room.begin()
        room.stage='combat'
        room.stage_left=90
        room.wave=1
        return room

    def action(self,r,p,**data):
        p.last_action=-100
        return r.action(p,data)

    async def test_24_slots_sale_and_resummon_no_double_sale(self):
        r=await self.room(2)
        p,q=r.players.values()
        p.gold=10000
        p.units=[{'id':100+i,'dex':1,'cell':i%CELL_COUNT,'power':1,'cooldown':0} for i in range(MAX_UNITS)]
        self.assertEqual(len(p.units),MAX_UNITS)
        self.assertIsNotNone(self.action(r,p,type='summon'))
        unit=p.units[-1]
        refund=p.public()['units'][-1]['sellValue']
        gold=p.gold
        self.assertIsNotNone(self.action(r,q,type='sell',id=unit['id']))
        self.assertIsNone(self.action(r,p,type='sell',id=unit['id']))
        self.assertEqual(p.gold,gold+refund)
        self.assertIsNotNone(self.action(r,p,type='sell',id=unit['id']))
        with patch('defense.random.choices',side_effect=[['base'],[1]]):
            self.assertIsNone(self.action(r,p,type='summon'))
        self.assertEqual(len(p.units),MAX_UNITS)
        self.assertEqual(len({u['cell'] for u in p.units}),CELL_COUNT)

    async def test_speed_is_host_only_and_scales_simulation(self):
        r=await self.room(2)
        p,q=r.players.values()
        self.assertIsNotNone(self.action(r,q,type='speed',value=3))
        for value in (True,0,4,'3'):
            self.assertIsNotNone(self.action(r,p,type='speed',value=value))
        self.assertIsNone(self.action(r,p,type='speed',value=3))
        await r.tick(.1)
        self.assertAlmostEqual(r.seconds,.3)
        self.assertEqual(r.speed,3)

    async def test_midboss_and_boss_have_distinct_health_and_visuals(self):
        r=await self.room(2)
        for wave in (5,10,15,20):
            r.wave=wave-1
            for p in r.players.values():
                p.enemies=[]
            r.start_round()
            await r.tick(.01)
            bosses=[r.shared_boss]*2 if wave%10==0 else [p.enemies[0] for p in r.players.values()]
            self.assertEqual([e['bossRank'] for e in bosses],['boss' if wave%10==0 else 'elite']*2)
            self.assertTrue(all(e['dex']==(149 if wave%10==0 else 95) for e in bosses))
            self.assertEqual(bosses[0]['maxHp'],bosses[1]['maxHp'])

    async def test_difficulty_host_lobby_only_and_health_scales(self):
        r=Room('CHECK')
        p,_=r.add(None,Socket())
        q,_=r.add(None,Socket())
        self.assertIsNotNone(r.configure(q,'normal'))
        self.assertIsNone(r.configure(p,'extreme'))
        await r.begin()
        self.assertIsNotNone(r.configure(p,'normal'))
        r.wave=1
        r.spawn(p)
        extreme=p.enemies[-1]['maxHp']
        r.difficulty='normal'
        r.spawn(p)
        self.assertAlmostEqual(extreme/p.enemies[-1]['maxHp'],1.7/.75)

    async def test_burn_poison_tick_and_expire_without_stacking(self):
        r=await self.room()
        p=r.players[1]
        p.units=[]
        r.spawn(p)
        e=p.enemies[0]
        e['hp']=1000
        r.inflict(e,'fire',100)
        r.inflict(e,'fire',100)
        r.inflict(e,'grass',100)
        r.simulate(p,1)
        self.assertAlmostEqual(e['hp'],982)
        r.simulate(p,2)
        self.assertEqual(e['burn'],0)
        self.assertEqual(e['poison'],2)
        r.simulate(p,2)
        self.assertEqual(e['poison'],0)
        self.assertEqual(e['burnDps'],0)
        self.assertAlmostEqual(e['hp'],934)

    async def test_paralysis_ice_water_and_boss_resistance(self):
        r=await self.room()
        p=r.players[1]
        p.units=[]
        r.spawn(p)
        e=p.enemies[0]
        r.inflict(e,'electric',100,True)
        r.simulate(p,.1)
        self.assertEqual(e['progress'],0)
        # Anti-chain-stun cooldown cannot be reset by another attack.
        e['stun']=0
        r.inflict(e,'electric',100,True)
        self.assertEqual(e['stun'],0)
        r.inflict(e,'ice',100)
        r.inflict(e,'water',100)
        self.assertEqual(e['slowFactor'],.35)
        r.spawn(p,boss=True)
        boss=p.enemies[-1]
        r.inflict(boss,'ice',100,True)
        r.inflict(boss,'electric',100,True)
        self.assertEqual(boss['slowFactor'],.65)
        self.assertEqual(boss['stun'],.4)

    async def test_shield_armor_and_curse_damage(self):
        enemy={'hp':100,'shield':20,'variant':'armored','curse':0}
        Room.hurt(enemy,100)
        self.assertEqual(enemy['hp'],50)
        self.assertEqual(enemy['shield'],0)
        enemy['curse']=2
        Room.hurt(enemy,10)
        self.assertAlmostEqual(enemy['hp'],41.95)

    async def test_poison_stacks_to_three_and_psychic_exposes_next_hit(self):
        r=await self.room()
        p=r.players[1]
        r.spawn(p)
        e=p.enemies[-1]
        for _ in range(5):
            r.inflict(e,'grass',100)
        self.assertEqual(e['poisonStacks'],3)
        self.assertEqual(e['poisonDps'],18)
        r.inflict(e,'psychic',100)
        self.assertGreater(e['expose'],0)
        p.units=[{'id':100,'dex':7,'power':1,'cell':0,'cooldown':0,'energy':0}]
        e['hp']=10000
        e['progress']=near(0)
        e['types']=[]
        e['progress']=near(0)
        e['types']=[]
        e['poison']=0
        before=e['hp']
        with patch('defense.random.random',return_value=1):
            r.simulate(p,.01)
        self.assertAlmostEqual(before-e['hp'],attack_damage(p.units[0])*1.5)
        self.assertEqual(e['expose'],0)

    async def test_wet_amplifies_electric_damage(self):
        r=await self.room()
        p=r.players[1]
        r.spawn(p)
        e=p.enemies[-1]
        p.units=[{'id':100,'dex':25,'power':1,'cell':0,'cooldown':0,'energy':0}]
        r.inflict(e,'water',100)
        e['hp']=10000
        e['progress']=near(0)
        e['types']=[]
        with patch('defense.random.random',return_value=1):
            r.simulate(p,.01)
        self.assertAlmostEqual(10000-e['hp'],attack_damage(p.units[0])*1.25)

    async def test_final_evolution_two_to_one_enhancement_and_cap(self):
        r=await self.room()
        p=r.players[1]
        p.units=[{'id':i+100,'dex':6,'power':1,'cell':i,'cooldown':0,'energy':50,'enhance':0} for i in range(2)]
        damage=attack_damage(p.units[0])
        self.assertIsNone(self.action(r,p,type='merge',id=100))
        self.assertEqual(len(p.units),1)
        self.assertEqual(p.units[0]['enhance'],1)
        self.assertEqual(p.units[0]['energy'],0)
        self.assertAlmostEqual(attack_damage(p.units[0])/damage,1.4)
        self.assertTrue(p.effects[-1]['enhanced'])
        p.units[0]['enhance']=10
        p.units.append({**p.units[0],'id':101,'cell':1})
        self.assertIsNotNone(self.action(r,p,type='merge',id=100))
        self.assertEqual(len(p.units),2)

    async def test_moves_have_distinct_damage_and_attack_intervals(self):
        self.assertLess(CATALOG[25]['interval'],CATALOG[94]['interval'])
        self.assertLess(CATALOG[25]['movePower'],CATALOG[94]['movePower'])
        self.assertNotEqual(CATALOG[6]['ultimatePower'],CATALOG[25]['ultimatePower'])


if __name__=='__main__':
    unittest.main()


