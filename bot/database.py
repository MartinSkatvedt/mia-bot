import asyncpg

SCHEMA = """
CREATE TABLE IF NOT EXISTS member_activity (
    member_id        BIGINT NOT NULL,
    guild_id         BIGINT NOT NULL,
    last_message_at  TIMESTAMPTZ,
    last_online_at   TIMESTAMPTZ,
    PRIMARY KEY (member_id, guild_id)
);
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


async def init_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
    return pool


async def upsert_last_message(pool: asyncpg.Pool, guild_id: int, member_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(UPSERT_LAST_MESSAGE, member_id, guild_id)


async def upsert_last_online(pool: asyncpg.Pool, guild_id: int, member_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(UPSERT_LAST_ONLINE, member_id, guild_id)


async def get_member_activity(
    pool: asyncpg.Pool, guild_id: int, member_id: int
) -> tuple | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(GET_MEMBER_ACTIVITY, member_id, guild_id)
    if row is None:
        return None
    return (row["last_message_at"], row["last_online_at"])
