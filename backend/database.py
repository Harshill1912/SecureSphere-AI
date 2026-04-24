"""Database models and session management"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Generator
import os

from config import get_settings

settings = get_settings()

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_login = Column(DateTime, nullable=True)


class ChatHistory(Base):
    """Chat history model for persistence"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)  # For user isolation
    session_id = Column(String, index=True, nullable=True)  # For session tracking
    filename = Column(String, index=True, nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    response_time = Column(Float, nullable=True)  # Response time in seconds
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_filename_created', 'filename', 'created_at'),
        Index('idx_session_created', 'session_id', 'created_at'),
        Index('idx_user_filename', 'user_id', 'filename'),
    )


class ChatSession(Base):
    """Chat session model for tracking conversations"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)  # For user isolation
    session_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, index=True, nullable=False)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentMetadata(Base):
    """Document metadata for tracking uploads"""
    __tablename__ = "document_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)  # For user isolation
    filename = Column(String, index=True, nullable=False)  # Removed unique - users can have same filename
    file_size = Column(Integer, nullable=True)
    chunks_count = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed = Column(DateTime, nullable=True)
    
    # Composite unique constraint: same user can't upload same filename twice
    __table_args__ = (
        Index('idx_user_filename', 'user_id', 'filename', unique=True),
    )


# Create tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
