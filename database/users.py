from database.session import SessionFactory
from database.models import User
from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update

INTERVAL_RESET = timedelta(hours=6)

async def reg_user(tg_id, username, tokens = 0, tokens_limit = 5000):
    async with SessionFactory() as session:
        await session.execute(
            insert(User).values(tg_id=tg_id, username=username, tokens=tokens, tokens_limit=tokens_limit, last_reset=datetime.now(timezone.utc))
            .on_conflict_do_update(
                index_elements=[User.tg_id],
                set_= {
                    "username": username
                }
            )
            )
        await session.commit()

async def reset_tokens(tg_id):
    async with SessionFactory() as session:
        res = await session.execute(update(User).where(User.tg_id == tg_id).values(tokens=0, last_reset=datetime.now(timezone.utc)))
        if res.rowcount == 0:
            return False
        await session.commit()
    return True

async def get_balance(tg_id):
    async with SessionFactory() as session:
        result = await session.execute(select(User.tokens, User.tokens_limit, User.last_reset).where(User.tg_id == tg_id))
        tokens, tokens_limit, last_reset = result.one()
        if datetime.now(timezone.utc) >= last_reset+INTERVAL_RESET:
            await reset_tokens(tg_id)
            return 0, tokens_limit, datetime.now(timezone.utc)
        return tokens, tokens_limit, last_reset

async def add_tokens(tg_id, tokens):
    async with SessionFactory() as session:
        await session.execute(update(User).where(User.tg_id == tg_id).values(tokens=User.tokens+tokens))
        await session.commit()