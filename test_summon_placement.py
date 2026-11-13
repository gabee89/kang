import unittest
from unittest.mock import patch

from defense import Room, Player, CELL_COUNT, MAP


class SummonPlacementTests(unittest.TestCase):
    def setUp(self):
        self.room = Room('STACK')
        self.player = Player(1, 'test', None)
        self.player.gold = 10000

    def summon(self, dex=1):
        with patch('defense.random.choices', side_effect=[['base'], [dex]]):
            return self.room.summon(self.player)

    def test_matching_species_fills_its_moved_cell_before_empty_cells(self):
        self.assertIsNone(self.summon())
        self.player.units[0]['cell'] = 12
        self.assertIsNone(self.summon())
        self.assertIsNone(self.summon())
        self.assertEqual([u['cell'] for u in self.player.units], [12, 12, 12])
        self.assertEqual(self.player.gold, 10000 - 3 * 40)
        self.assertEqual(len({u['id'] for u in self.player.units}), 3)

    def test_full_stack_opens_new_cell_then_fills_that_stack(self):
        for _ in range(5):
            self.assertIsNone(self.summon())
        self.assertEqual([u['cell'] for u in self.player.units], [0, 0, 0, 1, 1])

    def test_different_species_never_mix_and_match_any_existing_stack(self):
        for dex in (1, 4, 1, 7, 4):
            self.assertIsNone(self.summon(dex))
        self.assertEqual([u['cell'] for u in self.player.units], [0, 1, 0, 2, 1])

    def test_full_earlier_stack_does_not_hide_later_available_stack(self):
        for _ in range(4):
            self.summon()
        self.player.units[-1]['cell'] = 12
        self.summon()
        self.assertEqual(self.player.units[-1]['cell'], 12)

    def test_non_evolving_species_keep_two_unit_cap(self):
        for _ in range(3):
            self.assertIsNone(self.summon(131))
        self.assertEqual([u['cell'] for u in self.player.units], [0, 0, 1])

    def test_no_compatible_space_rejects_without_spending_or_adding_unit(self):
        self.player.units = [dict(id=i, dex=4, cell=i) for i in range(CELL_COUNT)]
        before = self.player.gold
        self.assertIsNotNone(self.summon(1))
        self.assertEqual(self.player.gold, before)
        self.assertEqual(len(self.player.units), CELL_COUNT)


class ShortRangeTests(unittest.TestCase):
    def test_basic_and_ultimate_respect_adjacent_and_two_cell_boundaries(self):
        for dex, distances in ((4, ((.99, True), (1.01, False), (1.99, False))),
                               (25, ((.99, True), (2.09, True), (2.11, False)))):
            for energy in (0, 100):
                for distance, hits in distances:
                    with self.subTest(dex=dex, energy=energy, distance=distance):
                        room = Room('RANGE')
                        room.stage = 'combat'
                        player = Player(1, 'test', None)
                        unit = dict(id=100, dex=dex, cell=0, power=1, cooldown=0, energy=energy)
                        player.units = [unit]
                        room.spawn(player)
                        enemy = player.enemies[0]
                        enemy.update(hp=10000, maxHp=10000, shield=0, types=[], weakness=None)
                        x, y = MAP['cells'][0]
                        with patch.object(Room, 'position', return_value=(x + distance, y)), \
                                patch.object(Room, 'inflict'), patch('defense.random.random', return_value=1):
                            room.simulate(player, .01, advance_enemies=False)
                        self.assertEqual(enemy['hp'] < 10000, hits)
                        if energy == 100:
                            self.assertEqual(unit['energy'], 0 if hits else 100)


if __name__ == '__main__':
    unittest.main()

