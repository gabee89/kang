"""Pokemon luck defense: 1–3 player WebSocket server."""
import asyncio
import json
import logging
import os
import secrets
import time
from pathlib import Path
from aiohttp import web, WSMsgType
from defense import Room, CATALOG
from leaderboard import Leaderboard
RANKING_KEY=web.AppKey('leaderboard',Leaderboard)
RANK_TASKS=web.AppKey('ranking_tasks',set)

ROOT = Path(__file__).resolve().parent
ROOMS = {}
MAX_ROOMS = 60
TICKER_KEY = web.AppKey('ticker', asyncio.Task)

def code():
    while True:
        value = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(5))
        if value not in ROOMS:
            return value

async def api_create(request):
    if len(ROOMS) >= MAX_ROOMS:
        return web.json_response({'error': '게임방이 너무 많습니다. 잠시 후 다시 시도해 주세요.'}, status=429)
    new = Room(code())
    ROOMS[new.code] = new
    return web.json_response({'code': new.code})


async def api_health(request):
    return web.json_response({'ok': True, 'rooms': len(ROOMS)})


async def api_catalog(request):
    return web.json_response(list(CATALOG.values()))


async def api_room_status(request):
    room = ROOMS.get(request.match_info.get('code','').upper())
    if not room:
        return web.json_response({'error': '방을 찾을 수 없습니다.'}, status=404)
    return web.json_response({'code': room.code, 'phase': room.phase,
                              'occupied': [p.slot for p in room.players.values()]})


async def websocket_handler(request):
    room_id = request.query.get('room', '').strip().upper()
    room = ROOMS.get(room_id)
    if room is None:
        return web.json_response({'error': '방이 없거나 종료됐습니다. 방 코드를 확인하세요.'}, status=404)
    ws = web.WebSocketResponse(heartbeat=18, max_msg_size=4096, receive_timeout=70)
    await ws.prepare(request)
    participant = None
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                if msg.type == WSMsgType.ERROR:
                    break
                continue
            try:
                payload = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            typ = payload.get('type')
            if typ == 'join' and participant is None:
                token = payload.get('token')
                token = token if isinstance(token, str) and len(token) < 150 else None
                p, err = room.add(payload.get('slot'), ws, token)
                if err:
                    await ws.send_json({'type': 'error', 'message': err})
                    await ws.close()
                    break
                name=payload.get('name')
                if isinstance(name,str) and room.phase=='lobby':p.name=''.join(c for c in name if c.isprintable()).strip()[:16] or p.name
                participant = p
                await ws.send_json({'type': 'joined', 'code': room.code, 'slot': p.slot,
                                    'token': p.token, 'isHost': room.host == p.token})
                await room.broadcast_room()
                if room.phase in ('playing', 'finished'):
                    await room.snapshot()

                continue
            if participant is None:
                await ws.send_json({'type': 'error', 'message': '먼저 입장해 주세요.'})
                continue
            if typ == 'start':
                if room.host != participant.token:
                    await room.send_to(participant, {'type': 'error', 'message': '방장만 시작할 수 있어요.'})
                elif not await room.begin():
                    await room.send_to(participant, {'type': 'error', 'message': '접속한 참가자가 한 명 이상 필요합니다.'})
            elif typ == 'mode':
                error=room.configure_mode(participant,payload.get('value'))
                if error:await room.send_to(participant,{'type':'error','message':error})
                else:await room.broadcast_room()
            elif typ == 'difficulty':
                error = room.configure(participant, payload.get('value'))
                if error:
                    await room.send_to(participant, {'type': 'error', 'message': error})
                else:
                    await room.broadcast_room()
            elif typ in ('summon', 'merge', 'move', 'upgrade', 'raid', 'sell', 'speed', 'luck','quick_merge','choose_card','support'):
                error = room.action(participant, payload)
                if error:
                    await room.send_to(participant, {'type': 'error', 'message': error})
            elif typ == 'rematch':
                if room.host == participant.token and room.phase == 'finished' and room.connected():
                    if room.participants==1 and not room.ranking_saved and not room.ranking_pending:
                        room.ranking_pending=True
                        task=asyncio.create_task(save_ranking(request.app,room,room.result))
                        request.app[RANK_TASKS].add(task)
                        task.add_done_callback(request.app[RANK_TASKS].discard)
                    room.phase = 'lobby'
                    await room.begin()
                else:
                    await room.send_to(participant, {'type': 'error', 'message': '방장만 재대결을 시작할 수 있어요.'})
            elif typ == 'leave':
                break
    except (ConnectionResetError, asyncio.TimeoutError):
        pass
    finally:
        if participant and participant.ws is ws:
            room.remove(participant)
            await room.broadcast_room()
            if room.phase == 'playing':
                await room.announce('📡 연결이 끊긴 참가자의 방어는 계속됩니다. 30초 안에 재접속할 수 있어요.', 'danger')
        await ws.close()
    return ws


