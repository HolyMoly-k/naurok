from database.session import SessionFactory
from database.models import User
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert


async def reg_user(tg_id, username, tokens = 0, tokens_limit = 5000, last_reset = datetime.now(timezone.utc)):
    async with SessionFactory() as session:
        await session.execute(
            insert(User).values(tg_id=tg_id, username=username, tokens=tokens, tokens_limit=tokens_limit, last_reset=last_reset)
            .on_conflict_do_update(
                index_elements=[User.tg_id],
                set_= {
                    "username": username
                }
            )
            )
        await session.commit()