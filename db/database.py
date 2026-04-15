import asyncpg
from config import DATABASE_URL

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                keyword TEXT NOT NULL,
                price_min INTEGER DEFAULT 0,
                price_max INTEGER DEFAULT 999999,
                location TEXT DEFAULT '',
                radius INTEGER DEFAULT 50,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                search_id INTEGER REFERENCES searches(id) ON DELETE CASCADE,
                external_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT,
                price INTEGER,
                url TEXT,
                image_url TEXT,
                location TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(external_id, platform)
            );
        ''')

async def get_pool():
    return pool
