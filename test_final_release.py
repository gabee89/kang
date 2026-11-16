import unittest
from unittest.mock import patch
from defense import Room, CELL_COUNT
from test_defense import Socket

class FinalReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def room(self,count=1,mode='competitive'):
        room=Room('FINAL')
        for _ in range(count):room.add(None,Socket())
        room.game_mode=mode
        await room.begin()
        return room

    async def test_solo_reaches_boss_through_natural_round_progression(self):
        room=await self.room();p=room.players[1]
        p.units=[dict(id=100+i,dex=150,cell=i,power=1,enhance=10,cooldown=0,energy=0,
                      ivs={'attack':31,'special':31,'speed':31}) for i in range(CELL_COUNT)]
        for _ in range(10000):
            room.advance(.1)
            if room.stage=='boss' or room.phase=='finished':break
        self.assertEqual((room.phase,room.wave,room.stage),('playing',10,'boss'))
        boss=room.shared_boss;before=boss['hp'];timer=room.stage_left;clock=room.seconds
        room.speed=3
        room.advance(5.7)
        self.assertAlmostEqual(room.boss_intro_left,.1)
        self.assertEqual((boss['hp'],room.stage_left,room.seconds),(before,timer,clock))
        room.advance(.31);room.advance(.1)
        self.assertLess(boss['hp'],before)
        self.assertGreater(p.boss_round_damage,0)

    async def test_solo_coop_and_three_players_receive_the_same_entry_pause(self):
        for count,mode in ((1,'coop'),(3,'coop'),(3,'competitive')):
            room=await self.room(count,mode)
            room.wave=9;room.stage_left=.001
            room.advance(.01)
            self.assertEqual((room.wave,room.stage), (10,'boss'))
            self.assertEqual(room.boss_intro_left,2)
            before=room.shared_boss['hp'];room.advance(1)
            self.assertEqual(room.shared_boss['hp'],before)

    async def test_matching_stack_and_latest_progression_are_retained(self):
        room=await self.room();p=room.players[1];p.units=[]
        with patch('defense.random.choices',side_effect=[['base'],[1]]*4):
            for _ in range(4):room.summon(p,True)
        self.assertEqual([u['cell'] for u in p.units],[0,0,0,1])
        self.assertIn('progress',vars(p))

