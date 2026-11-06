from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="ℹ️ Как пользоваться?",
                callback_data="how_to_use"
            )
        ]
    ]
)