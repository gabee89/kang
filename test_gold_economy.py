import unittest
from defense import Room,Player


class GoldEconomyTests(unittest.TestCase):
    def test_kill_rewards_and_golden_bonus_are_actually_paid(self):
        for kwargs,reward in (({},7),({'golden':True},47),({'boss':True,'boss_rank':'elite'},40),({'boss':True,'boss_rank':'boss'},90)):
            with self.subTest(kwargs=kwargs):
                r=Room('GOLD');p=Player(1,'test',None);r.spawn(p,**kwargs);p.enemies[0]['hp']=0
                before=p.gold;r.simulate(p,.01)
                self.assertEqual(p.gold-before,reward)

    def test_starting_budget_and_round_income(self):
        r=Room('GOLD');p=Player(1,'test',None);r.players={1:p}
        self.assertEqual(p.gold,240)
        r.start_round()
        self.assertEqual(p.gold,240+63)

    def test_shared_boss_reward_is_paid(self):
        r=Room('GOLD');p=Player(1,'test',None);r.players={1:p};r.participants=1;r.wave=9
        r.start_round();r.shared_boss['hp']=0;before=p.gold;r.boss_step(.01)
        self.assertEqual(p.gold-before,300)


if __name__=='__main__':unittest.main()

