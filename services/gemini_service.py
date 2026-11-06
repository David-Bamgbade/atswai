import asyncio
import time

from google import genai
from google.genai import errors, types

from config import GEMINI_API_KEY, GEMINI_MODELS


class GeminiService:

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing from .env")

        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=20000,
                retry_options=types.HttpRetryOptions(attempts=1)
            )
        )

        self.async_client = self.client.aio
        self.last_successful_model = None

    async def generate(self, prompt, json_mode=False):

        errors_encountered = []

        # Prioritize the model that most recently generated successfully.
        models = list(GEMINI_MODELS)

        if self.last_successful_model in models:
            models.remove(self.last_successful_model)
            models.insert(0, self.last_successful_model)

        for model in models:

            start_time = time.perf_counter()

            try:
                print(f"Trying Gemini model: {model}", flush=True)

                request_config = None

                if json_mode:
                    request_config = types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )

                response = await asyncio.wait_for(
                    self.async_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=request_config
                    ),
                    timeout=20.0
                )

                elapsed = time.perf_counter() - start_time

                if not response.text:
                    raise ValueError(
                        f"{model} returned an empty response"
                    )

                self.last_successful_model = model

                print(
                    f"Successful model: {model} ({elapsed:.2f}s)",
                    flush=True
                )

                return {
                    "answer": response.text,
                    "model": model
                }

            except asyncio.TimeoutError:

                elapsed = time.perf_counter() - start_time
                message = f"{model} timed out after {elapsed:.2f}s"

                print(message, flush=True)
                errors_encountered.append(message)

            except errors.APIError as error:

                elapsed = time.perf_counter() - start_time

                print(
                    f"{model} failed after {elapsed:.2f}s: {error}",
                    flush=True
                )

                if error.code in (400, 404, 408, 429, 500, 502, 503, 504):
                    errors_encountered.append(f"{model}: {error}")
                    continue

                raise

        raise RuntimeError(
            "All configured Gemini models failed.\n"
            + "\n".join(errors_encountered)
        )

    async def close(self):
        await self.async_client.aclose()


gemini_service = GeminiService()
