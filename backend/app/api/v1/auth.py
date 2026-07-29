from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.login_history import LoginHistory
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        location=payload.location,
        preferred_language=payload.preferred_language,
        # role is intentionally omitted here: it always defaults to FARMER at the
        # database level (see User.role). Public registration can never create
        # an admin account.
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    credentials_valid = bool(user and verify_password(payload.password, user.hashed_password))
    success = credentials_valid and bool(user and user.is_active)

    db.add(LoginHistory(
        user_id=user.id if user else None,
        email_attempted=payload.email,
        success=success,
        remember_me=payload.remember_me,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    if not credentials_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    return TokenResponse(
        access_token=create_access_token(user.email, user.role.value),
        refresh_token=create_refresh_token(user.email, user.role.value) if payload.remember_me else None,
        user=user,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Silently mints a new access token from a still-valid refresh token, so a
    "Remember Me" login doesn't have to be repeated until the refresh token
    itself expires (see REFRESH_TOKEN_EXPIRE_MINUTES) or the user logs out."""
    invalid = HTTPException(status_code=401, detail="Invalid or expired refresh token")
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise invalid

    user = db.query(User).filter(User.email == decoded["sub"]).first()
    if not user or not user.is_active:
        raise invalid

    return TokenResponse(
        access_token=create_access_token(user.email, user.role.value),
        refresh_token=create_refresh_token(user.email, user.role.value),  # rotate
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
