from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker
from database.users import reg_user

class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any]
        ],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:

        user = data.get("event_from_user")

        if user is None:
            return await handler(event, data)

        await reg_user(tg_id=user.id, username=user.username)

        return await handler(event, data)