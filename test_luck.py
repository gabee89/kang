import unittest
from defense import Room, summon_odds, luck_cost, MAP, ROUTE_LENGTH
from test_defense import Socket

class LuckTests(unittest.IsolatedAsyncioTestCase):
    async def test_personal_cost_cap_and_insufficient_funds(self):
        room=Room('LUCK')
        room.add(None,Socket())
        room.add(None,Socket())
        await room.begin()
        p,q=room.players.values()
        original=q.gold
        p.gold=10000
        for level in range(10):
            before=p.gold
            p.last_action=-100
            self.assertIsNone(room.action(p,{'type':'luck','level':999}))
            self.assertEqual(p.luck_level,level+1)
            self.assertEqual(before-p.gold,luck_cost(level))
        p.last_action=-100
        before=p.gold
        self.assertIsNotNone(room.action(p,{'type':'luck'}))
        self.assertEqual(p.gold,before)
        self.assertEqual(q.gold,original)
        self.assertEqual(q.luck_level,0)
        q.gold=99
        q.last_action=-100
        self.assertIsNotNone(room.action(q,{'type':'luck'}))
        self.assertEqual(q.gold,99)
        self.assertEqual(p.public()['summonOdds'],summon_odds(10))

    def test_odds_preserve_evolution_and_improve_rare_pulls(self):
        previous=summon_odds(0)
        self.assertEqual(previous,{'base':96,'middle':3,'final':.7,'legendary':.3})
        for level in range(1,11):
            odds=summon_odds(level)
            self.assertAlmostEqual(sum(odds.values()),100)
            self.assertGreaterEqual(odds['base'],75)
            for key in ('middle','final','legendary'):
                self.assertGreater(odds[key],previous[key])
            previous=odds
        self.assertEqual(summon_odds(999),summon_odds(10))

    def test_route_curvature_and_flank_attachment(self):
        import math
        self.assertGreater(len(MAP['route']),100)
        angles=[]
        for a,b in zip(MAP['route'],MAP['route'][1:]):
            angles.append(math.atan2(b[1]-a[1],b[0]-a[0]))
        # No right-angle corners remain in the combat path.
        self.assertLess(max(abs(math.atan2(math.sin(b-a),math.cos(b-a))) for a,b in zip(angles,angles[1:])),.55)
        self.assertTrue(0<MAP['flankProgress']<ROUTE_LENGTH)
        self.assertLess(min(math.dist(Room.position(MAP['flankProgress']),p) for p in MAP['route']),.15)

