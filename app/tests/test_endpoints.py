import pytest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_get_summary_success(monkeypatch, client):
    sample_id = str(uuid.uuid4())
    fake_obj = SimpleNamespace(
        id=sample_id,
        input_text="some long input text that is valid...",
        summary_text="a short summary",
        model="groq",
    )

    monkeypatch.setattr("app.crud.get_summary", AsyncMock(return_value=fake_obj))

    res = await client.get(f"/summaries/{sample_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["summary_text"] == "a short summary"


@pytest.mark.asyncio
async def test_get_summary_not_found(monkeypatch, client):
    sample_id = str(uuid.uuid4())
    monkeypatch.setattr("app.crud.get_summary", AsyncMock(return_value=None))

    res = await client.get(f"/summaries/{sample_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_summary_success(monkeypatch, client):
    sample_id = str(uuid.uuid4())
    fake_obj = SimpleNamespace(
        id=sample_id,
        input_text="some long input text that is valid...",
        summary_text="old summary",
        model="groq",
    )

    async def fake_get_db():
        class DummySession:
            async def commit(self):
                return None

            async def refresh(self, obj):
                return None

        yield DummySession()

    monkeypatch.setattr("app.crud.get_summary", AsyncMock(return_value=fake_obj))
    monkeypatch.setattr("app.main.get_db", fake_get_db)

    res = await client.put(f"/summaries/{sample_id}", json={"summary_text": "new summary"})
    assert res.status_code == 200
    data = res.json()
    assert data["summary_text"] == "new summary"


@pytest.mark.asyncio
async def test_delete_summary_success(monkeypatch, client):
    sample_id = str(uuid.uuid4())
    fake_obj = SimpleNamespace(
        id=sample_id,
        input_text="some long input text that is valid...",
        summary_text="a short summary",
        model="groq",
    )

    async def fake_get_db():
        class DummySession:
            async def delete(self, obj):
                return None

            async def commit(self):
                return None

        yield DummySession()

    monkeypatch.setattr("app.crud.get_summary", AsyncMock(return_value=fake_obj))
    monkeypatch.setattr("app.main.get_db", fake_get_db)

    res = await client.delete(f"/summaries/{sample_id}")
    assert res.status_code == 204
