"""
ai_service.py — Groq API integration with strict RAG-only answering
Only answers based on the knowledge base provided. Will not hallucinate or
answer questions outside the scope of the RCBA knowledge base.
"""

import os
import logging
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import boto3
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="/opt/chatbot/app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── ENV ───────────────────────────────────────────────────────────────────────
MODEL = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

KNOWLEDGE_S3_KEY = "knowledge/rcba_knowledge.txt"

_knowledge_cache = None
_last_error_time = 0


# ── EMAIL FUNCTION (BUILT-IN) ─────────────────────────────────────────────────
def send_error_email(error_msg: str, user_message: str):
    global _last_error_time

    if time.time() - _last_error_time < 60:
        return

    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("Email credentials not set")
        return

    try:
        msg = MIMEText(f"""
🚨 RCBA Chatbot Error

Error:
{error_msg}

User message:
{user_message}

Time:
{datetime.now()}
""")
        msg["Subject"] = "🚨 RCBA Chatbot Error"
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_USER

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        _last_error_time = time.time()

    except Exception as e:
        logger.error(f"Email failed: {str(e)}")


# ── S3 ────────────────────────────────────────────────────────────────────────
def load_knowledge_from_s3():
    bucket = os.getenv("S3_BUCKET", "")
    region = os.getenv("AWS_REGION", "ap-south-1")

    try:
        s3 = boto3.client("s3", region_name=region)
        response = s3.get_object(Bucket=bucket, Key=KNOWLEDGE_S3_KEY)
        return response["Body"].read().decode("utf-8")

    except Exception as e:
        logger.error(f"S3 error: {str(e)}")
        return f"[S3 error: {str(e)}]"


def get_knowledge():
    global _knowledge_cache
    if _knowledge_cache is None:
        _knowledge_cache = load_knowledge_from_s3()
    return _knowledge_cache


def reload_knowledge():
    global _knowledge_cache
    _knowledge_cache = None
    content = get_knowledge()
    if content.startswith("["):
        return False, content
    return True, "Knowledge base reloaded successfully ✅"


# ── STRICT RAG SYSTEM PROMPT ──────────────────────────────────────────────────
def _build_system_prompt():
    knowledge = get_knowledge()
    return f"""You are RCBA ImpactBot, the official AI assistant for the Rotaract Club of Bombay Airport (RCBA).

═══ CRITICAL RULES — FOLLOW STRICTLY ═══

1. KNOWLEDGE BASE ONLY: Answer EXCLUSIVELY using the KNOWLEDGE BASE provided below.
   Never make up, guess, or infer any facts not stated there.

2. OUT-OF-SCOPE QUESTIONS: If the question cannot be answered from the knowledge base,
   reply with exactly:
   "I don't have information on that. Please reach out to us at rc.bombayairport3141@gmail.com or visit rcbombayairport.org for more details! 😊"

3. NO GENERAL KNOWLEDGE: Do not answer questions about history, science, news,
   other organisations, or anything unrelated to RCBA.

4. TONE: Warm, friendly, enthusiastic — this is a youth community club.
   Use emojis naturally but sparingly.

5. FORMAT: Be concise. Use bullet points when listing multiple items.
   Never write walls of text.

6. ACCURACY: Quote dates, names, phone numbers, and links exactly as they appear
   in the knowledge base — never paraphrase or guess.

═══ KNOWLEDGE BASE ═══
{knowledge}
═══════════════════════

Remember: If the answer isn't in the knowledge base above, say you don't know and redirect to contact details.
"""


# ── GROQ CLIENT ───────────────────────────────────────────────────────────────
def _get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )


# ── MAIN RESPONSE FUNCTION ────────────────────────────────────────────────────
def get_ai_response(user_message, history):
    try:
        client = _get_client()

        messages = [{"role": "system", "content": _build_system_prompt()}]
        # Keep last 6 turns only — conserves tokens for the knowledge base
        messages += history[-6:]
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.1,   # Very low — factual/grounded RAG responses only
        )

        return response.choices[0].message.content.strip(), None

    except ValueError as e:
        logger.error(str(e))
        send_error_email(str(e), user_message)
        return "⚠️ Configuration issue. Please try again later.", None

    except RateLimitError:
        logger.error("Rate limit hit")
        return "⚠️ Too many requests. Try again shortly.", None

    except APIConnectionError:
        logger.error("Connection failed")
        send_error_email("API connection failed", user_message)
        return "⚠️ Unable to connect to AI service.", None

    except APIError as e:
        error_msg = f"AI API error: {e.message}"
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "⚠️ AI service issue. Please try again.", None

    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "⚠️ Something went wrong. Please try again.", None