"""Authentication routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, User
from schemas import UserRegister, UserLogin, Token, UserResponse
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user
)
from logger_config import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if username already exists
        existing_user = db.query(User).filter(
            User.username == user_data.username.lower()
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = db.query(User).filter(
            User.email == user_data.email.lower()
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            is_active=1
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.username}")
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            is_active=bool(new_user.is_active),
            created_at=new_user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    try:
        # Find user by username
        user = db.query(User).filter(
            User.username == form_data.username.lower()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if user.is_active == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        logger.info(f"User logged in: {user.username}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during login"
        )


@router.post("/login/json", response_model=Token)
async def login_json(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with JSON body (alternative to form data)"""
    try:
        # Find user by username
        user = db.query(User).filter(
            User.username == user_data.username.lower()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if user.is_active == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        logger.info(f"User logged in: {user.username}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during login"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=bool(current_user.is_active),
        created_at=current_user.created_at
    )
