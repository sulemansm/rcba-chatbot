"""
ai_service.py — Groq API integration (OpenAI-compatible)
RCBA-aware assistant with S3 knowledge base + logging + email alerts
"""

import os
import logging
import time
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from email_service import send_email  # 🔥 EMAIL ALERTS

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="/opt/chatbot/app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

# ── S3 config ─────────────────────────────────────────────────────────────────
KNOWLEDGE_S3_KEY = "knowledge/rcba_knowledge.txt"

# ── Cache ─────────────────────────────────────────────────────────────────────
_knowledge_cache: str | None = None

# ── Email cooldown (avoid spam) ───────────────────────────────────────────────
_last_error_time = 0


# ── S3 loader ─────────────────────────────────────────────────────────────────
def load_knowledge_from_s3() -> str:
    bucket = os.environ.get("S3_BUCKET", "")
    region = os.environ.get("AWS_REGION", "ap-south-1")

    if not bucket:
        logger.warning("S3_BUCKET not set")
        return "[Knowledge base not configured]"

    try:
        s3 = boto3.client("s3", region_name=region)
        response = s3.get_object(Bucket=bucket, Key=KNOWLEDGE_S3_KEY)
        return response["Body"].read().decode("utf-8")

    except Exception as e:
        logger.error(f"S3 error: {str(e)}")
        return f"[S3 error: {str(e)}]"


def get_knowledge() -> str:
    global _knowledge_cache
    if _knowledge_cache is None:
        _knowledge_cache = load_knowledge_from_s3()
    return _knowledge_cache


def reload_knowledge() -> tuple[bool, str]:
    global _knowledge_cache
    _knowledge_cache = None
    content = get_knowledge()

    if content.startswith("["):
        return False, content
    return True, f"Knowledge base reloaded ({len(content)} chars)"


# ── Prompt ────────────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    return f"""
You are the official AI assistant for RCBA.

Be helpful, friendly, and accurate.

--- KNOWLEDGE ---
{get_knowledge()}
--- END ---
"""


# ── Groq client ───────────────────────────────────────────────────────────────
def _get_client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )


# ── Email alert helper ────────────────────────────────────────────────────────
def send_error_email(error_msg: str, user_message: str):
    global _last_error_time

    # Avoid spam: max 1 email per minute
    if time.time() - _last_error_time < 60:
        return

    try:
        send_email(
            subject="🚨 RCBA Chatbot Error",
            body=f"""
Error occurred in chatbot:

Error: {error_msg}

User message: {user_message}

Time: {datetime.now()}
"""
        )
        _last_error_time = time.time()

    except Exception as e:
        logger.error(f"Email send failed: {str(e)}")


# ── Main function ─────────────────────────────────────────────────────────────
def get_ai_response(user_message: str, history: list[dict]) -> tuple[str, str | None]:
    try:
        client = _get_client()

        messages = [{"role": "system", "content": _build_system_prompt()}]
        messages += history[-8:]
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=768,
            temperature=0.6,
        )

        reply = response.choices[0].message.content.strip()
        return reply, None

    except ValueError as e:
        logger.error(str(e))
        send_error_email(str(e), user_message)
        return "⚠️ Configuration issue. Please try again later.", None

    except RateLimitError:
        logger.error("Rate limit hit")
        return "⚠️ Too many requests right now. Please try again shortly.", None

    except APIConnectionError:
        logger.error("Connection failed")
        send_error_email("API connection failed", user_message)
        return "⚠️ Unable to connect to AI service.", None

    except APIError as e:
        error_msg = f"AI API error: {e.message}"
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "⚠️ I'm having trouble responding right now. Please try again later.", None

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "⚠️ Something went wrong. Please try again.", None