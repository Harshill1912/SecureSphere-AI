"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from config import get_settings

settings = get_settings()


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    query: str = Field(..., min_length=settings.MIN_QUERY_LENGTH, max_length=settings.MAX_QUERY_LENGTH)
    filename: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    conversation_history: Optional[List[dict]] = None  # For follow-up questions
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        # Security: prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Invalid filename')
        return v


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    answer: str
    session_id: Optional[str] = None
    response_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources_count: Optional[int] = None


class UploadResponse(BaseModel):
    """Response schema for upload endpoint"""
    message: str
    file: str
    chunks_added: int
    file_size: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict] = None


class SummarizeRequest(BaseModel):
    """Request schema for summarization"""
    filename: str


class CompareRequest(BaseModel):
    """Request schema for document comparison"""
    filename1: str
    filename2: str


class MultiSearchRequest(BaseModel):
    """Request schema for multi-document search"""
    query: str
    filenames: Optional[List[str]] = None


class AnalyticsResponse(BaseModel):
    """Analytics response schema"""
    total_documents: int
    total_chats: int
    total_sessions: int
    average_response_time: Optional[float] = None
    most_asked_questions: List[dict] = []
    popular_documents: List[dict] = []


class UserRegister(BaseModel):
    """User registration schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        return v.strip().lower()


class UserLogin(BaseModel):
    """User login schema"""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True