import unittest
from unittest.mock import patch
from defense import Room, Player, MAP, CATALOG
from rounds import make_plan, WEATHER
from elements import effectiveness


class RoundEventTests(unittest.IsolatedAsyncioTestCase):
    def test_consecutive_rounds_cannot_repeat_the_same_weather(self):
        previous=make_plan(1)
        for number in range(2,51):
            plan=make_plan(number,previous)
            self.assertNotEqual(plan['weather'],previous['weather'])
            previous=plan

    async def room(self):
        class Socket:
            closed=False
            async def send_json(self, message): pass
        room=Room('EVENT')
        for _ in range(3):room.add(None,Socket())
        await room.begin()
        return room

    async def test_preview_roll_is_used_once_and_shared_by_every_player(self):
        room=await self.room()
        preview=dict(room.next_plan)
        with patch('campaign.make_plan', side_effect=AssertionError('round must use preview')):
            room.start_round()
            for i in range(8):
                room.spawned=i
                for player in room.players.values():
                    room.spawn(player,golden=i==4)
        self.assertEqual(room.active_plan,preview)
        for player in room.players.values():
            self.assertEqual({e['dex'] for e in player.enemies},{preview['dex']})
            self.assertTrue(all(list(e['types'])==preview['types'] for e in player.enemies))
            self.assertEqual(sum(e['golden'] for e in player.enemies),1)
        room.complete_round()
        self.assertEqual(room.next_plan['round'],2)
        self.assertEqual(room.stage,'prep')

    async def test_shortcut_is_announced_before_round_and_used_by_all_spawns(self):
        room=await self.room();room.wave=3;room.next_plan=make_plan(4)
        self.assertEqual(room.next_plan['entry'],'shortcut')
        room.start_round()
        for player in room.players.values():
            room.spawn(player)
            self.assertTrue(player.enemies[-1]['flank'])
            self.assertEqual(room.enemy_position(player.enemies[-1]),room.position(MAP['flankProgress']))
        room.complete_round();room.start_round()
        self.assertEqual(room.active_plan['entry'],'main')

    def test_theme_changes_every_ten_rounds_and_boss_rules_stay_separate(self):
        self.assertEqual([make_plan(n)['theme'] for n in (1,10,11,21,31,41)],
                         ['forest','forest','valley','volcano','snowfield','moonlit'])
        plan=make_plan(20)
        self.assertEqual((plan['dex'],plan['entry']),(149,'main'))

    def test_matchup_preview_combines_actual_dual_types_and_weather(self):
        for kind,(_,_,bonus) in WEATHER.items():
            with patch('rounds.random.choice',side_effect=[74,kind]):plan=make_plan(3)
            for role,multiplier in plan['matchups'].items():
                self.assertAlmostEqual(multiplier,round(effectiveness(role,plan['types'])*bonus.get(role,1),2))
            self.assertEqual(plan['matchups']['electric'],0)

    def test_weather_modifies_actual_hits_and_serialized_damage_together(self):
        damage=[]
        for weather in ('clear','rain','heat'):
            room=Room('WEATHER');room.stage='combat'
            room.active_plan={**make_plan(1),'weather':weather}
            player=Player(1,'test',None)
            player.units=[dict(id=1,dex=4,cell=0,power=1,cooldown=0,energy=0)]
            room.spawn(player);enemy=player.enemies[0]
            enemy.update(hp=10000,shield=0,types=[],weakness=None)
            with patch.object(Room,'position',return_value=MAP['cells'][0]),patch.object(Room,'inflict'),patch('defense.random.random',return_value=1):
                room.simulate(player,.01,advance_enemies=False)
            actual=10000-enemy['hp'];damage.append(actual)
            public=player.public(room.damage_bonuses())['units'][0]
            self.assertAlmostEqual(actual,public['attackDamage'],delta=.051)
        self.assertAlmostEqual(damage[1]/damage[0],.85)
        self.assertAlmostEqual(damage[2]/damage[0],1.2)

    async def test_next_plan_and_weather_are_in_every_snapshot(self):
        room=await self.room();messages=[]
        async def capture(message):messages.append(message)
        room.all=capture
        await room.snapshot()
        self.assertEqual(messages[-1]['roundPlan'],room.next_plan)
        room.start_round();await room.snapshot()
        self.assertEqual(messages[-1]['roundPlan'],room.active_plan)


if __name__=='__main__':unittest.main()

