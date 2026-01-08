import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_summary(monkeypatch, client):
    # Create a fake Groq client
    mock_client = AsyncMock()
    mock_client.summarize.return_value = "mock summary"

    # Patch the app-level client
    monkeypatch.setattr("app.main.client", mock_client)

    response = await client.post(
        "/summaries",
        json={"input_text": "This is a long test input. " * 10}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["summary_text"] == "mock summary"
