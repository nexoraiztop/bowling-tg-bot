import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bowling_bot.db")

# Bowling Game Settings - динамические диапазоны в зависимости от уровня
# Уровень 0-3: 2 кнопки (0-3, 3-6)
# Уровень 4+: 3 кнопки (0-2, 2-4, 4-6)

PRIZE_LEVELS = [15, 40, 75, 100, "NFT"]
INITIAL_PRIZE = 15

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

MIN_PINS = 0
MAX_PINS = 6
