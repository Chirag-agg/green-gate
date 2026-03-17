"""
Authentication router for GreenGate.
Handles user registration, login (JWT), and profile retrieval.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from models import User
from services.rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])

# JWT configuration
JWT_SECRET_KEY: str | None = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is required. Configure it in backend/.env before starting the API."
    )

# Password hashing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ──── Pydantic Schemas ────


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    company_name: str
    gstin: Optional[str] = None
    iec_number: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    company_name: str


class UserProfile(BaseModel):
    id: str
    email: str
    company_name: str
    gstin: Optional[str] = None
    iec_number: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──── Helper Functions ────


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against the hashed version."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    # Bcrypt requires bytes for the password and returns bytes for hash.
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Dependency to extract the current authenticated user from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


# ──── Endpoints ────


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth:register", max_requests=5, window_seconds=60))],
)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new MSME user account."""
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        company_name=request.company_name,
        gstin=request.gstin,
        iec_number=request.iec_number,
        state=request.state,
        sector=request.sector,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        company_name=user.company_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth:login", max_requests=10, window_seconds=60))],
)
def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login and receive a JWT access token."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        company_name=user.company_name,
    )


@router.get("/me", response_model=UserProfile)
def get_me(current_user: User = Depends(get_current_user)) -> UserProfile:
    """Get the current authenticated user's profile."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        company_name=current_user.company_name,
        gstin=current_user.gstin,
        iec_number=current_user.iec_number,
        state=current_user.state,
        sector=current_user.sector,
        created_at=current_user.created_at,
    )
