import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from aiohttp.test_utils import TestClient,TestServer
from defense import ROUTE_LENGTH
from server import create_app,ROOMS
import test_campaign as fixtures

class CampaignNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.env=patch.dict('os.environ',{'LEADERBOARD_PATH':str(Path(self.folder.name)/'scores.db'),'DATABASE_URL':''})
        self.env.start()
        self.client=TestClient(TestServer(create_app()));await self.client.start_server()
        self.sockets=[]

    async def asyncTearDown(self):
        for ws in self.sockets:await ws.close()
        await self.client.close();ROOMS.clear();self.env.stop();self.folder.cleanup()

    async def receive(self,ws,kind,predicate=lambda d:True):
        for _ in range(100):
            d=await ws.receive_json(timeout=5)
            if d['type']==kind and predicate(d):return d
        self.fail('missing '+kind)

    async def test_mode_shared_boss_and_relay_are_serialized_to_three_clients(self):
        code=(await (await self.client.post('/api/rooms')).json())['code']
        for i in range(3):
            ws=await self.client.ws_connect('/ws?room='+code);self.sockets.append(ws)
            await ws.send_json({'type':'join','name':'테스터 '+str(i+1)})
            await self.receive(ws,'joined')
        await self.sockets[0].send_json({'type':'mode','value':'coop'})
        await self.receive(self.sockets[0],'room',lambda d:d['gameMode']=='coop')
        await self.sockets[0].send_json({'type':'start'})
        previews=[]
        for ws in self.sockets:
            state=await self.receive(ws,'state')
            self.assertEqual((state['stage'],state['gameMode'],state['teamHp']),('prep','coop',60))
            previews.append(state['roundPlan'])
        self.assertTrue(all(p==previews[0] for p in previews))
        self.assertEqual(previews[0]['round'],1)
        r=ROOMS[code];r.wave=9;r.start_round();r.shared_boss['hp']=r.shared_boss['maxHp']=100000
        for p in r.players.values():p.units=[fixtures.CampaignTests().unit(dex=150)]
        for ws in self.sockets:
            state=await self.receive(ws,'state',lambda d:d['stage']=='boss' and all(p['bossDamage']>0 for p in d['players']))
            self.assertAlmostEqual(100000-state['boss']['hp'],sum(p['bossDamage'] for p in state['players']),delta=3)
        r.stage='combat';r.shared_boss=None;r.wave=11;r.spawned=48;r.round_time=24;r.stage_left=60
        for p in r.players.values():p.units=[];p.enemies=[]
        r.spawn(r.players[3]);enemy=r.players[3].enemies[0];enemy['progress']=ROUTE_LENGTH-.001;id=enemy['id']
        for ws in self.sockets:
            state=await self.receive(ws,'state',lambda d:any(e['id']==id for e in d['players'][0]['enemies']))
            self.assertEqual(state['teamHp'],59)
        await self.sockets[1].send_json({'type':'mode','value':'competitive'})
        self.assertIn('대기실',(await self.receive(self.sockets[1],'error'))['message'])
        response=await self.client.get('/api/leaderboard?difficulty=challenge')
        self.assertEqual(response.status,200)
        self.assertEqual((await response.json())['entries'],[])
        self.assertEqual((await self.client.post('/api/leaderboard',json={'score':999999})).status,405)


