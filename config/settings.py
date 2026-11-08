
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # MySQL
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "query_optimizer_db")

    DB_READ_USER = os.getenv("DB_READ_USER")
    DB_READ_PASSWORD = os.getenv("DB_READ_PASSWORD")

    DB_DBA_USER = os.getenv("DB_DBA_USER")
    DB_DBA_PASSWORD = os.getenv("DB_DBA_PASSWORD")

    # Ollama
    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:7b"
    )

    OLLAMA_EMBED_MODEL = os.getenv(
        "OLLAMA_EMBED_MODEL",
        "nomic-embed-text"
    )


settings = Settings()
