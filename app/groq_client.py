from groq import AsyncGroq
from app.config import settings
from app.exceptions import ExternalServiceError
import asyncio
import logging

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.timeout = settings.groq_timeout
        self.retries = settings.groq_retries
        self.backoff = settings.groq_backoff

    async def summarize(self, text: str) -> str:
        """Call the Groq chat completion in a resilient way: retries + timeout.

        Returns the concatenated streamed response text.
        Raises `ExternalServiceError` when exhausted.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                async def _call_and_gather():
                    completion = await self.client.chat.completions.create(
                        model=settings.groq_model,
                        messages=[{"role": "user", "content": text}],
                        temperature=1,
                        max_completion_tokens=1024,
                        top_p=1,
                        stream=True,
                        stop=None,
                    )

                    full_response = ""
                    async for chunk in completion:
                        full_response += (chunk.choices[0].delta.content or "")
                    return full_response

                # enforce an overall timeout for the network+streaming operation
                return await asyncio.wait_for(_call_and_gather(), timeout=self.timeout)

            except Exception as exc:
                logger.exception("Groq summarize attempt %s failed", attempt)
                if attempt >= self.retries:
                    raise ExternalServiceError()
                # exponential backoff
                await asyncio.sleep(self.backoff * (2 ** (attempt - 1)))
