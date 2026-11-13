import unittest
from unittest.mock import patch
from defense import Room,Player,MAP,attack_damage
from adventure import CARDS,MISSIONS,modifiers,refresh_traits,synergy_state,kill_reward


class AdventureTests(unittest.TestCase):
    def setUp(self):
        self.r=Room('NEW');self.r.phase='playing';self.r.participants=2
        self.p=Player(1,'one',None);self.q=Player(2,'two',None);self.r.players={1:self.p,2:self.q}
    def unit(self,id=1,dex=4,cell=0):return dict(id=id,dex=dex,cell=cell,power=1,enhance=0,cooldown=0,energy=0,xp=0)
    def offer(self):self.r.wave=5;self.r.complete_round()
    def test_independent_offers_and_single_use(self):
        self.offer()
        self.assertEqual(self.r.stage_left,18)
        self.assertEqual(len(set(self.p.progress['offer'])),3)
        self.assertIsNot(self.p.progress['offer'],self.q.progress['offer'])
        id=self.p.progress['offer'][0];self.assertIsNone(self.r.action(self.p,{'type':'choose_card','id':id}))
        self.assertEqual(self.p.progress['cards'][id],1)
        self.assertIsNotNone(self.r.choose_card(self.p,id))
        self.assertEqual(len(self.q.progress['offer']),3)
    def test_timeout_auto_selects_and_never_delays_other_players(self):
        self.offer();self.r.stage_left=.01;self.r.advance(.02)
        self.assertEqual((self.r.wave,self.r.stage),(6,'combat'))
        self.assertTrue(all(sum(p.progress['cards'].values())==1 and not p.progress['offer'] for p in (self.p,self.q)))
    def test_caps_invalid_choices_and_full_health_limit(self):
        self.offer();before=self.p.gold
        self.assertIsNotNone(self.r.choose_card(self.p,'forged'))
        self.assertEqual(self.p.gold,before)
        self.p.progress['offer']=['defense'];self.p.hp=19
        self.assertIsNone(self.r.choose_card(self.p,'defense'));self.assertEqual(self.p.hp,20)
        self.p.progress['cards']={id:data['cap'] for id,data in CARDS.items()}
        self.r.wave=15;self.r.complete_round();self.assertEqual(self.p.progress['offer'],[])
    def test_mission_reward_is_once_and_expires(self):
        with patch('adventure.random.choice',return_value='hunter'):self.r.start_round()
        before=self.p.gold;self.p.kills=30
        for _ in range(5):self.r.check_mission(self.p)
        self.assertEqual(self.p.gold-before,100);self.assertEqual(self.p.progress['missions'],1)
        m=self.q.progress['mission'];self.r.wave=10;self.r.complete_round()
        self.assertEqual(m['status'],'expired')
    def test_collector_and_evolution_missions_use_real_state(self):
        with patch('adventure.random.choice',return_value='collector'):self.r.start_round()
        self.p.units=[self.unit(i,dex) for i,dex in enumerate((4,7,25,92),1)]
        self.r.check_mission(self.p);self.assertEqual(self.p.progress['mission']['status'],'completed')
        self.p.progress['cards']={'evolution':1};before=self.p.gold
        for _ in range(5):self.r.evolution_event(self.p,1)
        self.assertEqual(self.p.gold-before,60)
    def test_synergy_activation_sale_removal_and_bounded_modifiers(self):
        self.p.units=[self.unit(i,dex,cell=i) for i,dex in enumerate((4,4,25,25),1)]
        self.assertTrue(next(s for s in synergy_state(self.p) if s['id']=='overload')['active'])
        u=self.p.units[0];self.p.progress['cards']={'fire':2,'ultimate':2};refresh_traits(self.p)
        self.assertAlmostEqual(modifiers(self.p,u,True)['damage'],1.45)
        self.r.action(self.p,{'type':'sell','id':4})
        self.assertFalse(next(s for s in synergy_state(self.p) if s['id']=='overload')['active'])
    def test_direct_synergy_does_not_inflate_dot_and_fractional_income_is_not_lost(self):
        self.p.units=[self.unit(i,dex) for i,dex in enumerate((1,1,92,92),1)];refresh_traits(self.p)
        result=modifiers(self.p,self.p.units[0]);self.assertEqual((result['damage'],result['dot']),(1.08,1))
        self.p.progress['cards']={'income':1};self.assertEqual(sum(kill_reward(self.p,7) for _ in range(10)),77)
    def test_card_damage_is_used_in_actual_combat_and_public_values(self):
        self.r.stage='combat';self.p.units=[self.unit()];self.p.progress['cards']={'fire':1}
        self.r.spawn(self.p);e=self.p.enemies[0];e.update(hp=10000,shield=0,types=[],weakness=None)
        with patch.object(Room,'position',return_value=MAP['cells'][0]),patch.object(Room,'inflict'),patch('defense.random.random',return_value=1):self.r.simulate(self.p,.01,False)
        self.assertAlmostEqual(10000-e['hp'],attack_damage(self.p.units[0])*1.15)
        self.assertAlmostEqual(self.p.public()['units'][0]['attackDamage'],10000-e['hp'],delta=.051)
    def test_flawless_mission_resets_on_loss_and_does_not_count_healing_as_no_loss(self):
        with patch('adventure.random.choice',return_value='flawless'):self.r.start_round()
        self.r.complete_round();self.assertEqual(self.p.progress['mission']['progress'],1)
        self.r.start_round();self.r.leak(self.p,dict(boss=False,raid=False,progress=0));self.p.hp=20
        self.r.complete_round();self.assertEqual(self.p.progress['mission']['progress'],0)
        for _ in range(2):self.r.start_round();self.r.complete_round()
        self.assertEqual(self.p.progress['mission']['status'],'completed')
    def test_combined_environment_and_card_damage_has_a_hard_cap(self):
        from defense import combat_damage,terrain_multiplier
        self.p.units=[self.unit(dex=4,cell=5)];self.p.progress['cards']={'fire':2,'ultimate':2};refresh_traits(self.p)
        u=self.p.units[0];base=attack_damage(u,special=True)/terrain_multiplier(4,5,True)
        self.assertAlmostEqual(combat_damage(self.p,u,True,1.2)/base,1.8)


if __name__=='__main__':unittest.main()

