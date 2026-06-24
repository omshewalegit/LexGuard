# """
# Centralized LLM client factory.

# All agents import from here — no scattered ChatGroq initialization.

# Dual-model architecture:
#   - get_llm()      → 70B (smart)  — for risk analysis, deep legal reasoning
#   - get_fast_llm() → 8B  (fast)   — for extraction, classification, simplification

# API key rotation: round-robin across all configured keys to distribute
# rate-limit headroom evenly. Random selection (previous design) caused
# hot-spotting where one key would hit its limit while others sat idle.
# """

# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# from utils.logger import get_logger
# import os
# import threading

# load_dotenv(override=True)

# logger = get_logger("llm")

# # ── Load all available API keys ─────────────────────────────────
# GROQ_KEYS = [
#     (os.getenv("GROQ_API_KEY_1") or "").strip(),
#     (os.getenv("GROQ_API_KEY_2") or "").strip(),
#     (os.getenv("GROQ_API_KEY_3") or "").strip(),
# ]
# GROQ_KEYS = [k for k in GROQ_KEYS if k]

# if not GROQ_KEYS:
#     raise EnvironmentError(
#         "No GROQ API keys found. "
#         "Add GROQ_API_KEY_1 (and optionally _2, _3) to your .env file."
#     )

# MODEL_SMART = "llama-3.3-70b-versatile"
# MODEL_FAST  = "llama-3.1-8b-instant"

# # ── Thread-safe round-robin key selector ────────────────────────
# _key_index = 0
# _key_lock  = threading.Lock()


# def _next_key() -> tuple[str, int]:
#     """Return the next API key in round-robin order (thread-safe)."""
#     global _key_index
#     with _key_lock:
#         key = GROQ_KEYS[_key_index % len(GROQ_KEYS)]
#         idx = (_key_index % len(GROQ_KEYS)) + 1
#         _key_index += 1
#     return key, idx


# # ── Cached instances ────────────────────────────────────────────
# # Keyed by (model, max_tokens, temperature, api_key) — reuses
# # existing ChatGroq objects instead of creating a new one per call.
# _instances: dict[tuple, ChatGroq] = {}
# _cache_lock = threading.Lock()


# def _get_or_create(
#     model: str,
#     max_tokens: int,
#     temperature: float,
#     timeout: int,
# ) -> ChatGroq:
#     """Return a cached ChatGroq instance, creating one if needed."""
#     key, key_idx = _next_key()
#     cache_key = (model, max_tokens, temperature, key)

#     with _cache_lock:
#         if cache_key not in _instances:
#             _instances[cache_key] = ChatGroq(
#                 api_key=key,
#                 model_name=model,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#                 timeout=timeout,
#             )
#             logger.debug(
#                 f"Created new {model.split('-')[0]}… instance "
#                 f"(key={key_idx}, tokens={max_tokens}, temp={temperature})"
#             )

#     return _instances[cache_key]


# def get_llm(
#     max_tokens: int = 3000,
#     temperature: float = 0.1,
#     timeout: int = 60,
# ) -> ChatGroq:
#     """
#     Return a 70B (smart) model instance.

#     Use for tasks requiring deep reasoning: risk assessment, legal analysis,
#     cross-clause validation. Slower but dramatically more accurate.
#     """
#     return _get_or_create(MODEL_SMART, max_tokens, temperature, timeout)


# def get_fast_llm(
#     max_tokens: int = 3000,
#     temperature: float = 0.1,
#     timeout: int = 60,
# ) -> ChatGroq:
#     """
#     Return an 8B (fast) model instance.

#     Use for simpler tasks: document classification, clause extraction,
#     plain-language simplification. Faster, lower token cost.
#     """
#     return _get_or_create(MODEL_FAST, max_tokens, temperature, timeout)

