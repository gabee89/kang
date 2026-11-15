import math
import unittest
from unittest.mock import patch

from defense import CATALOG, MAP, Player, Room, combat_damage
from progression import battle_form


class SkillProgressionTests(unittest.TestCase):
    def unit(self, dex=4, enhance=0):
        return dict(id=1, dex=dex, cell=0, power=1, energy=0,
                    cooldown=0, enhance=enhance)

    def test_every_site_has_a_reachable_melee_passage(self):
        for cell in MAP['cells']:
            self.assertLess(min(math.dist(cell, point) for point in MAP['route']),
                            CATALOG[4]['range'])

    def test_all_four_skills_execute_through_combat(self):
        for skill in CATALOG[4]['skills']:
            room = Room('SKILL')
            player = Player(1, 'test', None)
            unit = self.unit()
            unit.update(cooldown=99, skillTimers={'close':99, 'ranged':99})
            if skill['id'] == 'basic':
                unit['cooldown'] = 0
            elif skill['id'] == 'ultimate':
                unit['energy'] = 100
            else:
                unit['skillTimers'][skill['id']] = 0
            player.units = [unit]
            room.spawn(player)
            enemy = player.enemies[0]
            enemy.update(hp=100000, shield=0, types=[], weakness=None)
            with patch.object(Room, 'enemy_position', return_value=MAP['cells'][0]):
                room.simulate(player, .01, False)
            self.assertEqual(player.effects[-1]['skill'], skill['id'])
            self.assertLess(enemy['hp'], 100000)

    def test_form_thresholds_and_damage_apply_to_existing_units(self):
        for dex, threshold, kind in ((6,5,'mega'),(150,3,'mega'),
                                     (144,3,'legendary'),(26,5,'awakened')):
            unit = self.unit(dex, threshold-1)
            self.assertIsNone(battle_form(unit))
            unit['enhance'] = threshold
            self.assertEqual(battle_form(unit)['kind'], kind)
            player = Player(1, 'test', None)
            player.units = [unit]
            self.assertGreater(combat_damage(player, unit), 0)

    def test_displayed_skill_damage_matches_combat(self):
        room = Room('DISPLAY')
        player = Player(1, 'test', None)
        unit = self.unit(6, 5)
        unit.update(cooldown=99, skillTimers={'close':0, 'ranged':99})
        player.units = [unit]
        shown = next(s for s in player.public()['units'][0]['skills'] if s['id']=='close')['damage']
        room.spawn(player)
        player.enemies[0].update(hp=100000, shield=0, types=[], weakness=None)
        with patch.object(Room, 'enemy_position', return_value=MAP['cells'][0]), patch('defense.random.random', return_value=1):
            room.simulate(player, .01, False)
        self.assertAlmostEqual(player.effects[-1]['damage'], shown, delta=.6)

    def test_boss_cannot_skip_phase_from_a_single_attack(self):
        enemy = dict(hp=1000, maxHp=1000, shield=0, bossRank='boss', battleAge=0)
        Room.hurt(enemy, 100000)
        self.assertEqual(enemy['hp'], 700)
        enemy.update(shieldTriggered=True, patternPhase=2)
        Room.hurt(enemy, 100000)
        self.assertEqual(enemy['hp'], 350)
