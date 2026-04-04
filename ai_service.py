"""
ai_service.py — Groq API integration (OpenAI-compatible)
RCBA-aware assistant: loads knowledge base dynamically from S3.

Knowledge file location in S3:
    s3://<S3_BUCKET>/knowledge/rcba_knowledge.txt

To update RCBA info: just upload a new version of that file to S3.
No code changes or redeployment needed.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)

# ── Model ──────────────────────────────────────────────────────────────────────
# llama3-8b-8192: fast, free-tier, 8k context — ideal for a knowledge-base chatbot
MODEL = "llama3-8b-8192"

# S3 key where the knowledge base lives
KNOWLEDGE_S3_KEY = "knowledge/rcba_knowledge.txt"

# ── In-memory cache ────────────────────────────────────────────────────────────
# Loaded once per process start. Restart the service to pick up S3 changes,
# or call reload_knowledge() for hot-reload via the admin panel in app.py.
_knowledge_cache: str | None = None


# ── S3 loader ──────────────────────────────────────────────────────────────────
def load_knowledge_from_s3() -> str:
    """
    Fetches rcba_knowledge.txt from S3.
    Returns the file content as a string, or a fallback message on failure.
    """
    bucket = os.environ.get("S3_BUCKET", "")
    region = os.environ.get("AWS_REGION", "ap-south-1")

    if not bucket:
        logger.warning("S3_BUCKET not set — knowledge base unavailable.")
        return "[Knowledge base not configured. Set S3_BUCKET environment variable.]"

    try:
        s3 = boto3.client("s3", region_name=region)
        response = s3.get_object(Bucket=bucket, Key=KNOWLEDGE_S3_KEY)
        content = response["Body"].read().decode("utf-8")
        logger.info("Knowledge base loaded from s3://%s/%s (%d chars)", bucket, KNOWLEDGE_S3_KEY, len(content))
        return content

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchKey":
            msg = (
                f"Knowledge file not found at s3://{bucket}/{KNOWLEDGE_S3_KEY}. "
                "Please upload rcba_knowledge.txt to S3."
            )
        else:
            msg = f"S3 error ({code}): {e.response['Error']['Message']}"
        logger.error(msg)
        return f"[{msg}]"

    except BotoCoreError as e:
        msg = f"S3 connection error: {str(e)}"
        logger.error(msg)
        return f"[{msg}]"


def get_knowledge() -> str:
    """Returns cached knowledge, loading from S3 on first call."""
    global _knowledge_cache
    if _knowledge_cache is None:
        _knowledge_cache = load_knowledge_from_s3()
    return _knowledge_cache


def reload_knowledge() -> tuple[bool, str]:
    """Force-reloads the knowledge base from S3 (clears cache). Returns (success, message)."""
    global _knowledge_cache
    _knowledge_cache = None
    content = get_knowledge()
    if content.startswith("["):
        return False, content  # error message wrapped in brackets
    return True, f"Knowledge base reloaded successfully ({len(content)} characters)."


# ── System prompt builder ──────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    knowledge = get_knowledge()
    return f"""You are the official AI assistant for RCBA — the Rotaract Club of Bombay Airport.
Your job is to answer questions about RCBA clearly, warmly, and accurately using the
knowledge provided below. You speak like a friendly, enthusiastic club member.

When someone asks about RCBA's projects, events, how to join, how to donate, or
contact details — answer from the knowledge base. If something isn't covered in
the knowledge base, say so honestly and direct them to the website
(https://www.rcbombayairport.org) or the contact email (rc.bombayairport3141@gmail.com).

For general questions unrelated to RCBA, answer helpfully but briefly,
then gently bring the conversation back to RCBA if relevant.

Always be concise, warm, and enthusiastic — just like the RCBA spirit: Act For Impact! 🌟

--- RCBA KNOWLEDGE BASE ---
{knowledge}
--- END OF KNOWLEDGE BASE ---
"""


# ── Groq client ────────────────────────────────────────────────────────────────
def _get_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


# ── Main function ──────────────────────────────────────────────────────────────
def get_ai_response(user_message: str, history: list[dict]) -> tuple[str, str | None]:
    """
    Returns (reply_text, error_message).
    error_message is None on success.
    history = [{"role": "user"|"assistant", "content": "..."}]
    """
    try:
        client = _get_client()

        messages = [{"role": "system", "content": _build_system_prompt()}]
        # Keep last 8 turns to stay comfortably within the 8k context window
        messages += history[-8:]
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=768,   # generous but avoids burning free-tier tokens
            temperature=0.6,  # lower = more factual, fewer hallucinations
        )

        reply = response.choices[0].message.content.strip()
        return reply, None

    except ValueError as e:
        return "", str(e)
    except RateLimitError:
        return "", "Rate limit reached. Please wait a moment and try again."
    except APIConnectionError:
        return "", "Could not connect to the AI service. Check your internet connection."
    except APIError as e:
        return "", f"AI API error: {e.message}"
    except Exception as e:
        return "", f"Unexpected error: {str(e)}"
