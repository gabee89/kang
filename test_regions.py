import unittest
from unittest.mock import patch
from defense import (Room, Player, MAP, CELL_COUNT, terrain_multiplier, region_attack_interval,
                     energy_multiplier, critical_chance, attack_damage)
from individuals import attack_interval
from defense import CATALOG


class RegionTests(unittest.TestCase):
    def unit(self,dex=4,cell=0):
        return dict(id=1,dex=dex,cell=cell,power=1,cooldown=0,energy=0)

    def test_all_five_regions_exist_on_both_sides_and_cover_every_slot(self):
        self.assertEqual(len(MAP['terrain']),24)
        self.assertEqual(len(MAP['regions']),5)
        for side in (range(3),range(3,6)):
            kinds={MAP['terrain'][i] for i in range(CELL_COUNT) if i%6 in side}
            self.assertEqual(kinds,{'grass','fire','water','electric','ghost'})

    def test_regions_have_distinct_effects_and_affinities(self):
        self.assertEqual(terrain_multiplier(4,5),1.25)
        self.assertEqual(terrain_multiplier(25,5),1.15)
        for dex,boost in ((1,1.2),(4,1.15)):
            unit=self.unit(dex,0)
            self.assertAlmostEqual(attack_interval(unit,CATALOG)/region_attack_interval(unit),boost)
        self.assertEqual(energy_multiplier(self.unit(4,3)),1.25)
        self.assertEqual(energy_multiplier(self.unit(7,3)),1.4)
        self.assertEqual(terrain_multiplier(4,14,True),1.2)
        self.assertEqual(terrain_multiplier(25,14,True),1.3)
        self.assertEqual(terrain_multiplier(25,14,False),1)
        self.assertEqual(critical_chance(self.unit(4,2)),.20)
        self.assertEqual(critical_chance(self.unit(92,2)),.25)

    def test_lake_actually_charges_faster_and_region_move_updates_public_stats(self):
        room=Room('LAKE');p=Player(1,'test',None)
        unit=self.unit(7,3);p.units=[unit]
        room.simulate(p,1)
        self.assertAlmostEqual(unit['energy'],7*1.4)
        unit['cell']=5
        fire=p.public()['units'][0]
        self.assertEqual(fire['region']['id'],'fire')
        unit['cell']=0
        grass=p.public()['units'][0]
        self.assertLess(grass['attackInterval'],fire['attackInterval'])
        self.assertLess(grass['attackDamage'],fire['attackDamage'])

    def test_ghost_region_crit_is_used_by_server_not_only_displayed(self):
        for cell,critical in ((2,True),(0,False)):
            room=Room('CRIT');p=Player(1,'test',None);room.stage='combat'
            unit=self.unit(4,cell);p.units=[unit];room.spawn(p)
            e=p.enemies[0];e.update(hp=10000,shield=0,types=[],weakness=None)
            with patch.object(Room,'position',return_value=MAP['cells'][cell]),patch.object(Room,'inflict'),patch('defense.random.random',return_value=.18):
                room.simulate(p,.01,advance_enemies=False)
            self.assertAlmostEqual(10000-e['hp'],attack_damage(unit)*(2 if critical else 1))


if __name__=='__main__':unittest.main()