async def save_ranking(app,room,result):
    try:
        await app[RANKING_KEY].record_result(result)
        if room.run_id==result['runId']:room.ranking_saved=True
    except Exception:
        if room.run_id==result['runId']:room.ranking_retry=time.monotonic()+30
        logging.exception('ranking save failed')
    finally:
        room.ranking_pending=False

async def ticker(app):
    last = time.monotonic()
    try:
        while True:
            await asyncio.sleep(.05)
            now = time.monotonic()
            dt = min(.12, now - last)
            last = now
            for key, room in list(ROOMS.items()):
                try:
                    await room.tick(dt)
                    if room.phase=='finished' and room.participants==1 and not room.ranking_saved and not getattr(room,'ranking_pending',False) and now>=getattr(room,'ranking_retry',0):
                        room.ranking_pending=True
                        task=asyncio.create_task(save_ranking(app,room,room.result))
                        app[RANK_TASKS].add(task)
                        task.add_done_callback(app[RANK_TASKS].discard)
                    idle = now - room.last_active
                    if (room.phase in ('finished', 'lobby') and not room.connected() and idle > 180) or idle > 7200:
                        ROOMS.pop(key, None)
                except Exception:
                    logging.exception('room %s tick failed', key)
    except asyncio.CancelledError:
        pass


async def on_startup(app):
    await app[RANKING_KEY].initialize()
    app[TICKER_KEY] = asyncio.create_task(ticker(app))


async def on_cleanup(app):
    app[TICKER_KEY].cancel()
    await asyncio.gather(app[TICKER_KEY], return_exceptions=True)
    await asyncio.gather(*app[RANK_TASKS],return_exceptions=True)


async def serve_index(request):
    return web.FileResponse(ROOT / 'index.html')


async def api_leaderboard(request):
    difficulty=request.query.get('difficulty','challenge')
    if difficulty not in ('normal','challenge','extreme'):
        raise web.HTTPBadRequest()
    store=request.app[RANKING_KEY]
    try:
        rows=await store.top(difficulty)
    except Exception:
        logging.exception('ranking read failed')
        return web.json_response({'error':'랭킹 저장소에 연결하지 못했습니다. 잠시 후 다시 시도하세요.'},status=503)
    return web.json_response({'entries':rows,'durable':store.durable,'difficulty':difficulty})

def create_app():
    app = web.Application(client_max_size=1024 * 64)
    app[RANKING_KEY]=Leaderboard()
    app[RANK_TASKS]=set()
    app.router.add_get('/api/leaderboard',api_leaderboard)
    app.router.add_post('/api/rooms', api_create)
    app.router.add_get('/api/rooms/{code}', api_room_status)
    app.router.add_get('/api/health', api_health)
    app.router.add_get('/api/catalog', api_catalog)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', serve_index)
    app.router.add_static('/assets', ROOT / 'assets', show_index=False)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    web.run_app(create_app(), host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


