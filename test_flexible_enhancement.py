import unittest
from defense import Room, Player


class FlexibleEnhancementTests(unittest.TestCase):
    def setUp(self):
        self.room=Room('MERGE');self.room.phase='playing';self.p=Player(1,'test',None)
    def unit(self,id,level,dex=6,cell=0,power=1):
        return dict(id=id,dex=dex,cell=cell,power=power,enhance=level,energy=0,cooldown=0,xp=id,
                    ivs={'attack':id,'special':id+1,'speed':id+2})
    def test_different_levels_work_in_both_selection_orders(self):
        for a,b,result in ((1,0,2),(2,0,3),(0,2,3),(3,2,4),(9,0,10)):
            with self.subTest(a=a,b=b):
                self.p.units=[self.unit(1,a),self.unit(2,b)]
                self.assertIsNone(self.room.merge_unit(self.p,self.p.units[0]))
                self.assertEqual(len(self.p.units),1)
                self.assertEqual((self.p.units[0]['id'],self.p.units[0]['enhance'],self.p.units[0]['xp']),(1,result,3))
                self.assertEqual(self.p.units[0]['ivs'],{'attack':2,'special':3,'speed':4})
    def test_quick_merge_uses_same_rule_and_prefers_low_level_material(self):
        self.p.units=[self.unit(1,2),self.unit(2,0,cell=1),self.unit(3,5,cell=2)]
        self.assertIsNone(self.room.action(self.p,{'type':'quick_merge'}))
        self.assertEqual([(u['id'],u['enhance']) for u in self.p.units],[(1,3),(3,5)])
    def test_different_species_and_maximum_units_are_not_materials(self):
        self.p.units=[self.unit(1,2),self.unit(2,0,dex=9),self.unit(3,10)]
        before=[dict(u) for u in self.p.units]
        self.assertIsNotNone(self.room.merge_unit(self.p,self.p.units[0]))
        self.assertEqual(self.p.units,before)
    def test_non_evolving_units_accept_different_power_without_losing_it(self):
        self.p.units=[self.unit(1,0,dex=131),self.unit(2,1,dex=131,power=2)]
        self.assertIsNone(self.room.merge_unit(self.p,self.p.units[0]))
        self.assertEqual((self.p.units[0]['enhance'],self.p.units[0]['power']),(2,2))
    def test_pre_evolution_recipe_still_requires_three_matching_units(self):
        self.p.units=[self.unit(1,1,dex=4),self.unit(2,0,dex=4),self.unit(3,0,dex=4)]
        self.assertIsNotNone(self.room.merge_unit(self.p,self.p.units[0]))


if __name__=='__main__':unittest.main()

