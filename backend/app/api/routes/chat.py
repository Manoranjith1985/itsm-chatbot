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


def _parse_object_id(oid: str):
    """Parse a MongoDB ObjectId string, raising 422 on invalid format."""
    try:
        from beanie import PydanticObjectId
        return PydanticObjectId(oid)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid ID format: {oid}")


@router.post("/chat")
async def chat(body: ChatRequest, current_user: User = Depends(get_current_user)):
    conv = None
    if body.conversation_id:
        try:
            conv = await Conversation.get(_parse_object_id(body.conversation_id))
        except HTTPException:
            conv = None  # treat bad ID as new conversation

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
    # Validate token BEFORE accepting the connection
    token = websocket.query_params.get("token", "")
    if token:
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=4001)
            return
    # If no query param token, we'll validate from first message
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            # Support token in both query params and message body
            msg_token = data.get("token", token)
            from app.core.security import decode_token
            payload = decode_token(msg_token)
            if not payload:
                await websocket.send_json({"type": "error", "message": "Unauthorized"})
                await websocket.close(code=4001)
                return

            user = await User.find_one(User.email == payload.get("sub", ""))
            if not user:
                await websocket.close(code=4001)
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
    except Exception:
        pass


@router.get("/conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    convs = await Conversation.find(Conversation.user_id == str(current_user.id)).to_list()
    return [{"id": str(c.id), "created_at": c.created_at, "message_count": len(c.messages)} for c in convs]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: User = Depends(get_current_user)):
    conv = await Conversation.get(_parse_object_id(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")
    await conv.delete()
    return {"deleted": conversation_id}


@router.delete("/conversations")
async def delete_all_conversations(current_user: User = Depends(get_current_user)):
    convs = await Conversation.find(Conversation.user_id == str(current_user.id)).to_list()
    for c in convs:
        await c.delete()
    return {"deleted": len(convs)}
