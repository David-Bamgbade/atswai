import asyncio
from contextlib import AsyncExitStack, asynccontextmanager

from google import genai

from config import GEMINI_API_KEY, GEMINI_LIVE_MODELS


class GeminiLiveService:

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing from .env")

        if not GEMINI_LIVE_MODELS:
            raise ValueError("GEMINI_LIVE_MODELS is empty in .env")

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.async_client = self.client.aio
        self.last_successful_model = None

    @asynccontextmanager
    async def connect(self, config):

        models = list(GEMINI_LIVE_MODELS)

        if self.last_successful_model in models:
            models.remove(self.last_successful_model)
            models.insert(0, self.last_successful_model)

        errors_encountered = []

        for model in models:
            stack = AsyncExitStack()

            try:
                print(
                    f"Connecting to Gemini Live model: {model}",
                    flush=True
                )

                session = await stack.enter_async_context(
                    self.async_client.live.connect(
                        model=model,
                        config=config
                    )
                )

            except asyncio.CancelledError:
                await stack.aclose()
                raise

            except Exception as error:
                await stack.aclose()

                message = (
                    f"{model} connection failed: "
                    f"{type(error).__name__}: {error}"
                )

                print(message, flush=True)
                errors_encountered.append(message)
                continue

            self.last_successful_model = model

            print(
                f"Gemini Live connected successfully: {model}",
                flush=True
            )

            try:
                yield session, model
            finally:
                await stack.aclose()

            return

        raise RuntimeError(
            "All configured Gemini Live models failed.\n"
            + "\n".join(errors_encountered)
        )

    async def close(self):
        await self.async_client.aclose()
        self.client.close()


gemini_live_service = GeminiLiveService()
