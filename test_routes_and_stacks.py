import unittest
from unittest.mock import patch
from defense import Room, Player, MAP, ROUTE_LENGTH, CATALOG
from rounds import make_plan


class StackMovementTests(unittest.TestCase):
    def setUp(self):
        self.room=Room('MOVE');self.room.phase='playing'
        self.p=Player(1,'test',None)

    def unit(self,id,dex,cell):return dict(id=id,dex=dex,cell=cell,power=1,cooldown=0)

    def move(self,id,cell):
        self.p.last_action=-100
        return self.room.action(self.p,dict(type='move',id=id,cell=cell))

    def test_any_member_moves_the_entire_stack(self):
        self.p.units=[self.unit(i,4,0) for i in (1,2,3)]
        self.assertIsNone(self.move(2,5))
        self.assertEqual([u['cell'] for u in self.p.units],[5,5,5])

    def test_combined_stacks_remain_a_single_moving_group(self):
        self.p.units=[self.unit(1,4,0),self.unit(2,4,0),self.unit(3,4,5)]
        self.assertIsNone(self.move(2,5))
        self.assertIsNone(self.move(3,9))
        self.assertEqual([u['cell'] for u in self.p.units],[9,9,9])

    def test_over_capacity_rejects_atomically_without_splitting(self):
        self.p.units=[self.unit(i,4,0) for i in (1,2,3)]+[self.unit(4,4,5)]
        before=[dict(u) for u in self.p.units]
        self.assertIsNotNone(self.move(2,5))
        self.assertEqual(self.p.units,before)

    def test_different_species_swap_whole_stacks(self):
        self.p.units=[self.unit(i,4,0) for i in (1,2,3)]+[self.unit(i,7,5) for i in (4,5)]
        self.assertIsNone(self.move(2,5))
        self.assertEqual([u['cell'] for u in self.p.units],[5,5,5,0,0])


class DirectionTests(unittest.TestCase):
    def test_round_roll_can_choose_both_directions(self):
        for bit,direction in ((0,1),(1,-1)):
            with patch('rounds.random.getrandbits',return_value=bit):
                self.assertEqual(make_plan(1)['direction'],direction)

    def test_both_directions_follow_same_background_route_in_reverse(self):
        r=Room('PATH')
        for progress in (0,ROUTE_LENGTH*.3,ROUTE_LENGTH):
            self.assertEqual(r.enemy_position(dict(progress=progress,direction=-1)),r.position(ROUTE_LENGTH-progress))
            self.assertEqual(r.enemy_position(dict(progress=progress,direction=1)),r.position(progress))

    def test_reverse_shortcut_starts_at_visible_shortcut_and_moves_toward_other_exit(self):
        r=Room('PATH');r.wave=4;r.active_plan={**make_plan(4),'direction':-1}
        p=Player(1,'test',None);r.spawn(p)
        enemy=p.enemies[0]
        self.assertEqual(enemy['direction'],-1)
        self.assertAlmostEqual(enemy['progress'],ROUTE_LENGTH-MAP['flankProgress'])
        self.assertEqual(r.enemy_position(enemy),r.position(MAP['flankProgress']))
        enemy['progress']+=.5
        for actual,expected in zip(r.enemy_position(enemy),r.position(MAP['flankProgress']-.5)):
            self.assertAlmostEqual(actual,expected)

    def test_reverse_targets_use_real_world_position_and_effect_endpoint(self):
        r=Room('PATH');r.stage='combat';r.wave=1;r.active_plan={**make_plan(1),'direction':-1,'weather':'clear'}
        p=Player(1,'test',None)
        p.units=[dict(id=1,dex=4,cell=0,power=1,cooldown=0,energy=0)]
        r.spawn(p);e=p.enemies[0];e.update(hp=10000,types=[],weakness=None,shield=0)
        with patch.object(Room,'position',return_value=MAP['cells'][0]),patch.object(Room,'inflict'),patch('defense.random.random',return_value=1):
            r.simulate(p,.01,advance_enemies=False)
        self.assertLess(e['hp'],10000)
        self.assertAlmostEqual(p.effects[-1]['targets'][0],ROUTE_LENGTH-e['progress'])


if __name__=='__main__':unittest.main()

