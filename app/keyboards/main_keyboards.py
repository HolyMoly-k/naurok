from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

start_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="ℹ️ Как пользоваться?",
                callback_data="how_to_use"
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 Баланс",
                callback_data='balance'
            )
        ],
    ]
)

back_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data='back'
            )
        ]
    ]
)