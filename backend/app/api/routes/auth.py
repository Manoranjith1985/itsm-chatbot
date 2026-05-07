import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.models import User, UserRole
from app.api.deps import get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    if await User.find_one(User.email == body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.viewer,
    )
    await user.insert()
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = await User.find_one(User.email == body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return TokenResponse(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.strftime("%Y-%m-%d %H:%M"),
    }


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Generate a 6-digit reset code (shown in response since no email server)."""
    user = await User.find_one(User.email == body.email)
    # Always return 200 to prevent email enumeration
    if not user:
        return {"message": "If that email exists, a reset code has been generated.", "reset_token": None}
    token = str(secrets.randbelow(900000) + 100000)  # 6-digit code
    user.reset_token = token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    await user.save()
    return {
        "message": "Reset code generated. Use it within 30 minutes.",
        "reset_token": token,   # In production this would be emailed; shown here for demo
    }


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
    user = await User.find_one(User.email == body.email)
    if not user or not user.reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    if user.reset_token != body.token:
        raise HTTPException(status_code=400, detail="Incorrect reset code")
    if user.reset_token_expiry and datetime.now(timezone.utc) > user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    user.hashed_password = hash_password(body.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    await user.save()
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, current_user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
    current_user.hashed_password = hash_password(body.new_password)
    await current_user.save()
    return {"message": "Password changed successfully"}
