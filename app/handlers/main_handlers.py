from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram import Router, F
from app.keyboards.main_keyboards import start_keyboard
from main import main as url_handler
from google.genai.errors import APIError
from httpx import HTTPStatusError

router = Router()

help_photo = FSInputFile("images/help_photo.png")

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
    "<b>👋 Добро пожаловать в NaAnswer!</b>\n\n"
    "Привет! Я помогу тебе быстро справляться с тестами на платформе <b>naurok🔔</b>.\n\n"
    "🤖 Просто отправь мне ссылку на тест, и я отправлю тебе правильные ответы.\n", reply_markup=start_keyboard)

@router.callback_query(F.data == "how_to_use")
async def how_to_use(callback: CallbackQuery):
    await callback.message.answer_photo(
        photo=help_photo,
        caption=("📖 Как пользоваться ботом:\n\n"
        "1. Начни проходить тест.\n"
        "2. Скопируй ссылку своего прохождения.\n"
        "3. Скинь ссылку мне.\n"
        "4. Дождись результата!")
    )
    await callback.answer()

@router.message(F.text)
async def text_messages(message: Message):
    await message.answer("🕐 Начинаю обработку...")
    try:
        await message.answer(await url_handler(message.text))
    except HTTPStatusError:
        await message.answer("❌ <b>Некорректная ссылка!</b>\n\n"
                            "⚠️ <b>Важно!</b>\n"
                            "Отправляйте ссылку непосредственно во время прохождения теста.")
    except APIError as e:
        if e.code == 503:
            await message.answer("⚠️ Сервера Gemini перегружены, ошибка не на нашей стороне, попробуйте еще раз.")
        else:
            await message.answer(f"⚠️ Error {e}, try again")
    except Exception as e:
        print(f'[BOT] {e}')
        await message.answer(f"⚠️ Unknown Error, try again later")