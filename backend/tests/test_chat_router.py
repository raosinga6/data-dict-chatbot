import pytest


@pytest.mark.asyncio
async def test_chat_returns_200(client):
    payload = {"question": "what tables exist?"}
    response = await client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_response_schema(client):
    payload = {"question": "describe orders table"}
    data = (await client.post("/api/v1/chat", json=payload)).json()
    assert "session_id" in data
    assert "question" in data


@pytest.mark.asyncio
async def test_chat_empty_message_fails_validation(client):
    payload = {"question": "hi"}
    response = await client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_too_long_fails_validation(client):
    payload = {"question": "x" * 2001}
    response = await client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feedback_accepted(client):
    payload = {"trace_id": "test-trace-001", "rating": "good"}
    response = await client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_feedback_invalid_rating(client):
    payload = {"trace_id": "test-trace-002", "rating": "maybe"}
    response = await client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_process_time_header_present(client):
    response = await client.post("/api/v1/chat", json={"question": "hello world?"})
    assert "X-Process-Time" in response.headers
