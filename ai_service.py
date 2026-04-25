"""
ai_service.py — Groq API with expressive RAG-only answering
Youth-energy tone. Grounded in the knowledge base but warm, vivid, empathetic.
"""

import os
import logging
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="/opt/chatbot/app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── ENV ───────────────────────────────────────────────────────────────────────
MODEL      = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

KNOWLEDGE_S3_KEY = "knowledge/rcba_knowledge.txt"

_knowledge_cache = None
_last_error_time = 0


# ── EMAIL ALERT ───────────────────────────────────────────────────────────────
def send_error_email(error_msg: str, user_message: str):
    global _last_error_time

    # Avoid spam — max 1 email per minute
    if time.time() - _last_error_time < 60:
        return

    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("Email credentials not set")
        return

    try:
        msg = MIMEText(f"""
\U0001f6a8 RCBA Chatbot Error

Error:
{error_msg}

User message:
{user_message}

Time:
{datetime.now()}
""")
        msg["Subject"] = "\U0001f6a8 RCBA Chatbot Error"
        msg["From"]    = EMAIL_USER
        msg["To"]      = EMAIL_USER

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        _last_error_time = time.time()

    except Exception as e:
        logger.error(f"Email failed: {str(e)}")


# ── S3 KNOWLEDGE ──────────────────────────────────────────────────────────────
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
    return True, "Knowledge base reloaded successfully \u2705"


# ── SYSTEM PROMPT (RAG + youth-energy personality) ────────────────────────────
def _build_system_prompt():
    knowledge = get_knowledge()
    return f"""You are RCBA ImpactBot — the vibrant, warm-hearted AI voice of the Rotaract Club of Bombay Airport (RCBA). You speak like a passionate, enthusiastic Rotaractor who genuinely cares about people and the community.

YOUR PERSONALITY:
- Energetic, warm, and youth-forward — like a friend who's super excited about the club
- Empathetic and encouraging — make people feel welcome and inspired
- Conversational and natural — not robotic or stiff
- Use light, positive energy in every response — this is a youth movement!
- Occasional use of exclamation marks and emojis is great, but keep it tasteful
- When someone seems interested in joining, be genuinely encouraging
- When someone asks about a project, paint a vivid picture of the impact — bring it to life!

KNOWLEDGE BASE RULES (non-negotiable):
1. Every fact, name, date, number, and link MUST come from the KNOWLEDGE BASE below
2. You may elaborate, explain context, and use expressive language — but never invent new facts
3. If something isn't in the knowledge base, say warmly: "That's a great question! I don't have that info handy — but you can reach our team at rc.bombayairport3141@gmail.com or visit rcbombayairport.org \U0001f60a"
4. Never answer general knowledge questions unrelated to RCBA

HOW TO EXPAND KNOWLEDGE BASE ANSWERS:
- For projects: describe the human impact, who benefits, the spirit behind it — make it feel real
- For events: convey the excitement and community energy
- For joining: be genuinely encouraging and highlight what makes RCBA special
- For contact details: give them exactly as listed, and add a warm closing nudge
- Use bullet points naturally when listing multiple things
- Keep responses focused — enthusiastic but not overwhelming

KNOWLEDGE BASE:
{knowledge}

Remember: You're not just answering questions — you're representing a movement. Make every interaction count!
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
        client   = _get_client()
        messages = [{"role": "system", "content": _build_system_prompt()}]
        messages += history[-6:]
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=640,
            temperature=0.55,  # warm & expressive, still grounded
        )

        return response.choices[0].message.content.strip(), None

    except ValueError as e:
        logger.error(str(e))
        send_error_email(str(e), user_message)
        return "Oops, looks like there's a configuration hiccup. Please try again in a moment!", None

    except RateLimitError:
        logger.error("Rate limit hit")
        return "We're getting a lot of love right now! Try again in a few seconds \U0001f604", None

    except APIConnectionError:
        logger.error("Connection failed")
        send_error_email("API connection failed", user_message)
        return "Hmm, can't reach the AI service right now. Give it a moment and try again!", None

    except APIError as e:
        error_msg = f"AI API error: {e.message}"
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "Something went sideways on our end. Try again shortly!", None

    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        send_error_email(error_msg, user_message)
        return "Something unexpected happened. Our team has been notified!", None