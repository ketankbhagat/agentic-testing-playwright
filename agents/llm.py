"""Shared LLM + environment setup for every agent node."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# This project's .env first, then the ai-test-architect project's .env (where the
# Anthropic key lives). load_dotenv never overrides a variable that is already set.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / "ai-test-architect" / ".env")

# claude-sonnet-4-20250514 (the original spec) is retired and returns 404.
MODEL = os.environ.get("QA_AGENT_MODEL", "claude-sonnet-5")


def get_llm(max_tokens: int = 8000) -> ChatAnthropic:
    # No temperature: Claude 5 models reject it ("temperature is deprecated for this model")
    return ChatAnthropic(model=MODEL, max_tokens=max_tokens)


def text_of(response) -> str:
    """Flatten a chat response to plain text (content may be a list of blocks)."""
    content = response.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)


def strip_fences(text: str) -> str:
    """Remove a leading/trailing markdown code fence if the model added one."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
