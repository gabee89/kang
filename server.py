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
            elif typ == 'difficulty':
                error = room.configure(participant, payload.get('value'))
                if error:
                    await room.send_to(participant, {'type': 'error', 'message': error})
                else:
                    await room.broadcast_room()
            elif typ in ('summon', 'merge', 'move', 'upgrade', 'raid', 'sell', 'speed'):
                error = room.action(participant, payload)
                if error:
                    await room.send_to(participant, {'type': 'error', 'message': error})
            elif typ == 'rematch':
                if room.host == participant.token and room.phase == 'finished' and room.connected():
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
                    idle = now - room.last_active
                    if (room.phase in ('finished', 'lobby') and not room.connected() and idle > 180) or idle > 7200:
                        ROOMS.pop(key, None)
                except Exception:
                    logging.exception('room %s tick failed', key)
    except asyncio.CancelledError:
        pass


async def on_startup(app):
    app[TICKER_KEY] = asyncio.create_task(ticker(app))


async def on_cleanup(app):
    app[TICKER_KEY].cancel()
    await asyncio.gather(app[TICKER_KEY], return_exceptions=True)


async def serve_index(request):
    return web.FileResponse(ROOT / 'index.html')


def create_app():
    app = web.Application(client_max_size=1024 * 64)
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

