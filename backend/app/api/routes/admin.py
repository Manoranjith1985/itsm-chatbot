"""User management routes — superadmin only."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_superadmin, require_admin_or_above
from app.db.models import User, UserRole, Conversation

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


@router.get("/users", response_model=List[UserOut])
async def list_users(current_user: User = Depends(require_superadmin)):
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


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    current_user: User = Depends(require_superadmin),
):
    from beanie import PydanticObjectId
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Protect superadmin account from role downgrade by anyone except themselves
    if user.email == "manoumaranjith@gmail.com" and current_user.id != user.id:
        raise HTTPException(status_code=403, detail="Cannot change the superadmin's role")

    try:
        user.role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    await user.save()
    return {"id": user_id, "role": user.role.value}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: StatusUpdate,
    current_user: User = Depends(require_superadmin),
):
    from beanie import PydanticObjectId
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email == "manoumaranjith@gmail.com":
        raise HTTPException(status_code=403, detail="Cannot deactivate the superadmin account")

    user.is_active = body.is_active
    await user.save()
    return {"id": user_id, "is_active": user.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_superadmin),
):
    from beanie import PydanticObjectId
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email == "manoumaranjith@gmail.com":
        raise HTTPException(status_code=403, detail="Cannot delete the superadmin account")

    # Delete all their conversations too
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
