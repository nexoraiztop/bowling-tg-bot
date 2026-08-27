"""
Telegram бот: слот-машина 🎰 с джекпотом 777 и мини-игрой в боулинг.
Пользователь выбивает 777 на реальной слот-машине Telegram, затем играет в боулинг.
"""

import asyncio
import logging
import os
import random
import uuid
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Dice,
)
from aiogram.filters import Command

from database import SessionLocal, User, GameSession

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Сохраняем активные игры
active_games = {}

# Pin ranges для разных уровней
PIN_RANGES_2_BUTTONS = {
    0: (0, 3),
    1: (3, 6),
}

PIN_RANGES_3_BUTTONS = {
    0: (0, 2),
    1: (2, 4),
    2: (4, 6),
}

PRIZE_LEVELS = [15, 40, 75, 100, "NFT"]

# Значение dice для 777 на слот-машине
JACKPOT_VALUE = 64


def get_pin_ranges(prize_level):
    """Get pin ranges based on prize level"""
    if prize_level >= 2:  # 75, 100, NFT - 3 кнопки
        return PIN_RANGES_3_BUTTONS
    else:  # 15, 40 - 2 кнопки
        return PIN_RANGES_2_BUTTONS


def mention(user_id: int, name: str) -> str:
    """HTML-ссылка на пользователя"""
    return f'<a href="tg://user?id={user_id}">{name}</a>'


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Start command"""
    db = SessionLocal()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id, username=username, current_prize="15", prize_level=0)
        db.add(user)
        db.commit()
    
    welcome_text = (
        f"🎰 Добро пожаловать в Bowling Slot Bot!\n\n"
        f"Правила игры:\n"
        f"1️⃣ Отправьте эмодзи 🎰 боту\n"
        f"2️⃣ Если выбьете 777 - запускается мини-игра в боулинг!\n"
        f"3️⃣ Выберите диапазон кедлей и попробуйте угадать\n"
        f"4️⃣ Если попадете - приз повышается, если нет - приз сгорает!\n\n"
        f"💰 Призы: 15 → 40 → 75 → 100 → NFT\n\n"
        f"Ваш текущий приз: <b>{user.current_prize}</b>\n\n"
        f"👉 Отправьте /spin или просто 🎰 чтобы крутить слот!"
    )
    
    await message.reply(welcome_text)
    db.close()


@dp.message(Command("spin"))
async def cmd_spin(message: Message):
    """Send dice emoji to spin slots"""
    await message.reply_dice(emoji="🎰")


@dp.message(F.dice)
async def handle_dice(message: Message):
    """Handle dice result"""
    if message.dice.emoji != "🎰":
        return
    
    dice_value = message.dice.value
    
    db = SessionLocal()
    user_id = message.from_user.id
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            username=message.from_user.username or message.from_user.first_name,
            current_prize="15",
            prize_level=0
        )
        db.add(user)
        db.commit()
    
    # Check if jackpot (777)
    if dice_value == JACKPOT_VALUE:
        # Start bowling game
        prize_level = user.prize_level
        pin_ranges = get_pin_ranges(prize_level)
        
        # Create game session
        game_id = uuid.uuid4().hex[:12]
        game_session = GameSession(
            user_id=user_id,
            prize_level=prize_level,
            current_prize=user.current_prize
        )
        db.add(game_session)
        db.commit()
        
        active_games[game_id] = {
            "session_id": game_session.id,
            "user_id": user_id,
            "current_prize": user.current_prize,
            "prize_level": prize_level,
        }
        
        # Create buttons for pinfall ranges
        keyboard = []
        for range_id, (min_pins, max_pins) in pin_ranges.items():
            button_text = f"🎳 {min_pins}-{max_pins}"
            keyboard.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"range_{game_id}_{range_id}"
            )])
        
        message_text = (
            f"🎉 <b>ДЖЕКПОТ! 777!</b> 🎉\n\n"
            f"{mention(user_id, message.from_user.full_name)}, поздравляю! 🎊\n\n"
            f"🎳 Началась мини-игра в боулинг!\n"
            f"💰 Приз на кону: <b>{user.current_prize}</b>\n\n"
            f"Выберите диапазон кедлей:"
        )
        
        await message.reply(message_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        # No jackpot
        pass
    
    db.close()


@dp.callback_query(F.data.startswith("range_"))
async def handle_range_selection(callback: CallbackQuery):
    """Handle range selection and throw pins"""
    await callback.answer()
    
    # Parse callback data
    parts = callback.data.split("_")
    game_id = parts[1]
    range_id = int(parts[2])
    
    game = active_games.get(game_id)
    if not game:
        await callback.message.edit_text("❌ Игра больше недоступна")
        return
    
    db = SessionLocal()
    user_id = game["user_id"]
    user = db.query(User).filter(User.user_id == user_id).first()
    
    pin_ranges = get_pin_ranges(game["prize_level"])
    min_pins, max_pins = pin_ranges[range_id]
    
    # Generate random pinfall (0-6)
    actual_pins = random.randint(0, 6)
    
    # Check if user guessed correctly
    won = min_pins <= actual_pins < max_pins
    
    # Update game session
    game_session_id = game["session_id"]
    game_session = db.query(GameSession).filter(GameSession.id == game_session_id).first()
    game_session.pinfall_range = f"{min_pins}-{max_pins}"
    game_session.actual_pins = actual_pins
    game_session.guessed_correctly = won
    
    # Update user
    user.total_games += 1
    
    if won:
        user.total_wins += 1
        # Повышаем приз
        if game["prize_level"] < len(PRIZE_LEVELS) - 1:
            new_level = game["prize_level"] + 1
            new_prize = str(PRIZE_LEVELS[new_level])
            level_message = f"✨ Приз повышен до <b>{new_prize}</b>!"
        else:
            # Уже на максимум (NFT)
            new_level = game["prize_level"]
            new_prize = str(PRIZE_LEVELS[new_level])
            level_message = f"🏆 Максимум - <b>NFT</b>!"
    else:
        # Приз сгорает - ИГРА ЗАКАНЧИВАЕТСЯ
        new_level = 0
        new_prize = str(PRIZE_LEVELS[0])
        level_message = f"💥 Приз сгорел! Начинаете с <b>15</b>"
    
    user.prize_level = new_level
    user.current_prize = new_prize
    user.last_played = datetime.utcnow()
    db.commit()
    
    # Create result message with emojis
    result_emoji = "✅ ПОПАЛ!" if won else "❌ ПРОМАХ!"
    
    pins_emoji = "🎳" * actual_pins
    
    message_text = (
        f"{result_emoji}\n\n"
        f"Выбор: <b>{min_pins}-{max_pins}</b>\n"
        f"Результат: {pins_emoji} <b>({actual_pins})</b>\n\n"
        f"{level_message}\n"
        f"💰 Приз: <b>{new_prize}</b>\n"
        f"Всего побед: {user.total_wins}/{user.total_games}"
    )
    
    await callback.message.edit_text(message_text)
    
    # Clean up
    active_games.pop(game_id, None)
    db.close()


async def main():
    """Start the bot"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
