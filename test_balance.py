import unittest
from defense import Room,Player,DIFFICULTIES
from campaign import PREPARATION
from rounds import make_plan


class BalanceTests(unittest.TestCase):
    def test_preparation_and_starting_budget_support_six_pulls(self):
        self.assertEqual(PREPARATION,10)
        p=Player(1,'test',None)
        self.assertEqual(p.gold//40,6)

    def test_difficulty_order_remains_strict(self):
        self.assertLess(DIFFICULTIES['normal'],DIFFICULTIES['challenge'])
        self.assertLess(DIFFICULTIES['challenge'],DIFFICULTIES['extreme'])

    def test_shorter_shortcut_is_less_durable_in_either_direction(self):
        for direction in (1,-1):
            r=Room('BAL');r.wave=8;plan={**make_plan(8),'direction':direction}
            p=Player(1,'test',None);r.active_plan={**plan,'entry':'main'};r.spawn(p)
            regular=p.enemies[-1]['maxHp']
            r.active_plan={**plan,'entry':'shortcut'};r.spawn(p)
            self.assertLess(p.enemies[-1]['maxHp'],regular)


if __name__=='__main__':unittest.main()

