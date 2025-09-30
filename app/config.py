import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
	OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
	YANDEX_USER: str = os.getenv("YANDEX_USER", "")
	YANDEX_KEY: str = os.getenv("YANDEX_KEY", "")

	# Optional Yandex XML params
	YANDEX_L10N: str = os.getenv("YANDEX_L10N", "ru")
	YANDEX_SORTBY: str = os.getenv("YANDEX_SORTBY", "rlv")
	YANDEX_FILTER: str = os.getenv("YANDEX_FILTER", "strict")
	YANDEX_RESULTS: int = int(os.getenv("YANDEX_RESULTS", "5"))

	# OpenAI model choices
	OPENAI_MODEL_CLAIMS: str = os.getenv("OPENAI_MODEL_CLAIMS", "gpt-4o-mini")
	OPENAI_MODEL_VERDICT: str = os.getenv("OPENAI_MODEL_VERDICT", "gpt-4o-mini")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()