"""
Centralized LLM client factory.
All agents use this — no scattered ChatGroq initialization.
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv(override=True)

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()
if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY not found. "
        "Create a .env file with: GROQ_API_KEY=your_key_here"
    )

MODEL_NAME = "llama-3.3-70b-versatile"

# ── Cached instances keyed by (max_tokens, temperature) ──────
_instances: dict[tuple, ChatGroq] = {}


def get_llm(
    max_tokens: int = 3000,
    temperature: float = 0.1,
    timeout: int = 60,
) -> ChatGroq:
    """
    Return a ChatGroq instance. Reuses cached instances for
    identical (max_tokens, temperature) combinations.
    """
    key = (max_tokens, temperature)
    if key not in _instances:
        _instances[key] = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=MODEL_NAME,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    return _instances[key]

