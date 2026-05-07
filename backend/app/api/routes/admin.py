"""User management routes — admin/superadmin."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.deps import require_superadmin, require_admin_or_above
from app.core.security import hash_password
from app.db.models import User, UserRole, Conversation
from app.db.init_db import SUPERADMIN_EMAIL

router = APIRouter()


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    conversation_count: int


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    is_active: bool


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "viewer"


class AdminPasswordReset(BaseModel):
    new_password: str


def _parse_oid(oid: str):
    try:
        from beanie import PydanticObjectId
        return PydanticObjectId(oid)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid ID format: {oid}")


@router.get("/users", response_model=List[UserOut])
async def list_users(current_user: User = Depends(require_admin_or_above)):
    users = await User.find_all().to_list()
    result = []
    for u in users:
        conv_count = await Conversation.find(Conversation.user_id == str(u.id)).count()
        result.append(UserOut(
            id=str(u.id),
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at.strftime("%Y-%m-%d %H:%M"),
            conversation_count=conv_count,
        ))
    return result


@router.post("/users", status_code=201)
async def create_user(body: CreateUserRequest, current_user: User = Depends(require_admin_or_above)):
    if await User.find_one(User.email == body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role. Valid: admin, agent, viewer")
    # Only superadmin can create admin/superadmin accounts
    if role in (UserRole.admin, UserRole.superadmin) and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can create admin accounts")
    user = User(email=body.email, hashed_password=hash_password(body.password), role=role)
    await user.insert()
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, body: RoleUpdate, current_user: User = Depends(require_superadmin)):
    user = await User.get(_parse_oid(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == SUPERADMIN_EMAIL and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Cannot change the superadmin's role")
    try:
        user.role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role")
    await user.save()
    return {"id": user_id, "role": user.role.value}


@router.patch("/users/{user_id}/status")
async def update_user_status(user_id: str, body: StatusUpdate, current_user: User = Depends(require_superadmin)):
    user = await User.get(_parse_oid(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == SUPERADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Cannot deactivate the superadmin account")
    user.is_active = body.is_active
    await user.save()
    return {"id": user_id, "is_active": user.is_active}


@router.patch("/users/{user_id}/password")
async def admin_reset_password(user_id: str, body: AdminPasswordReset, current_user: User = Depends(require_admin_or_above)):
    user = await User.get(_parse_oid(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == SUPERADMIN_EMAIL and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can reset the superadmin's password")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    user.hashed_password = hash_password(body.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    await user.save()
    return {"message": f"Password reset for {user.email}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(require_superadmin)):
    user = await User.get(_parse_oid(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == SUPERADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Cannot delete the superadmin account")
    convs = await Conversation.find(Conversation.user_id == str(user.id)).to_list()
    for c in convs:
        await c.delete()
    await user.delete()
    return {"deleted": user_id}


@router.get("/stats")
async def get_stats(current_user: User = Depends(require_admin_or_above)):
    total_users = await User.count()
    active_users = await User.find(User.is_active == True).count()
    total_convs = await Conversation.count()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_conversations": total_convs,
    }
