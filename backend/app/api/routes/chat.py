import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.db.models import User, Conversation, Message, Platform
from app.agent.graph import run_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


@router.post("/chat")
async def chat(body: ChatRequest, current_user: User = Depends(get_current_user)):
    conv = None
    if body.conversation_id:
        from beanie import PydanticObjectId
        conv = await Conversation.get(PydanticObjectId(body.conversation_id))
    if not conv:
        conv = Conversation(user_id=str(current_user.id), platform=Platform.web)
        await conv.insert()

    history = [{"role": m.role, "content": m.content} for m in conv.messages[-12:]]
    result = await run_agent(body.message, history, current_user)

    conv.messages.append(Message(role="user", content=body.message))
    conv.messages.append(Message(role="assistant", content=result["text"], chart_data=result.get("chart")))
    await conv.save()

    return {"conversation_id": str(conv.id), "response": result["text"], "chart": result.get("chart")}


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            token = data.get("token", "")
            from app.core.security import decode_token
            payload = decode_token(token)
            if not payload:
                await websocket.send_json({"type": "error", "message": "Unauthorized"})
                await websocket.close()
                return

            user = await User.find_one(User.email == payload["sub"])
            if not user:
                await websocket.close()
                return

            message = data.get("message", "")
            history = data.get("history", [])

            await websocket.send_json({"type": "stream_start"})

            result = await run_agent(message, history, user)

            await websocket.send_json({"type": "stream_chunk", "content": result["text"]})
            if result.get("chart"):
                await websocket.send_json({"type": "chart", "data": result["chart"]})
            await websocket.send_json({"type": "stream_end"})

    except WebSocketDisconnect:
        pass


@router.get("/conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    convs = await Conversation.find(Conversation.user_id == str(current_user.id)).to_list()
    return [{"id": str(c.id), "created_at": c.created_at, "message_count": len(c.messages)} for c in convs]
