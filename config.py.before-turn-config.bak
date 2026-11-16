import os
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "accountingknowledgebase"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_MODELS",
        "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-3.1-flash-lite"
    ).split(",")
    if model.strip()
]

GEMINI_LIVE_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_LIVE_MODELS",
        ""
    ).split(",")
    if model.strip()
]

MODEL_NAME = GEMINI_MODELS[0]

