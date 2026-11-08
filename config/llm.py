
from langchain_ollama import ChatOllama, OllamaEmbeddings

from config.settings import settings


# =========================================
# LOCAL LLM
# =========================================

llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0
)


# =========================================
# EMBEDDING MODEL
# =========================================

embeddings = OllamaEmbeddings(
    model=settings.OLLAMA_EMBED_MODEL,
    base_url=settings.OLLAMA_BASE_URL
)
