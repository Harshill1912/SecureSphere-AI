"""Configuration management for production environment"""
import os
from typing import List
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # API Settings
    API_TITLE: str = os.getenv("API_TITLE", "SecureSphere API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv("API_DESCRIPTION", "Production-ready AI-powered document Q&A system")
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        origin.strip() 
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ]
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    CORS_ALLOW_METHODS: List[str] = os.getenv("CORS_ALLOW_METHODS", "*").split(",")
    CORS_ALLOW_HEADERS: List[str] = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
    
    # File Upload Settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    # AI Model Settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_CONTEXT_SIZE: int = int(os.getenv("LLM_CONTEXT_SIZE", "2048"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    
    # Vector DB Settings
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "securesphere_collection")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    SIMILARITY_SEARCH_K: int = int(os.getenv("SIMILARITY_SEARCH_K", "5"))
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./secureSphere.db")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "200"))
    
    # Chat Settings
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "1000"))
    MIN_QUERY_LENGTH: int = int(os.getenv("MIN_QUERY_LENGTH", "3"))
    CHAT_TIMEOUT_SECONDS: int = int(os.getenv("CHAT_TIMEOUT_SECONDS", "120"))  # Increased to 120s for slower LLMs
    ENABLE_CHAT_HISTORY: bool = os.getenv("ENABLE_CHAT_HISTORY", "True").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production-min-32-chars-long")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
