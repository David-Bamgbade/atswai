import asyncio
import time

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODELS


async def main():
    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=15000,
            retry_options=types.HttpRetryOptions(attempts=1)
        )
    )

    try:
        for model in GEMINI_MODELS:
            start = time.perf_counter()

            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model,
                        contents="Reply with OK."
                    ),
                    timeout=16
                )

                elapsed = time.perf_counter() - start

                if response.text:
                    print(f"PASS | {model} | {elapsed:.2f}s")
                else:
                    print(f"EMPTY | {model} | {elapsed:.2f}s")

            except asyncio.TimeoutError:
                print(f"TIMEOUT | {model} | 16 seconds")

            except Exception as error:
                elapsed = time.perf_counter() - start
                print(
                    f"FAIL | {model} | {elapsed:.2f}s | "
                    f"{type(error).__name__}: {error}"
                )

    finally:
        await client.aio.aclose()


asyncio.run(main())
