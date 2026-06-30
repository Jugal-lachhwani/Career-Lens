"""
LLM factory utilities.

Provides a single place to access NVIDIA NIM
OpenAI-compatible endpoints using environment variables.
"""

import os
import importlib
from dotenv import load_dotenv

load_dotenv()


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "nvidia_nim").strip().lower()


def _get_nim_api_key() -> str | None:
    """Return NVIDIA NIM key from supported env var names."""
    return (
        os.getenv("NVIDIA_NIM_API_KEY")
        or os.getenv("NVIDIA_API_KEY")
        or os.getenv("NIM_API_KEY")
    )


def get_json_llm(temperature: float = 0.2):
    """
    Return an LLM configured for structured/JSON-heavy outputs.

    Env vars:
    - LLM_PROVIDER=nvidia_nim
    - NVIDIA_NIM_API_KEY=<required for nvidia_nim>
    - NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
    - NVIDIA_NIM_MODEL=meta/llama-3.1-70b-instruct
    """
    provider = _get_provider()

    if provider != "nvidia_nim":
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Ollama support has been removed. "
            "Use LLM_PROVIDER='nvidia_nim'."
        )

    try:
        chatopenai_module = importlib.import_module("langchain_openai")
        ChatOpenAI = getattr(chatopenai_module, "ChatOpenAI")
    except ImportError as exc:
        raise ImportError(
            "langchain-openai is required for NVIDIA NIM support. "
            "Install it with: pip install langchain-openai"
        ) from exc

    api_key = _get_nim_api_key()
    if not api_key:
        raise ValueError(
            "NVIDIA NIM API key is required. Set NVIDIA_NIM_API_KEY (or NVIDIA_API_KEY)."
        )

    base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.1-70b-instruct")

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
    )


def get_text_llm(temperature: float = 0.2):
    """
    Return an LLM for conversational/free-form text responses.
    """
    return get_json_llm(temperature=temperature)
