"""Tests for Copilot Chat, Conversations, and User Feedback."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_copilot_chat_flow(async_client: AsyncClient):
    # 1. Send first chat message (creates a conversation automatically)
    chat_payload = {
        "message": "What is the policy for password complexity?",
        "include_graph": True,
        "max_depth": 2,
    }
    chat_res = await async_client.post("/api/copilot/chat", json=chat_payload)
    assert chat_res.status_code == 200
    msg = chat_res.json()

    assert msg["sender"] == "copilot"
    assert "content" in msg
    assert msg["grounding_score"] is not None
    conversation_id = msg["conversation_id"]
    message_id = msg["id"]
    assert conversation_id is not None

    # 2. Submit feedback on the copilot answer
    fb_payload = {
        "rating": "helpful",
        "feedback_text": "Accurate response with verifiable citations.",
    }
    fb_res = await async_client.post(
        f"/api/copilot/messages/{message_id}/feedback",
        json=fb_payload,
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["rating"] == "helpful"
    assert fb_data["message_id"] == message_id

    # 3. List conversations
    convs_res = await async_client.get("/api/copilot/conversations")
    assert convs_res.status_code == 200
    conv_list = convs_res.json()
    assert len(conv_list) >= 1
    assert any(c["id"] == conversation_id for c in conv_list)

    # 4. Get conversation detail
    detail_res = await async_client.get(f"/api/copilot/conversations/{conversation_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["messages"]) >= 2  # user + copilot

    # 5. Delete conversation
    del_res = await async_client.delete(f"/api/copilot/conversations/{conversation_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


@pytest.mark.asyncio
async def test_copilot_chat_stream_flow(async_client: AsyncClient):
    chat_payload = {
        "message": "What is the policy for zero trust architecture?",
        "include_graph": True,
        "max_depth": 2,
    }
    res = await async_client.post("/api/copilot/chat/stream", json=chat_payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

    body = res.text
    assert "data: " in body
    assert '"event": "metadata"' in body
    assert '"event": "token"' in body or '"event": "done"' in body
    assert '"event": "done"' in body