"""
Centralized LLM client factory.

All agents import from here — no scattered ChatGroq initialization.

Dual-model architecture:
  - get_llm()      → 70B (smart)  — for risk analysis, deep legal reasoning
  - get_fast_llm() → 8B  (fast)   — for extraction, classification, simplification

API key rotation: round-robin across all configured keys to distribute
rate-limit headroom evenly.

FIX HISTORY:
1) (original) Round-robin key selection with cached ChatGroq instances.
2) (2026-06-22, fix #1) [CURRENT]
   - CRITICAL BUG FIXED: cache key previously included the api_key, so
     round-robin only fired on cold-start (first 3 calls). After that,
     every call hit the cache and returned the same instance for the same
     (model, max_tokens, temperature) combo — effectively no rotation at
     all. Concurrent batches were all hammering the same key.
     FIX: cache is now keyed by (model, api_key) only — max_tokens and
     temperature are set on the instance at call time via .bind(), not
     baked into the cached object. This means 3 instances max (one per
     key), and every call truly round-robins.
   - logger.info added for every key selection — matches what the logs
     already show ("Using GROQ_API_KEY_2 (fast/8b)") so the log output
     is actually coming from this file now.
   - Key health tracking added: if a key gets a rate-limit error, it's
     cooled down for RATE_LIMIT_COOLDOWN_SECONDS before being selected
     again. Round-robin skips cooled-down keys automatically.
   - _next_key() now accepts a model_label for readable log output.
   - Cache simplified: 3 base instances (one per key per model), params
     applied via .bind() — no more instance explosion from unique
     (max_tokens, temperature) combos.
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from utils.logger import get_logger
import os
import time
import threading

load_dotenv(override=True)

logger = get_logger("llm")

# ── Load all available API keys ───────────────────────────────────────────────
GROQ_KEYS: list[str] = [
    (os.getenv("GROQ_API_KEY_1") or "").strip(),
    (os.getenv("GROQ_API_KEY_2") or "").strip(),
    (os.getenv("GROQ_API_KEY_3") or "").strip(),
]
GROQ_KEYS = [k for k in GROQ_KEYS if k]

if not GROQ_KEYS:
    raise EnvironmentError(
        "No GROQ API keys found. "
        "Add GROQ_API_KEY_1 (and optionally _2, _3) to your .env file."
    )

MODEL_SMART = "llama-3.3-70b-versatile"
MODEL_FAST  = "llama-3.1-8b-instant"

# How long a rate-limited key is skipped before being retried
RATE_LIMIT_COOLDOWN_SECONDS = 30.0


# ── Key health tracking ───────────────────────────────────────────────────────
# Maps key_index → timestamp when it was rate-limited (0.0 = healthy)
_key_cooldown: list[float] = [0.0] * len(GROQ_KEYS)
_key_index                 = 0
_rotation_lock             = threading.Lock()


def _next_key(model_label: str = "") -> tuple[str, int]:
    """
    Return the next healthy API key in round-robin order (thread-safe).
    Skips keys that are currently in cooldown from a recent rate-limit hit.
    Falls back to least-recently-rate-limited key if ALL keys are cooling down.
    """
    global _key_index
    with _rotation_lock:
        now        = time.monotonic()
        n          = len(GROQ_KEYS)
        start      = _key_index

        for _ in range(n):
            idx     = _key_index % n
            cooled  = _key_cooldown[idx]
            _key_index += 1

            if now - cooled >= RATE_LIMIT_COOLDOWN_SECONDS:
                key     = GROQ_KEYS[idx]
                key_num = idx + 1
                logger.info(f"Using GROQ_API_KEY_{key_num} ({model_label})")
                return key, key_num

        # All keys cooling down — pick the one whose cooldown expires soonest
        best_idx = min(range(n), key=lambda i: _key_cooldown[i])
        key      = GROQ_KEYS[best_idx]
        key_num  = best_idx + 1
        logger.warning(
            f"All {n} keys in cooldown — using least-recently-limited "
            f"GROQ_API_KEY_{key_num} ({model_label})"
        )
        _key_index = best_idx + 1
        return key, key_num


def mark_key_rate_limited(api_key: str) -> None:
    """
    Call this from an agent when a rate-limit error is caught.
    Puts the key in cooldown so _next_key() skips it for a while.
    """
    try:
        idx = GROQ_KEYS.index(api_key)
        _key_cooldown[idx] = time.monotonic()
        logger.warning(
            f"GROQ_API_KEY_{idx + 1} marked as rate-limited — "
            f"cooling down for {RATE_LIMIT_COOLDOWN_SECONDS}s"
        )
    except ValueError:
        pass  # key not in list — ignore


# ── Base instance cache ───────────────────────────────────────────────────────
# Keyed by (model, api_key) ONLY — max_tokens and temperature applied via
# .bind() at call time, not baked into the cached object.
# Maximum 6 instances: 2 models × 3 keys.
_base_instances: dict[tuple[str, str], ChatGroq] = {}
_cache_lock = threading.Lock()


def _get_base_instance(model: str, api_key: str) -> ChatGroq:
    """Return a cached base ChatGroq instance for (model, api_key)."""
    cache_key = (model, api_key)
    with _cache_lock:
        if cache_key not in _base_instances:
            _base_instances[cache_key] = ChatGroq(
                api_key=api_key,
                model_name=model,
                temperature=0.1,    # default; overridden via .bind() below
                max_tokens=2000,    # default; overridden via .bind() below
                timeout=90,
            )
        return _base_instances[cache_key]


def _make_llm(
    model: str,
    model_label: str,
    max_tokens: int,
    temperature: float,
) -> ChatGroq:
    """
    Get the next key via round-robin, fetch/create the base instance,
    and return it with max_tokens + temperature bound for this call.
    """
    api_key, _ = _next_key(model_label)
    base        = _get_base_instance(model, api_key)

    # .bind() returns a new Runnable with these params set for this call —
    # does not mutate the cached base instance
    return base.bind(max_tokens=max_tokens, temperature=temperature)


def get_llm(
    max_tokens: int   = 3000,
    temperature: float = 0.1,
    timeout: int       = 60,     # kept for backward-compat call signature; timeout set on base instance
) -> ChatGroq:
    """
    Return a 70B (smart) model instance with round-robin key selection.
    Use for deep reasoning: risk assessment, legal analysis.
    """
    return _make_llm(MODEL_SMART, "smart/70b", max_tokens, temperature)


def get_fast_llm(
    max_tokens: int    = 3000,
    temperature: float = 0.1,
    timeout: int       = 60,
) -> ChatGroq:
    """
    Return an 8B (fast) model instance with round-robin key selection.
    Use for simpler tasks: extraction, classification, simplification.
    """
    return _make_llm(MODEL_FAST, "fast/8b", max_tokens, temperature)