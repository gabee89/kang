import json
import time
import unittest
from aiohttp.test_utils import TestClient, TestServer
from defense import Room
from server import create_app, ROOMS


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
        self.assertEqual((p.gold, q.gold), (120, 160))
        p.gold = 0
        self.assertIsNotNone(self.action(r, p, type='summon'))
        p.gold = 10000
        while len(p.units) < 12:
            self.action(r, p, type='summon')
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
        self.assertIsNotNone(self.action(r, p, type='move', id=100, cell=12))
        self.assertIsNone(self.action(r, p, type='move', id=100, cell=11))
        self.assertEqual(p.units[0]['cell'], 11)

    async def test_raid_cost_cooldown_and_targets(self):
        r = await self.room(3)
        p, q, z = r.players.values()
        self.assertIsNone(self.action(r, p, type='raid'))
        self.assertEqual(p.gold, 80)
        self.assertEqual(len(p.enemies), 0)
        self.assertEqual([len(v.enemies) for v in (q, z)], [1, 1])
        self.assertIsNotNone(self.action(r, p, type='raid'))
        self.assertEqual(p.gold, 80)

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
        p.enemies[0]['progress'] = 31.99
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
        for path in ('/', '/assets/client.js', '/assets/style.css', '/api/catalog', '/api/health'):
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
        await sockets[0].close()
        reconnect = await self.client.ws_connect('/ws?room=' + code)
        await reconnect.send_json({'type': 'join', 'token': joined[0]['token']})
        self.assertEqual((await self.receive(reconnect, 'joined'))['slot'], joined[0]['slot'])
        self.assertEqual((await self.receive(reconnect, 'state'))['phase'], 'playing')
        for ws in sockets[1:] + [reconnect]:
            await ws.close()


if __name__ == '__main__':
    unittest.main()

