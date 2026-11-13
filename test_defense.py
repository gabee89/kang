import json
import time
import unittest
import math
from unittest.mock import patch
from aiohttp.test_utils import TestClient, TestServer
from defense import Room, ROUTE_LENGTH, terrain_multiplier, MAP, CATALOG, MAX_UNITS, WAVE_LENGTH, CELL_COUNT
from server import create_app, ROOMS


def near(cell):
    return min((i/40 for i in range(int(ROUTE_LENGTH*40))),key=lambda t:math.dist(MAP['cells'][cell],Room.position(t)))

class Socket:
    closed = False
    async def send_json(self, data):
        pass


class RulesTests(unittest.IsolatedAsyncioTestCase):
    async def room(self, count):
        r = Room('TEST1')
        for _ in range(count):
            r.add(None, Socket())
        self.assertTrue(await r.begin())
        r.stage='combat'
        r.stage_left=90
        r.wave=1
        return r

    def action(self, r, p, **data):
        p.last_action = -100
        return r.action(p, data)

    async def test_one_two_three_can_start(self):
        for count in (1, 2, 3):
            r = await self.room(count)
            await r.tick(.05)
            self.assertEqual(r.phase, 'playing')
            self.assertEqual(r.participants, count)
            self.assertTrue(all(len(p.units) == 2 for p in r.players.values()))

    async def test_summon_spends_only_own_coins_and_enforces_capacity(self):
        r = await self.room(3)
        p, q, _ = r.players.values()
        self.assertIsNone(self.action(r, p, type='summon'))
        self.assertEqual((p.gold, q.gold), (160, 200))
        p.gold = 0
        self.assertIsNotNone(self.action(r, p, type='summon'))
        p.gold = 10000
        p.units=[{'id':100+i,'dex':1,'cell':i%CELL_COUNT,'power':1,'cooldown':0} for i in range(MAX_UNITS)]
        gold = p.gold
        self.assertIsNotNone(self.action(r, p, type='summon'))
        self.assertEqual(p.gold, gold)

    async def test_merge_evolves_and_move_validates(self):
        r = await self.room(1)
        p = r.players[1]
        p.units = [{'id': i + 100, 'dex': 1, 'cell': i, 'power': 1, 'cooldown': 0} for i in range(3)]
        self.assertIsNone(self.action(r, p, type='merge', id=100))
        self.assertEqual((len(p.units), p.units[0]['dex']), (1, 2))
        self.assertIsNotNone(self.action(r, p, type='move', id=100, cell=True))
        self.assertIsNotNone(self.action(r, p, type='move', id=100, cell=MAX_UNITS))
        self.assertIsNone(self.action(r, p, type='move', id=100, cell=11))
        self.assertEqual(p.units[0]['cell'], 11)

    async def test_raid_cost_cooldown_and_targets(self):
        r = await self.room(3)
        p, q, z = r.players.values()
        self.assertIsNone(self.action(r, p, type='raid'))
        self.assertEqual(p.gold, 120)
        self.assertEqual(len(p.enemies), 0)
        self.assertEqual([len(v.enemies) for v in (q, z)], [1, 1])
        self.assertIsNotNone(self.action(r, p, type='raid'))
        self.assertEqual(p.gold, 120)

    async def test_disconnect_does_not_pause_and_allows_secure_rejoin(self):
        r = await self.room(3)
        p = r.players[1]
        r.remove(p)
        await r.tick(.1)
        self.assertGreater(r.seconds, 0)
        self.assertIsNone(r.add(None, Socket(), 'fake-token')[0])
        same, err = r.add(None, Socket(), p.token)
        self.assertIs(same, p)
        self.assertIsNone(err)
        self.assertIsNone(r.add(None, Socket(), p.token)[0])

    async def test_disconnected_player_forfeits_and_host_transfers(self):
        r = await self.room(2)
        p, q = r.players.values()
        r.remove(p)
        p.last_seen -= 31
        self.assertEqual(r.host, q.token)
        await r.tick(.1)
        self.assertEqual(r.phase, 'finished')
        self.assertEqual(r.winner, q.slot)

    async def test_solo_finishes_only_after_death_and_tie_is_draw(self):
        r = await self.room(1)
        await r.tick(.1)
        self.assertEqual(r.phase, 'playing')
        p = r.players[1]
        p.hp, p.eliminated_at = 0, r.seconds
        await r.tick(.1)
        self.assertTrue(r.result['solo'])
        self.assertIsNone(r.winner)
        r = await self.room(2)
        for p in r.players.values():
            p.hp, p.eliminated_at = 0, 10
        await r.tick(.1)
        self.assertIsNone(r.winner)

    async def test_leak_elimination_and_no_actions_after_death(self):
        r = await self.room(1)
        p = r.players[1]
        p.units = []
        p.hp = 1
        r.spawn(p)
        p.enemies[0]['progress'] = ROUTE_LENGTH - .01
        await r.tick(.1)
        self.assertEqual(p.hp, 0)
        self.assertEqual(r.phase, 'finished')
        self.assertIsNotNone(self.action(r, p, type='summon'))

    async def test_simulation_eventually_ends_without_actions(self):
        r = await self.room(3)
        for _ in range(20000):
            await r.tick(.1)
            if r.phase == 'finished':
                break
        self.assertEqual(r.phase, 'finished')
        self.assertTrue(all(p.gold >= 0 for p in r.players.values()))

    async def test_shared_winding_route_and_endpoint(self):
        self.assertEqual(Room.position(0), (10, 6))
        self.assertEqual(Room.position(ROUTE_LENGTH), (0, 0))
        self.assertEqual(Room.position(ROUTE_LENGTH + 10), (0, 0))
        for x, y in MAP['cells']:
            self.assertTrue(all(math.dist((x, y), Room.position(t / 10)) > .55
                                for t in range(int(ROUTE_LENGTH * 10))))

    async def test_fire_region_damage_and_affinity(self):
        self.assertEqual(terrain_multiplier(4, 5), 1.25)
        self.assertEqual(terrain_multiplier(1, 5), 1.15)
        self.assertEqual(terrain_multiplier(4, 0), 1)
        r = await self.room(1)
        p = r.players[1]
        hits = []
        for cell in (5, 3):
            p.units = [{'id': 1, 'dex': 4, 'cell': cell, 'power': 1, 'cooldown': 0}]
            p.enemies = []
            r.spawn(p)
            e = p.enemies[0]
            e['progress'] = near(cell)
            e['types']=[]
            before = e['hp']
            with patch('defense.random.random', return_value=1), patch.object(Room,'inflict'):
                r.simulate(p, .01)
            hits.append(before - e['hp'])
        self.assertAlmostEqual(hits[0] / hits[1], 1.25)

    async def test_path_zones_change_enemy_speed(self):
        r = await self.room(1)
        p = r.players[1]
        p.units = []
        distances = []
        for start in (2, *[(z['start']+z['end'])/2 for z in MAP['zones']]):
            p.enemies = []
            r.spawn(p)
            e = p.enemies[0]
            e['progress'] = start
            r.simulate(p, .1)
            distances.append(e['progress'] - start)
        self.assertAlmostEqual(distances[1] / distances[0], .65)
        self.assertAlmostEqual(distances[2] / distances[0], 1.35)

    async def test_golden_enemy_reward_and_fair_spawn(self):
        r = await self.room(3)
        r.wave=2
        r.start_round()
        r.round_time=4*.54
        await r.tick(.01)
        for p in r.players.values():
            self.assertEqual(sum(bool(e.get('golden')) for e in p.enemies), 1)
        p = r.players[1]
        p.units = []
        p.enemies = [e for e in p.enemies if e.get('golden')]
        p.enemies[0]['hp'] = 0
        before = p.gold
        r.simulate(p, .1)
        self.assertEqual(p.gold - before, 30)

    async def test_melee_range_and_damage_vs_ranged(self):
        r = await self.room(1)
        p = r.players[1]
        damage = []
        # Same-tier Charmeleon and Ivysaur, same neutral tile and target.
        for dex in (5, 2):
            p.units = [{'id': 100, 'dex': dex, 'cell': 3, 'power': 1, 'cooldown': 0}]
            p.enemies = []
            r.spawn(p)
            e = p.enemies[0]
            e['hp'] = e['maxHp'] = 1000
            e['progress'] = near(p.units[0]['cell'])
            e['types']=[]
            with patch('defense.random.random', return_value=1), patch.object(Room, 'inflict'):
                r.simulate(p, .01)
            damage.append(1000 - e['hp'])
        self.assertAlmostEqual(damage[0] / damage[1], 1.9*CATALOG[5]['movePower']/CATALOG[2]['movePower'])
        self.assertLess(CATALOG[5]['range'], CATALOG[2]['range'])
        for dex in (5, 2):
            p.units = [{'id': 100, 'dex': dex, 'cell': 3, 'power': 1, 'cooldown': 0}]
            p.enemies = []
            r.spawn(p)
            e = p.enemies[0]
            e['hp'] = 1000
            e['progress'] = next(i/40 for i in range(int(ROUTE_LENGTH*40)) if 1.25<math.dist(MAP['cells'][3],Room.position(i/40))<1.75)
            e['types']=[]
            r.simulate(p, .01)
            self.assertEqual(e['hp'] < 1000, dex == 2)

    async def test_full_gauge_waits_for_target_then_casts_once(self):
        r = await self.room(1)
        p = r.players[1]
        u = {'id': 100, 'dex': 25, 'cell': 0, 'power': 1, 'cooldown': 0, 'energy': 100}
        p.units, p.enemies = [u], []
        r.simulate(p, .1)
        self.assertEqual(u['energy'], 100)
        r.spawn(p)
        e = p.enemies[0]
        e['hp'] = e['maxHp'] = 10000
        e['progress']=near(0)
        e['types']=[]
        r.simulate(p, .1)
        self.assertEqual(u['energy'], 0)
        casts = [f for f in p.effects if f['kind'] == 'ultimate']
        self.assertEqual(len(casts), 1)
        self.assertEqual(casts[0]['move'], '10만볼트')
        self.assertGreater(10000 - e['hp'], 18.4 * 3)
        r.simulate(p, .1)
        self.assertEqual(len([f for f in p.effects if f['kind'] == 'ultimate']), 1)

    async def test_gauge_charges_and_events_survive_snapshot_gap(self):
        r = await self.room(1)
        p = r.players[1]
        p.units = [{'id': 100, 'dex': 1, 'cell': 0, 'power': 1, 'cooldown': 0, 'energy': 0}]
        r.spawn(p)
        p.enemies[0]['hp'] = 10000
        p.enemies[0]['progress']=near(0)
        p.enemies[0]['types']=[]
        r.simulate(p, .05)
        self.assertGreater(p.units[0]['energy'], 18)
        event = p.effects[0]
        self.assertEqual(event['kind'], 'attack')
        r.seconds += .1
        r.simulate(p, .05)
        self.assertIn(event['id'], [f['id'] for f in p.public()['effects']])
        r.seconds += 2
        p.enemies = []
        r.simulate(p, .05)
        self.assertNotIn(event['id'], [f['id'] for f in p.effects])

    async def test_short_ranges_require_roadside_melee_placement(self):
        nearest = lambda cell: min(math.dist(MAP['cells'][cell], Room.position(t / 40))
                                   for t in range(int(ROUTE_LENGTH * 40)))
        self.assertLess(nearest(0), CATALOG[4]['range'])
        self.assertGreater(nearest(13), CATALOG[4]['range'])
        self.assertLess(nearest(13), CATALOG[25]['range'])

    async def test_swap_and_merge_evolution_preserve_unique_cells(self):
        r = await self.room(1)
        p = r.players[1]
        p.units = [{'id': i + 100, 'dex': 1, 'cell': i, 'power': 1, 'cooldown': 0, 'energy': 90} for i in range(3)]
        self.assertIsNone(self.action(r, p, type='move', id=100, cell=1))
        self.assertEqual([u['cell'] for u in p.units], [1, 1, 2])
        self.assertIsNone(self.action(r, p, type='merge', id=100))
        u = p.units[0]
        self.assertEqual((len(p.units), u['dex'], u['cell'], u['energy']), (1, 2, 1, 0))
        self.assertEqual(CATALOG[u['dex']]['mode'], 'ranged')
        self.assertEqual(p.effects[-1]['kind'], 'evolve')
        self.assertEqual(p.effects[-1]['move'], '이상해풀')


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        ROOMS.clear()

    async def receive(self, ws, kind):
        for _ in range(100):
            msg = await ws.receive_json(timeout=3)
            if msg['type'] == kind:
                return msg
        self.fail('missing ' + kind)

    async def test_http_and_three_independent_websockets(self):
        for path in ('/', '/assets/client.js', '/assets/battlefield.js', '/assets/combat-fx.js', '/assets/map.json', '/assets/style.css', '/api/catalog', '/api/health'):
            self.assertEqual((await self.client.get(path)).status, 200)
        response = await self.client.post('/api/rooms')
        code = (await response.json())['code']
        sockets, joined = [], []
        for _ in range(3):
            ws = await self.client.ws_connect('/ws?room=' + code)
            await ws.send_json({'type': 'join'})
            joined.append(await self.receive(ws, 'joined'))
            sockets.append(ws)
        await sockets[1].send_json({'type': 'start'})
        self.assertEqual((await self.receive(sockets[1], 'error'))['message'], '방장만 시작할 수 있어요.')
        await sockets[0].send_str('[]')
        await sockets[0].send_json({'type': 'start'})
        for ws in sockets:
            d = await self.receive(ws, 'state')
            self.assertEqual(d['phase'], 'playing')
            self.assertEqual(len(d['players']), 3)
        # Another socket cannot move the first player's unit, and cannot forge energy.
        room = ROOMS[code]
        first = room.players[1]
        original = first.units[0]['cell']
        await sockets[1].send_json({'type': 'move', 'id': first.units[0]['id'], 'cell': 11, 'energy':100})
        self.assertEqual((await self.receive(sockets[1], 'error'))['message'], '포켓몬을 선택해 주세요.')
        self.assertEqual(first.units[0]['cell'], original)
        self.assertLess(first.units[0]['energy'], 100)
        # A cast is serialized into the shared snapshot for all three clients.
        first.units[0]['energy'] = 100
        room.spawn(first)
        first.enemies[-1]['hp'] = 10000
        first.enemies[-1]['progress']=near(first.units[0]['cell'])
        room.stage='combat'
        room.stage_left=90
        await room.tick(.05)
        for ws in sockets:
            for _ in range(30):
                snapshot = await self.receive(ws, 'state')
                if any(e['kind'] == 'ultimate' for p in snapshot['players'] for e in p['effects']):
                    break
            else:
                self.fail('ultimate was not synchronized')
        await sockets[0].close()
        reconnect = await self.client.ws_connect('/ws?room=' + code)
        await reconnect.send_json({'type': 'join', 'token': joined[0]['token']})
        self.assertEqual((await self.receive(reconnect, 'joined'))['slot'], joined[0]['slot'])
        self.assertEqual((await self.receive(reconnect, 'state'))['phase'], 'playing')
        for ws in sockets[1:] + [reconnect]:
            await ws.close()


if __name__ == '__main__':
    unittest.main()


