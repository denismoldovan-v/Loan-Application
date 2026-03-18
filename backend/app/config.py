import os
from functools import lru_cache

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def get_settings():
    # Load .env once; cached for the lifetime of the process.
    load_dotenv()

    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    }

