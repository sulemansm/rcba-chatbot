"""
app.py — Main Streamlit UI
Production-ready AI chatbot with lead capture.
"""

import os

import streamlit as st
from datetime import datetime

from ai_service import get_ai_response, reload_knowledge
from s3_service import upload_lead_to_s3
from email_service import send_lead_email

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
# Sidebar state
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "show_admin_prompt" not in st.session_state:
    st.session_state.show_admin_prompt = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCBA ImpactBot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" if st.session_state.sidebar_open else "collapsed",
)

# Toggle button (top right)
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("☰"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>

/* Base */
html, body, [data-testid="stApp"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
    background: radial-gradient(circle at 20% 20%, #1c1c2a, #0b0b10 60%);
    color: #eaeaf0;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ───────────────── Glass Core ───────────────── */

/* Main container glass */
.block-container {
    max-width: 860px;
    padding-top: 2rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* Chat wrapper */
.chat-wrapper {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
    margin-bottom: 1rem;
}

/* Message rows */
.msg-row {
    display: flex;
    gap: 10px;
    animation: fadeIn 0.25s ease;
}

.msg-row.user {
    flex-direction: row-reverse;
}

/* Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Avatar */
.avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
}

/* Bubbles */
.bubble {
    padding: 12px 16px;
    border-radius: 18px;
    max-width: 75%;
    font-size: 0.95rem;
    line-height: 1.6;
}

/* Bot bubble */
.bubble.bot {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
}

/* User bubble */
.bubble.user {
    background: linear-gradient(135deg, rgba(124,124,240,0.35), rgba(124,124,240,0.15));
    backdrop-filter: blur(20px);
    border: 1px solid rgba(124,124,240,0.35);
}

/* Timestamp */
.ts {
    font-size: 0.65rem;
    opacity: 0.45;
    margin-top: 4px;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: rgba(255,255,255,0.06) !important;
    backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    color: #fff !important;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    background: rgba(255,255,255,0.06) !important;
    backdrop-filter: blur(20px);
    border-radius: 16px !important;
}

/* Buttons */
[data-testid="stButton"] button {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(14px);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.08);
    transition: 0.2s;
}

[data-testid="stButton"] button:hover {
    background: rgba(255,255,255,0.18);
    transform: translateY(-1px);
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 1.5rem 0;
}

/* Sidebar text */
.sidebar-logo {
    font-size: 1.05rem;
    font-weight: 600;
}

.sidebar-sub {
    font-size: 0.75rem;
    opacity: 0.5;
}

</style>
""", unsafe_allow_html=True)


# ── Session state initialisation ───────────────────────────────────────────────
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi there! 👋 I'm the RCBA ImpactBot — your guide to the Rotaract Club of Bombay Airport. Ask me about our projects, events, how to join, or anything else about RCBA! 🌟",
                "time": datetime.now().strftime("%H:%M"),
            }
        ]
    if "lead_submitted" not in st.session_state:
        st.session_state.lead_submitted = False


init_session()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">RCBA ImpactBot 🥰</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Rotaract Club of Bombay Airport · Act For Impact</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Stats
    total = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("Messages sent", total)

    st.markdown("---")

    # Clear chat
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat cleared. How can I help you?",
                "time": datetime.now().strftime("%H:%M"),
            }
        ]
        st.rerun()

    # Reload knowledge base from S3
        # Reload button
    if st.button("🔄 Reload knowledge base"):
        st.session_state.show_admin_prompt = True

    # Password prompt
    if st.session_state.show_admin_prompt:
        password = st.text_input("Enter admin password", type="password")

        if st.button("Submit"):
            if password == ADMIN_PASSWORD:
                st.session_state.show_admin_prompt = False
                ok, msg = reload_knowledge()

                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.error("Incorrect password ❌")

    st.markdown("---")

    # ── Lead capture form ──────────────────────────────────────────────────────
    st.markdown('<div class="lead-title">📋 Get in Touch</div>', unsafe_allow_html=True)

    if st.session_state.lead_submitted:
        st.success("✅ Thanks! We'll be in touch soon.")
    else:
        with st.form("lead_form", clear_on_submit=True):
            name  = st.text_input("Name *", placeholder="Jane Smith")
            email = st.text_input("Email *", placeholder="jane@example.com")
            phone = st.text_input("Phone", placeholder="+91 98765 43210")

            submitted = st.form_submit_button("Submit →", use_container_width=True)

            if submitted:
                # Validation
                if not name.strip():
                    st.error("Name is required.")
                elif not email.strip() or "@" not in email:
                    st.error("A valid email is required.")
                else:
                    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    lead_data = {
                        "name":      name.strip(),
                        "email":     email.strip(),
                        "phone":     phone.strip() or "—",
                        "timestamp": timestamp,
                    }

                    # Upload to S3
                    s3_ok, s3_msg = upload_lead_to_s3(lead_data)
                    if not s3_ok:
                        st.warning(f"S3: {s3_msg}")

                    # Send email
                    mail_ok, mail_msg = send_lead_email(lead_data)
                    if not mail_ok:
                        st.warning(f"Email: {mail_msg}")

                    st.session_state.lead_submitted = True
                    st.rerun()


# ── Main chat area ─────────────────────────────────────────────────────────────
st.markdown("## 🌟 RCBA AI Assistant")
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# Render history
chat_html = '<div class="chat-wrapper">'
for msg in st.session_state.messages:
    role     = msg["role"]
    content  = msg["content"]
    ts       = msg.get("time", "")
    css_role = "bot" if role == "assistant" else "user"
    icon     = "AI" if role == "assistant" else "You"

    chat_html += f"""
    <div class="msg-row {css_role}">
        <div class="avatar {css_role}">{icon[0]}</div>
        <div>
            <div class="bubble {css_role}">{content}</div>
            <div class="ts">{ts}</div>
        </div>
    </div>"""

chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ── Chat input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me about RCBA — projects, events, how to join…"):
    now = datetime.now().strftime("%H:%M")

    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})

    # Get AI response
    with st.spinner("Thinking…"):
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]  # exclude the message just added
        ]
        reply, err = get_ai_response(prompt, history)

    if err:
        reply = f"⚠️ {err}"

    st.session_state.messages.append({"role": "assistant", "content": reply, "time": now})
    st.rerun()
