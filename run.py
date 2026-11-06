import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from app.handlers.main_handlers import router as main_router
from app.middleware import RegistrationMiddleware
from database.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)

bot = Bot(token=TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def main():
    try:
        dp.update.outer_middleware(
            RegistrationMiddleware()
        )
        dp.include_router(main_router)
        await dp.start_polling(bot)
    finally:
        await engine.dispose()
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")