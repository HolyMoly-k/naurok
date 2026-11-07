from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram import Router, F
from app.keyboards.main_keyboards import start_keyboard, back_keyboard
from main import main as url_handler
from google.genai.errors import APIError
from httpx import HTTPStatusError
from main import MODEL, clean
from json import JSONDecodeError
from database.users import get_balance, INTERVAL_RESET, add_tokens, reset_tokens
from datetime import datetime, timezone

router = Router()

help_photo = FSInputFile("images/help_photo.png")

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
    "<b>👋 Добро пожаловать в NaAnswer!</b>\n\n"
    "Привет! Я помогу тебе быстро справляться с тестами на платформе <b>naurok🔔</b>.\n\n"
    "🤖 Просто отправь мне ссылку на тест, и я отправлю тебе правильные ответы.\n", reply_markup=start_keyboard)

@router.callback_query(F.data == 'back')
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>👋 Добро пожаловать в NaAnswer!</b>\n\n"
        "Привет! Я помогу тебе быстро справляться с тестами на платформе <b>naurok🔔</b>.\n\n"
        "🤖 Просто отправь мне ссылку на тест, и я отправлю тебе правильные ответы.\n",
        reply_markup=start_keyboard
    )
    await callback.answer()

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

def create_balance(tokens, tokens_limit, last_reset) -> str:
    used_percent = (tokens / tokens_limit * 100) if tokens_limit else 0
    remaining = max(0, tokens_limit - tokens)

    reset_at = last_reset + INTERVAL_RESET
    reset_text = reset_at.strftime("%d.%m.%Y в %H:%M")

    progress = 10
    filled = round(used_percent / 100 * progress)
    bar = "🟩" * filled + "⬜" * (progress - filled)

    text = (
        "💳 <b>Ваш баланс</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🪙 <b>Использовано:</b> {tokens:,} токенов\n"
        f"📦 <b>Лимит:</b> {tokens_limit:,} токенов\n"
        f"✨ <b>Осталось:</b> {remaining:,} токенов\n\n"
        f"📊 <b>Использование:</b> {used_percent:.1f}%\n"
        f"{bar}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔄 <b>Следующее обновление:</b>\n"
        f"<code>{reset_text}</code>"
    )
    return text

async def show_balance(event: CallbackQuery | Message):
    user_id = event.from_user.id
    tokens, tokens_limit, last_reset = await get_balance(user_id)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(create_balance(tokens, tokens_limit, last_reset), reply_markup=back_keyboard)
        await event.answer()
    else:
        await event.answer(create_balance(tokens, tokens_limit, last_reset))

router.message.register(show_balance, Command('balance'))
router.callback_query.register(show_balance, F.data == "balance")

def create_message(questions, answers, name, subject, grade, tokens_spent):
    result = f"📋 <b>{name}</b>\n"
    result += f"━━━━━━━━━━━━━━━━━━\n"
    result += f"📚 Предмет: <b>{subject}</b>\n"
    result += f"🎓 Класс: <b>{grade}</b>\n\n"
    result += f"✅ <b>Ответы:</b>\n"

    for num, item in answers.items():
        q = questions[int(num) - 1]
        result += f"\n<b>{num}.</b>\n"
        for letter in item["answer"]:
            idx = ord(letter) - ord('A')
            option = clean(q['options'][idx]['value'])
            result += f"   <b>{letter})</b> {option}\n"

    result += "\n━━━━━━━━━━━━━━━━━━\n"
    result += f"🪙 Потрачено токенов: <b>{tokens_spent:,}</b>\n"
    result += f"🤖 <i>Ответы сгенерированы {MODEL}</i>"

    return result

@router.message(F.text)
async def text_messages(message: Message):
    await message.answer("🕐 Начинаю обработку...")
    tokens, limit, last_reset = await get_balance(message.from_user.id)
    if (tokens >= limit):
        if (datetime.now(timezone.utc) >= last_reset+INTERVAL_RESET):
            await reset_tokens(message.from_user.id)
        else:
            await message.answer("❌ Вы достигли лимита токенов, для просмотра баланса напишите /balance")
            return
    try:
        data = await url_handler(message.text, limit-tokens)
        questions, answers, name, subject, grade, tokens_spent = data["questions"], data["answers"], data["name"], data["subject"], data["grade"], data["tokens_spent"]
        await add_tokens(message.from_user.id, tokens_spent)
        await message.answer(create_message(questions, answers, name, subject, grade, tokens_spent))
    except HTTPStatusError:
        await message.answer("❌ <b>Некорректная ссылка!</b>\n\n"
                            "⚠️ <b>Важно!</b>\n"
                            "Отправляйте ссылку непосредственно во время прохождения теста.")
    except APIError as e:
        if e.code == 503:
            await message.answer("⚠️ Сервера Gemini перегружены, ошибка не на нашей стороне, попробуйте еще раз.")
        else:
            await message.answer(f"⚠️ Error {e}, try again")
    except JSONDecodeError:
        await message.answer("⚠️ ИИ модель вернула кривой json, попробуйте еще раз")
    # except Exception as e:
    #     print(f'[BOT] {e}')
    #     await message.answer(f"⚠️ Unknown Error, try again later")