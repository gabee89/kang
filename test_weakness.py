import unittest
from unittest.mock import patch
from defense import Room, attack_damage, CATALOG
from test_defense import Socket


class WeaknessTests(unittest.IsolatedAsyncioTestCase):
    async def room(self):
        r=Room('WEAK')
        r.add(None,Socket())
        await r.begin()
        return r,r.players[1]

    def test_opposite_weaknesses_change_damage_and_keep_neutral_unchanged(self):
        for weakness in ('melee','ranged',None):
            for mode in ('melee','ranged'):
                enemy={'hp':1000,'shield':0,'weakness':weakness}
                Room.hurt(enemy,100,mode)
                expected=100 if weakness is None else 160 if weakness==mode else 55
                self.assertAlmostEqual(1000-enemy['hp'],expected)

    async def test_regular_attack_and_ranged_ultimate_use_their_own_modes(self):
        r,p=await self.room()
        u={'id':100,'dex':4,'cell':0,'power':1,'cooldown':0,'energy':0}
        p.units=[u]
        r.spawn(p)
        enemy=p.enemies[0]
        enemy.update(hp=10000,shield=0,weakness='melee')
        with patch('defense.random.random',return_value=1),patch.object(Room,'inflict'):
            r.simulate(p,.01)
        self.assertAlmostEqual(10000-enemy['hp'],attack_damage(u)*1.6)
        enemy['hp']=10000
        u['energy']=100
        with patch('defense.random.random',return_value=1),patch.object(Room,'inflict'):
            r.simulate(p,.01)
        self.assertEqual(CATALOG[4]['ultimateMode'],'ranged')
        self.assertAlmostEqual(10000-enemy['hp'],attack_damage(u,special=True)*.55)

    async def test_burn_keeps_attack_mode_resistance(self):
        r,p=await self.room()
        p.units=[]
        r.spawn(p)
        enemy=p.enemies[0]
        enemy.update(hp=1000,shield=0,weakness='melee')
        r.inflict(enemy,'fire',100,mode='ranged')
        r.simulate(p,1)
        self.assertAlmostEqual(1000-enemy['hp'],12*.55)

    async def test_special_spawn_schedule_is_fair_and_bosses_alternate(self):
        r=Room('PAIR')
        p,_=r.add(None,Socket())
        q,_=r.add(None,Socket())
        await r.begin()
        r.wave=2
        r.spawned=2
        r.spawn(p)
        self.assertIsNone(p.enemies[-1]['weakness'])
        r.wave=3
        for number,weakness in ((2,'melee'),(4,'ranged'),(0,None)):
            r.spawned=number
            r.spawn(p)
            r.spawn(q)
            self.assertEqual(p.enemies[-1]['weakness'],weakness)
            self.assertEqual(q.enemies[-1]['weakness'],weakness)
        for wave,weakness in ((5,'melee'),(10,'ranged'),(15,'melee'),(20,'ranged')):
            r.wave=wave
            r.spawn(p,boss=True)
            self.assertEqual(p.enemies[-1]['weakness'],weakness)

    def test_weakness_stacks_with_armor_and_absorbs_shield(self):
        enemy={'hp':1000,'shield':100,'variant':'armored','weakness':'melee'}
        Room.hurt(enemy,100,'melee')
        self.assertEqual(enemy['shield'],0)
        self.assertAlmostEqual(enemy['hp'],988)


if __name__=='__main__':
    unittest.main()

