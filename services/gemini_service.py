
from google import genai
from google.genai import errors

from config import GEMINI_API_KEY, GEMINI_MODELS


class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing from .env")

        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def generate(self, prompt):
        errors_encountered = []

        for model in GEMINI_MODELS:
            try:
                print(f"Trying Gemini model: {model}")

                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                if not response.text:
                    raise ValueError(
                        f"{model} returned an empty response"
                    )

                print(f"Successful model: {model}")

                return {
                    "answer": response.text,
                    "model": model
                }

            except errors.APIError as error:
                print(f"{model} failed: {error}")

                # Try another model for availability,
                # quota, or model-not-found errors.
                if error.code in (404, 429, 503):
                    errors_encountered.append(
                        f"{model}: {error}"
                    )
                    continue

                raise

        raise RuntimeError(
            "All configured Gemini models failed.\n"
            + "\n".join(errors_encountered)
        )


gemini_service = GeminiService()
