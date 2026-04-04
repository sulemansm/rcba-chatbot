"""
app.py — Main Streamlit UI
Production-ready AI chatbot with lead capture.
"""

import streamlit as st
from datetime import datetime

from ai_service import get_ai_response, reload_knowledge
from s3_service import upload_lead_to_s3
from email_service import send_lead_email

# Sidebar state
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Assistant",
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
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Mono:wght@400;700&display=swap');

/* ── Reset & Base ── */
html, body, [data-testid="stApp"] {
    font-family: 'DM Sans', sans-serif;
    background: #0d0d0f;
    color: #e8e6e0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #111114;
    border-right: 1px solid #222228;
}
[data-testid="stSidebar"] .block-container { padding-top: 2rem; }

/* ── Main container ── */
.block-container {
    padding: 2rem 2.5rem;
    max-width: 860px;
}

/* ── Chat bubbles ── */
.chat-wrapper { display: flex; flex-direction: column; gap: 1.2rem; margin-bottom: 1.5rem; }

.msg-row { display: flex; align-items: flex-start; gap: 0.75rem; animation: fadeUp 0.25s ease; }
.msg-row.user  { flex-direction: row-reverse; }

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

.avatar {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0; font-weight: 700;
    font-family: 'Space Mono', monospace;
}
.avatar.bot  { background: #1a1a2e; border: 1px solid #30305a; color: #7c7cf0; }
.avatar.user { background: #1a2e1a; border: 1px solid #305a30; color: #7cf07c; }

.bubble {
    padding: 0.85rem 1.15rem;
    border-radius: 16px;
    max-width: 78%;
    font-size: 0.92rem;
    line-height: 1.65;
    word-break: break-word;
}
.bubble.bot {
    background: #17171d;
    border: 1px solid #28282f;
    border-top-left-radius: 4px;
    color: #ddd9d0;
}
.bubble.user {
    background: #0f2011;
    border: 1px solid #1c3e1c;
    border-top-right-radius: 4px;
    color: #c8f0c8;
    text-align: right;
}

/* ── Timestamp ── */
.ts { font-size: 0.68rem; color: #555; margin-top: 0.3rem; font-family: 'Space Mono', monospace; }
.msg-row.user  .ts { text-align: right; }

/* ── Divider ── */
.section-divider {
    border: none;
    border-top: 1px solid #222228;
    margin: 1.5rem 0;
}

/* ── Lead form card ── */
.lead-card {
    background: #111114;
    border: 1px solid #222228;
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 0.5rem;
}
.lead-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7c7cf0;
    margin-bottom: 1rem;
}

/* ── Streamlit input overrides ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #0d0d0f !important;
    border: 1px solid #2a2a33 !important;
    border-radius: 10px !important;
    color: #e8e6e0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #7c7cf0 !important;
    box-shadow: 0 0 0 2px rgba(124,124,240,0.12) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: #7c7cf0;
    color: #fff;
    border: none;
    border-radius: 10px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.06em;
    padding: 0.55rem 1.25rem;
    transition: background 0.18s, transform 0.12s;
    cursor: pointer;
}
[data-testid="stButton"] > button:hover {
    background: #6060d8;
    transform: translateY(-1px);
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: #111114 !important;
    border: 1px solid #2a2a33 !important;
    border-radius: 12px !important;
    color: #e8e6e0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Success / Error ── */
[data-testid="stAlert"] { border-radius: 10px; }

/* ── Sidebar heading ── */
.sidebar-logo {
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: #7c7cf0;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
}
.sidebar-sub {
    font-size: 0.78rem;
    color: #555;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ── Session state initialisation ───────────────────────────────────────────────
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi there! 👋 I'm the RCBA AI Assistant — your guide to the Rotaract Club of Bombay Airport. Ask me about our projects, events, how to join, donate, or anything else about RCBA! 🌟",
                "time": datetime.now().strftime("%H:%M"),
            }
        ]
    if "lead_submitted" not in st.session_state:
        st.session_state.lead_submitted = False


init_session()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🌟 RCBA Assistant</div>', unsafe_allow_html=True)
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
    if st.button("🔄 Reload knowledge base"):
        ok, msg = reload_knowledge()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

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
