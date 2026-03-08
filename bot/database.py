import asyncio

import asyncpg
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS member_activity (
    member_id        BIGINT NOT NULL,
    guild_id         BIGINT NOT NULL,
    last_message_at  TIMESTAMPTZ,
    last_online_at   TIMESTAMPTZ,
    PRIMARY KEY (member_id, guild_id)
);

CREATE TABLE IF NOT EXISTS mia_sessions (
    id         BIGSERIAL PRIMARY KEY,
    member_id  BIGINT NOT NULL,
    guild_id   BIGINT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at   TIMESTAMPTZ NOT NULL,
    duration   INTERVAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_member_activity_guild_id ON member_activity (guild_id);
CREATE INDEX IF NOT EXISTS idx_mia_sessions_guild_id ON mia_sessions (guild_id);
"""

UPSERT_LAST_MESSAGE = """
INSERT INTO member_activity (member_id, guild_id, last_message_at)
VALUES ($1, $2, NOW())
ON CONFLICT (member_id, guild_id) DO UPDATE
    SET last_message_at = NOW();
"""

UPSERT_LAST_ONLINE = """
INSERT INTO member_activity (member_id, guild_id, last_online_at)
VALUES ($1, $2, NOW())
ON CONFLICT (member_id, guild_id) DO UPDATE
    SET last_online_at = NOW();
"""

GET_MEMBER_ACTIVITY = """
SELECT last_message_at, last_online_at
FROM member_activity
WHERE member_id = $1 AND guild_id = $2;
"""

INSERT_MIA_SESSION = """
    INSERT INTO mia_sessions (member_id, guild_id, started_at, ended_at, duration)
    VALUES ($1, $2, $3, $4, $4 - $3);
"""

GET_TOP_MIA_SESSIONS = """
    SELECT member_id, started_at, ended_at, duration
    FROM (
        SELECT member_id, started_at, ended_at, duration
        FROM mia_sessions
        WHERE guild_id = $1

        UNION ALL

        SELECT member_id, last_message_at AS started_at,
               NULL::TIMESTAMPTZ AS ended_at,
               NOW() - last_message_at AS duration
        FROM member_activity
        WHERE guild_id = $1
          AND last_message_at IS NOT NULL
    ) combined
    ORDER BY duration DESC
    LIMIT $2;
"""


async def init_pool(dsn: str) -> asyncpg.Pool:
    for attempt in range(5):
        try:
            pool = await asyncpg.create_pool(dsn)
            async with pool.acquire() as conn:
                await conn.execute(SCHEMA)
            return pool
        except (OSError, asyncpg.PostgresError):
            if attempt == 4:
                raise
            await asyncio.sleep(2)


async def upsert_last_message(pool: asyncpg.Pool, guild_id: int, member_id: int) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT last_message_at FROM member_activity WHERE guild_id=$1 AND member_id=$2",
                guild_id, member_id,
            )
            now = datetime.now(timezone.utc)
            if row and row["last_message_at"]:
                await conn.execute(INSERT_MIA_SESSION, member_id, guild_id, row["last_message_at"], now)
            await conn.execute(UPSERT_LAST_MESSAGE, member_id, guild_id)


async def upsert_last_online(pool: asyncpg.Pool, guild_id: int, member_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(UPSERT_LAST_ONLINE, member_id, guild_id)


async def get_top_mia_sessions(pool: asyncpg.Pool, guild_id: int, limit: int):
    async with pool.acquire() as conn:
        return await conn.fetch(GET_TOP_MIA_SESSIONS, guild_id, limit)


async def get_member_activity(
    pool: asyncpg.Pool, guild_id: int, member_id: int
) -> tuple | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(GET_MEMBER_ACTIVITY, member_id, guild_id)
    if row is None:
        return None
    return (row["last_message_at"], row["last_online_at"])
