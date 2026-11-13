import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from aiohttp.test_utils import TestClient,TestServer
from server import create_app,ROOMS
from defense import Room


class AdventureNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory();self.env=patch.dict('os.environ',{'LEADERBOARD_PATH':str(Path(self.folder.name)/'scores.db'),'DATABASE_URL':''});self.env.start()
        self.client=TestClient(TestServer(create_app()));await self.client.start_server();self.sockets=[]
    async def asyncTearDown(self):
        for ws in self.sockets:await ws.close()
        await self.client.close();ROOMS.clear();self.env.stop();self.folder.cleanup()
    async def receive(self,ws,predicate):
        for _ in range(150):
            d=await ws.receive_json(timeout=5)
            if predicate(d):return d
        self.fail('expected state missing')
    async def test_choices_reconnect_and_support_are_server_owned(self):
        code=(await(await self.client.post('/api/rooms')).json())['code'];joined=[]
        for _ in range(3):
            ws=await self.client.ws_connect('/ws?room='+code);self.sockets.append(ws);await ws.send_json({'type':'join'});joined.append(await self.receive(ws,lambda d:d['type']=='joined'))
        await self.sockets[0].send_json({'type':'mode','value':'coop'});await self.receive(self.sockets[0],lambda d:d['type']=='room' and d['gameMode']=='coop')
        await self.sockets[0].send_json({'type':'start'});await self.receive(self.sockets[0],lambda d:d['type']=='state')
        r=ROOMS[code];r.start_round();r.wave=5;r.complete_round();await r.snapshot()
        first=await self.receive(self.sockets[0],lambda d:d['type']=='state' and d['players'][0]['adventure']['choices'])
        card=first['players'][0]['adventure']['choices'][0]['id'];await self.sockets[0].send_json({'type':'choose_card','id':card,'coins':999999})
        selected=await self.receive(self.sockets[0],lambda d:d['type']=='state' and not d['players'][0]['adventure']['choices'])
        self.assertEqual(selected['players'][0]['adventure']['cards'][0]['id'],card)
        await self.sockets[0].send_json({'type':'choose_card','id':card});await self.receive(self.sockets[0],lambda d:d['type']=='error')
        await self.sockets[0].close();await asyncio.sleep(.03)
        ws=await self.client.ws_connect('/ws?room='+code);self.sockets.append(ws);await ws.send_json({'type':'join','token':joined[0]['token']});await self.receive(ws,lambda d:d['type']=='joined')
        restored=await self.receive(ws,lambda d:d['type']=='state');self.assertEqual(restored['players'][0]['adventure']['cards'][0]['id'],card)
        r.stage_left=0;r.advance(.01);p=r.players[1];before=p.gold
        await ws.send_json({'type':'support','skill':'attack','target':2,'cost':0})
        support=await self.receive(ws,lambda d:d['type']=='state' and d['players'][1]['adventure']['support']['attackLeft']>0)
        self.assertEqual(support['players'][0]['gold'],before-80)
        await ws.send_json({'type':'support','skill':'attack','target':2});await self.receive(ws,lambda d:d['type']=='error')


class AdventureCampaignTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_fifty_rounds_choices_and_results_for_one_to_three_in_both_modes(self):
        class Socket:
            closed=False
            async def send_json(self,d):pass
        for count in (1,2,3):
            for mode in ('competitive','coop'):
                with self.subTest(count=count,mode=mode):
                    r=Room('FIFTY');r.game_mode=mode
                    for _ in range(count):r.add(None,Socket())
                    await r.begin()
                    for number in range(1,51):
                        r.start_round();self.assertEqual(r.wave,number)
                        if r.stage=='boss':r.shared_boss['hp']=0;r.boss_step(.01)
                        else:r.complete_round()
                    self.assertEqual(r.phase,'finished');self.assertTrue(r.result['completed']);self.assertEqual(len(r.result['scores']),count)
                    self.assertTrue(all(sum(p.progress['cards'].values())==5 for p in r.players.values()))
                    self.assertIsNotNone(r.result['mvpSlot'])
                    r.phase='lobby';await r.begin()
                    self.assertTrue(all(not p.progress['cards'] and p.progress['supports']==0 and p.progress['mission'] is None for p in r.players.values()))


if __name__=='__main__':unittest.main()

