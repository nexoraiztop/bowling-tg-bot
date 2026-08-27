import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bowling_bot.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    username = Column(String)
    current_prize = Column(String, default="15")
    prize_level = Column(Integer, default=0)
    total_games = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_played = Column(DateTime, nullable=True)


class GameSession(Base):
    __tablename__ = "game_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    prize_level = Column(Integer)
    current_prize = Column(String)
    pinfall_range = Column(String, nullable=True)
    actual_pins = Column(Integer, nullable=True)
    guessed_correctly = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create all tables
Base.metadata.create_all(bind=engine)
