"""Server-only ranked results. Optional durable PostgreSQL, explicit local fallback."""
import asyncio
import os
import sqlite3
from contextlib import closing
from pathlib import Path

class Leaderboard:
    def __init__(self,path=None):
        self.url=os.environ.get('DATABASE_URL','')
        self.path=path or os.environ.get('LEADERBOARD_PATH',str(Path(__file__).parent/'leaderboard.sqlite3'))
        self.durable=bool(self.url or os.environ.get('LEADERBOARD_PATH'))
        self.lock=asyncio.Lock()

    async def query(self,sql,params=(),fetch=False):
        if self.url:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.url,connect_timeout=8) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql.replace('?','%s'),params)
                    return await cur.fetchall() if fetch else None
        def run():
            with closing(sqlite3.connect(self.path,timeout=10)) as conn:
                cur=conn.execute(sql,params)
                rows=cur.fetchall() if fetch else None
                conn.commit()
                return rows
        return await asyncio.to_thread(run)

    async def initialize(self):
        await self.query('CREATE TABLE IF NOT EXISTS solo_scores (run_id TEXT PRIMARY KEY, name TEXT NOT NULL, difficulty TEXT NOT NULL, score INTEGER NOT NULL, wave INTEGER NOT NULL, cleared INTEGER NOT NULL, seconds REAL NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

    async def record(self,room):
        if room.participants==1 and room.result:
            await self.record_result(room.result)

    async def record_result(self,result):
        if not result.get('solo'):return
        p=result['scores'][0]
        async with self.lock:
            await self.query('INSERT INTO solo_scores (run_id,name,difficulty,score,wave,cleared,seconds) VALUES (?,?,?,?,?,?,?) ON CONFLICT(run_id) DO NOTHING',
                             (result['runId'],p['name'],result['difficulty'],p['score'],result['wave'],int(result['completed']),result['seconds']))

    async def top(self,difficulty='challenge'):
        rows=await self.query('SELECT name,score,wave,cleared,seconds,created FROM solo_scores WHERE difficulty=? ORDER BY score DESC,seconds ASC,run_id ASC LIMIT 50',(difficulty,),True)
        return [{'name':r[0],'score':r[1],'wave':r[2],'completed':bool(r[3]),'seconds':r[4],'date':r[5]} for r in rows]

