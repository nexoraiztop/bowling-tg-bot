import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

from config import BOT_TOKEN, PRIZE_LEVELS, PIN_RANGES_2_BUTTONS, PIN_RANGES_3_BUTTONS, MAX_PINS
from database import SessionLocal, User, GameSession

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_pin_ranges(prize_level):
    """Get pin ranges based on prize level"""
    if prize_level >= 2:  # 75, 100, NFT - 3 кнопки
        return PIN_RANGES_3_BUTTONS
    else:  # 15, 40 - 2 кнопки
        return PIN_RANGES_2_BUTTONS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    db = SessionLocal()
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id, username=username, current_prize="15", prize_level=0)
        db.add(user)
        db.commit()
    
    welcome_text = (
        f"🎰 Добро пожаловать в Bowling Slot Bot!\n\n"
        f"Правила игры:\n"
        f"1️⃣ Напишите сообщение с эмодзи 🎰\n"
        f"2️⃣ Если выпадет 777 - запускается мини-игра в боулинг!\n"
        f"3️⃣ Выберите диапазон кедлей и попробуйте угадать\n"
        f"4️⃣ Если попадете - приз повышается, если нет - приз сгорает!\n\n"
        f"💰 Призы: 15 → 40 → 75 → 100 → NFT\n\n"
        f"Ваш текущий приз: <b>{user.current_prize}</b>"
    )
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
    db.close()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any message with 🎰"""
    if "🎰" not in update.message.text:
        return
    
    db = SessionLocal()
    user_id = update.effective_user.id
    
    # Get or create user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id, username=update.effective_user.username, current_prize="15", prize_level=0)
        db.add(user)
        db.commit()
    
    # Spin the slots - 3 random numbers
    slot_results = [random.randint(1, 9) for _ in range(3)]
    slot_display = " ".join([str(x) for x in slot_results])
    
    # Check if 777
    if slot_results == [7, 7, 7]:
        # Start bowling game
        prize_level = user.prize_level
        pin_ranges = get_pin_ranges(prize_level)
        
        # Create game session
        game_session = GameSession(
            user_id=user_id,
            prize_level=prize_level,
            current_prize=user.current_prize
        )
        db.add(game_session)
        db.commit()
        
        context.user_data['game_session_id'] = game_session.id
        context.user_data['current_prize'] = user.current_prize
        context.user_data['prize_level'] = prize_level
        
        # Create buttons for pinfall ranges
        keyboard = []
        for range_id, (min_pins, max_pins) in pin_ranges.items():
            button_text = f"🎳 {min_pins}-{max_pins}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"range_{range_id}")])
        
        message_text = (
            f"🎰 {slot_display} 🎰\n\n"
            f"🎉 777! 🎉\n\n"
            f"🎳 Мини-игра в боулинг!\n"
            f"💰 Приз на кону: <b>{user.current_prize}</b>\n\n"
            f"Выберите диапазон кедлей:"
        )
        
        await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        # No jackpot
        message_text = f"🎰 {slot_display} 🎰"
        await update.message.reply_text(message_text)
    
    db.close()


async def select_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle range selection and throw pins"""
    query = update.callback_query
    await query.answer()
    
    # Extract range id from callback data
    range_id = int(query.data.split("_")[1])
    
    db = SessionLocal()
    user_id = update.effective_user.id
    user = db.query(User).filter(User.user_id == user_id).first()
    
    pin_ranges = get_pin_ranges(context.user_data['prize_level'])
    min_pins, max_pins = pin_ranges[range_id]
    
    # Generate random pinfall (0-6)
    actual_pins = random.randint(0, MAX_PINS)
    
    # Check if user guessed correctly
    won = min_pins <= actual_pins < max_pins
    
    # Update game session
    game_session_id = context.user_data['game_session_id']
    game_session = db.query(GameSession).filter(GameSession.id == game_session_id).first()
    game_session.pinfall_range = f"{min_pins}-{max_pins}"
    game_session.actual_pins = actual_pins
    game_session.guessed_correctly = won
    
    # Update user
    user.total_games += 1
    
    if won:
        user.total_wins += 1
        # Повышаем приз
        if context.user_data['prize_level'] < len(PRIZE_LEVELS) - 1:
            new_level = context.user_data['prize_level'] + 1
            new_prize = str(PRIZE_LEVELS[new_level])
            level_message = f"✨ Приз повышен до <b>{new_prize}</b>!"
        else:
            # Уже на максимум (NFT)
            new_level = context.user_data['prize_level']
            new_prize = str(PRIZE_LEVELS[new_level])
            level_message = f"🏆 Максимум - <b>NFT</b>!"
    else:
        # Приз сгорает - ИГРА ЗАКАНЧИВАЕТСЯ
        new_level = 0
        new_prize = str(PRIZE_LEVELS[0])
        level_message = f"💥 Приз сгорел! Начинаете с <b>15</b>"
    
    user.prize_level = new_level
    user.current_prize = new_prize
    db.commit()
    
    # Create result message with emojis
    result_emoji = "✅ ПОПАЛ!" if won else "❌ ПРОМАХ!"
    
    pins_emoji = "🎳" * actual_pins
    
    message_text = (
        f"{result_emoji}\n\n"
        f"Выбор: <b>{min_pins}-{max_pins}</b>\n"
        f"Результат: {pins_emoji} <b>({actual_pins})</b>\n\n"
        f"{level_message}\n"
        f"💰 Приз: <b>{new_prize}</b>"
    )
    
    await query.edit_message_text(message_text, parse_mode=ParseMode.HTML)
    db.close()


def main() -> None:
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(select_range, pattern="^range_"))
    
    # Run the bot
    application.run_polling()


if __name__ == '__main__':
    main()
