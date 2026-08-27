import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bowling_bot.db")

# Bowling Game Settings
PINS_RANGES = {
    0: (0, 3),
    1: (3, 6),
    2: (6, 8),
    3: (8, 10),
}

# Prize Levels
PRIZE_LEVELS = [15, 40, 75, 100, "NFT"]
INITIAL_PRIZE = 15

# Game Settings
MIN_PINS = 0
MAX_PINS = 10
THROWS_PER_GAME = 1
