import random
import unittest
from defense import Room,CATALOG,attack_damage,experience_need
from individuals import iv_factor,attack_interval
from test_defense import Socket


class GrowthTests(unittest.IsolatedAsyncioTestCase):
    async def setup_room(self):
        r=Room('GROW')
        r.add(None,Socket())
        await r.begin()
        return r,r.players[1]

    def unit(self,dex=1,**extra):
        return {'id':100,'dex':dex,'cell':0,'power':1,'cooldown':0,'energy':0,'xp':0,'enhance':0,
                'evolutions':0,'ivs':{'attack':15,'special':15,'speed':15},**extra}

    async def test_ivs_change_relevant_damage_and_interval(self):
        low=self.unit(ivs={'attack':0,'special':0,'speed':0})
        high=self.unit(ivs={'attack':31,'special':31,'speed':31})
        self.assertAlmostEqual(attack_damage(high)/attack_damage(low),1.1/.9)
        self.assertAlmostEqual(attack_interval(high,CATALOG)/attack_interval(low,CATALOG),.88)
        special=self.unit(25,ivs={'attack':31,'special':0,'speed':0})
        self.assertEqual(iv_factor(special,'special'),.9)
        special['ivs']['attack']=0
        before=attack_damage(special)
        special['ivs']['attack']=31
        self.assertEqual(attack_damage(special),before)

    async def test_summons_roll_stable_bounded_individual_values(self):
        r,p=await self.setup_room()
        p.units=[]
        for _ in range(36):
            r.summon(p,True)
        self.assertGreater(len({tuple(u['ivs'].values()) for u in p.units}),25)
        for u in p.units:
            self.assertTrue(all(type(v) is int and 0<=v<=31 for v in u['ivs'].values()))
        self.assertEqual(p.public()['units'][0]['ivs'],p.units[0]['ivs'])

    async def test_manual_merge_keeps_selected_ivs_and_all_experience(self):
        r,p=await self.setup_room()
        good={'attack':31,'special':30,'speed':31}
        p.units=[self.unit(ivs=good,xp=100),self.unit(id=101,cell=1,xp=40),self.unit(id=102,cell=2,xp=25)]
        before=attack_damage(p.units[0],special=True)
        p.last_action=-100
        self.assertIsNone(r.action(p,{'type':'merge','id':100}))
        u=p.units[0]
        self.assertEqual((u['dex'],u['xp'],u['ivs'],u['evolutions']),(2,165,good,1))
        self.assertGreater(attack_damage(u,special=True),before*1.5)

    async def test_experience_evolution_is_slow_and_two_stage_needs_650(self):
        r,p=await self.setup_room()
        p.units=[self.unit()]
        original=dict(p.units[0]['ivs'])
        for _ in range(399):
            r.gain_experience(p)
        self.assertEqual(p.units[0]['dex'],1)
        r.gain_experience(p)
        self.assertEqual((p.units[0]['dex'],p.units[0]['xp']),(2,0))
        self.assertEqual(experience_need(p.units[0]),1000)
        for _ in range(999):
            r.gain_experience(p)
        self.assertEqual(p.units[0]['dex'],2)
        r.gain_experience(p)
        self.assertEqual(p.units[0]['dex'],3)
        self.assertEqual(p.units[0]['ivs'],original)
        self.assertEqual(p.effects[-1]['reason'],'experience')
        p.units=[self.unit(25,xp=649)]
        r.gain_experience(p)
        self.assertEqual(p.units[0]['dex'],26)

    async def test_non_evolving_and_manual_final_growth_are_distinct(self):
        r,p=await self.setup_room()
        self.assertEqual((CATALOG[3]['lineLength'],CATALOG[26]['lineLength'],CATALOG[131]['lineLength']),(3,2,1))
        direct=self.unit(3)
        trained=self.unit(3,evolutions=2)
        self.assertAlmostEqual(attack_damage(trained)/attack_damage(direct),1.3)
        p.units=[self.unit(131,xp=10000)]
        r.gain_experience(p)
        self.assertEqual(p.units[0]['dex'],131)
        self.assertEqual(experience_need(p.units[0]),0)

    async def test_base_forms_dominate_draws_and_final_forms_are_rare(self):
        r,p=await self.setup_room()
        saved=random.getstate()
        try:
            random.seed(24)
            counts={}
            for _ in range(2000):
                p.units=[]
                r.summon(p,True)
                group=p.units[0]['source']
                counts[group]=counts.get(group,0)+1
            self.assertGreater(counts['base'],1850)
            self.assertLess(counts.get('final',0),40)
            self.assertLess(counts.get('legendary',0),20)
        finally:
            random.setstate(saved)


if __name__=='__main__':
    unittest.main()

