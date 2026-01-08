import sys
import pathlib
import pytest
import asyncio
from httpx import AsyncClient

# Ensure project root is on sys.path so `import app` works when pytest
# adds the test directory to sys.path during collection.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the FastAPI app for the test client after ensuring sys.path
from app.main import app as fastapi_app

# This fixture is sometimes needed to force the event loop scope for async tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        yield ac
