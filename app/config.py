import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
	OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

	# SearchAPI.io
	SEARCHAPI_KEY: str = os.getenv("SEARCHAPI_KEY", "")
	SEARCHAPI_RESULTS: int = int(os.getenv("SEARCHAPI_RESULTS", "5"))

	# OpenAI model choices
	OPENAI_MODEL_CLAIMS: str = os.getenv("OPENAI_MODEL_CLAIMS", "gpt-4o-mini")
	OPENAI_MODEL_VERDICT: str = os.getenv("OPENAI_MODEL_VERDICT", "gpt-4o-mini")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()