import unittest
from unittest.mock import patch
from defense import Room,Player,MAP
from rounds import make_plan
from adventure import modifiers,refresh_traits


class CoopAdventureTests(unittest.TestCase):
    def setUp(self):
        class Socket:
            closed=False
            async def send_json(self,d):pass
        self.r=Room('COOP');self.r.phase='playing';self.r.stage='combat';self.r.game_mode='coop';self.r.participants=3;self.r.team_hp=60
        self.p=Player(1,'one',Socket());self.q=Player(2,'two',Socket());self.z=Player(3,'three',Socket());self.r.players={p.slot:p for p in (self.p,self.q,self.z)}
        self.q.units=[dict(id=1,dex=4,cell=0,power=1,cooldown=0,energy=10)]
    def test_support_validates_mode_state_targets_cost_and_cooldown(self):
        before=self.p.gold
        for target in (1,99,True):self.assertIsNotNone(self.r.support_skill(self.p,'attack',target))
        self.q.ws.closed=True;self.assertIsNotNone(self.r.support_skill(self.p,'attack',2));self.q.ws.closed=False
        self.assertEqual(self.p.gold,before)
        self.assertIsNone(self.r.support_skill(self.p,'attack',2));self.assertEqual(self.p.gold,before-80)
        self.assertIsNotNone(self.r.support_skill(self.p,'energy',2));self.assertEqual(self.p.progress['supports'],1)
        refresh_traits(self.q);self.assertAlmostEqual(modifiers(self.q,self.q.units[0])['damage'],1.1)
        self.q.room_seconds=11;self.assertEqual(modifiers(self.q,self.q.units[0])['damage'],1)
        self.r.game_mode='competitive';self.assertIsNotNone(self.r.support_skill(self.z,'attack',2))
    def test_defense_prevents_one_life_loss_once_and_keeps_relay_alive(self):
        self.r.team_hp=1;self.assertIsNone(self.r.support_skill(self.p,'defense',2))
        e=dict(progress=0,direction=1,boss=False,raid=False)
        self.r.leak(self.q,e);self.assertEqual(self.r.team_hp,1);self.assertTrue(all(p.hp>0 for p in self.r.players.values()))
        self.assertEqual(len(self.r.transfers),1)
        self.r.leak(self.q,e);self.assertEqual(self.r.team_hp,0)
    def test_energy_is_bounded_and_receiver_cannot_stack_supports(self):
        self.q.units[0]['energy']=90;self.assertIsNone(self.r.support_skill(self.p,'energy',2))
        self.assertEqual(self.q.units[0]['energy'],100)
        before=self.z.gold;self.assertIsNotNone(self.r.support_skill(self.z,'energy',2));self.assertEqual(self.z.gold,before)
        self.r.participants=1;self.assertIsNotNone(self.r.support_skill(self.z,'attack',2))
    def test_boss_shield_contribution_break_and_enrage(self):
        r=self.r;r.wave=9;r.start_round();boss=r.shared_boss;boss.update(hp=6900,maxHp=10000,shield=0,types=[])
        r.active_plan={**make_plan(10),'weather':'clear'}
        self.p.units=self.q.units;self.q.units=[]
        with patch('defense.attack_damage',return_value=1000),patch('defense.random.random',return_value=1),patch.object(Room,'inflict'):
            r.boss_step(.01)
        self.assertTrue(boss['shieldTriggered']);self.assertEqual(boss['shield'],0)
        self.assertGreater(boss['exposed'],0);self.assertAlmostEqual(self.p.boss_damage,1000)
        self.assertEqual(r.adventure_event['kind'],'break')
        boss['hp']=3000;self.p.units=[];before=r.stage_left;r.boss_step(1)
        self.assertEqual(boss['patternPhase'],3);self.assertAlmostEqual(before-r.stage_left,.15)
    def test_zero_metrics_hide_titles_and_ties_are_deterministic(self):
        self.r.finish();self.assertIsNone(self.r.result['mvpSlot']);self.assertTrue(all(not a for a in self.r.result['awards'].values()))
        self.r.phase='playing'
        for p in (self.p,self.q):p.boss_damage=200;p.kills=10
        self.r.finish();self.assertEqual(self.r.result['mvpSlot'],1)
        for p in (self.p,self.q):self.assertIn('boss',[a['id'] for a in self.r.result['awards'][str(p.slot)]])


if __name__=='__main__':unittest.main()

