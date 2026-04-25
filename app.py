"""
app.py — RCBA ImpactBot
Themed to match release.rcbombayairport.in
RAG-only: all answers grounded in the knowledge base.
"""

import os
import streamlit as st
from datetime import datetime

from ai_service import get_ai_response, reload_knowledge
from s3_service import upload_lead_to_s3
from email_service import send_lead_email

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

for key, val in {
    "sidebar_open": True,
    "admin_authenticated": False,
    "show_admin_prompt": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(
    page_title="RCBA ImpactBot",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded" if st.session_state.sidebar_open else "collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Syne:wght@700;800&display=swap');

:root {
    --orange:       #f97316;
    --orange-dim:   rgba(249,115,22,0.12);
    --orange-mid:   rgba(249,115,22,0.25);
    --teal:         #22d3ee;
    --teal-dim:     rgba(34,211,238,0.10);
    --purple:       #a855f7;
    --bg:           #0d0d10;
    --surface:      rgba(255,255,255,0.04);
    --border:       rgba(255,255,255,0.08);
    --border-light: rgba(255,255,255,0.05);
    --text:         rgba(255,255,255,0.88);
    --muted:        rgba(255,255,255,0.38);
    --font-body:    'Inter', sans-serif;
    --font-display: 'Syne', sans-serif;
}

html, body, [data-testid="stApp"] {
    font-family: var(--font-body);
    background: var(--bg);
    color: var(--text);
}

/* ── ambient blobs (behind everything) ── */
[data-testid="stApp"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse 340px 340px at -80px -80px, rgba(192,57,10,0.45), transparent 70%),
        radial-gradient(ellipse 260px 260px at 20% 90%, rgba(107,33,168,0.38), transparent 70%),
        radial-gradient(ellipse 240px 240px at 88% 12%, rgba(14,116,144,0.35), transparent 70%),
        radial-gradient(ellipse 200px 200px at 92% 80%, rgba(147,51,234,0.30), transparent 70%);
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.022) !important;
    border-right: 1px solid var(--border) !important;
    backdrop-filter: blur(12px);
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── Main container ── */
.block-container {
    padding: 1.5rem 2rem;
    max-width: 880px;
    position: relative; z-index: 1;
}

/* ── Sidebar brand block ── */
.sb-brand {
    padding: 1.25rem 1rem 1rem;
    border-bottom: 1px solid var(--border-light);
    margin-bottom: 0;
}
.sb-logo-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.sb-logo {
    width: 38px; height: 38px; border-radius: 50%;
    background: var(--surface); border: 1.5px solid rgba(255,255,255,0.12);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.sb-logo-ring {
    width: 23px; height: 23px; border-radius: 50%;
    border: 3px solid transparent;
    border-top-color: var(--orange); border-right-color: var(--teal);
    border-bottom-color: var(--purple); border-left-color: #4ade80;
}
.sb-club  { font-family: var(--font-display); font-size: 13px; font-weight: 800; color: #fff; line-height: 1.2; }
.sb-sub   { font-size: 9px; color: var(--orange); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }
.sb-pill  {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--teal-dim); border: 1px solid rgba(34,211,238,0.22);
    border-radius: 20px; padding: 3px 10px;
}
.sb-dot   { width: 6px; height: 6px; border-radius: 50%; background: var(--teal); }
.sb-pill-text { font-size: 9px; color: var(--teal); font-weight: 600; letter-spacing: 0.04em; }

/* ── Stats grid ── */
.sb-stats {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    padding: 14px 16px; border-bottom: 1px solid var(--border-light);
}
.stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 8px 10px;
}
.stat-label { font-size: 8.5px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1px; }
.stat-val   { font-family: var(--font-display); font-size: 20px; font-weight: 800; }
.orange { color: var(--orange); }
.teal   { color: var(--teal); }

/* ── Section heading ── */
.sb-section {
    font-size: 8.5px; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.1em; padding: 12px 16px 6px; display: block;
}

/* ── Form ── */
.sb-form-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 16px 10px;
}
.sb-form-title { font-family: var(--font-display); font-size: 12px; font-weight: 800; color: #fff; }
.sb-form-badge {
    font-size: 8px; padding: 2px 7px; border-radius: 20px;
    background: var(--orange-dim); border: 1px solid var(--orange-mid);
    color: var(--orange); font-weight: 600; letter-spacing: 0.05em;
}

/* ── Social ── */
.sb-social {
    display: flex; gap: 6px; padding: 0 16px 16px;
}
.soc-btn {
    flex: 1; padding: 5px 0; border-radius: 7px; text-align: center;
    background: var(--surface); border: 1px solid var(--border);
    font-size: 10px; color: var(--muted); cursor: pointer;
    text-decoration: none; display: block;
}
.soc-btn:hover { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.8); }

/* ── Streamlit input overrides ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important;
    color: rgba(255,255,255,0.8) !important;
    font-family: var(--font-body) !important;
    font-size: 11px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(249,115,22,0.5) !important;
    box-shadow: 0 0 0 2px rgba(249,115,22,0.08) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label {
    color: var(--muted) !important; font-size: 9px !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: var(--orange) !important;
    color: #fff !important; border: none !important;
    border-radius: 9px !important;
    font-family: var(--font-display) !important;
    font-weight: 800 !important; font-size: 11px !important;
    letter-spacing: 0.02em; padding: 0.5rem 1rem;
    transition: opacity 0.15s, transform 0.1s;
}
[data-testid="stButton"] > button:hover { opacity: 0.88; transform: translateY(-1px); }

[data-testid="stFormSubmitButton"] > button {
    background: var(--orange) !important;
    color: #fff !important; font-weight: 800 !important;
    width: 100% !important; border-radius: 9px !important;
    font-family: var(--font-display) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    color: rgba(255,255,255,0.85) !important;
    font-family: var(--font-body) !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(249,115,22,0.4) !important;
    box-shadow: 0 0 0 3px rgba(249,115,22,0.06) !important;
}

/* ── Chat header ── */
.chat-header {
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 14px; border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
}
.ch-logo {
    width: 42px; height: 42px; border-radius: 50%;
    background: var(--surface); border: 1.5px solid rgba(255,255,255,0.1);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ch-ring {
    width: 26px; height: 26px; border-radius: 50%;
    border: 3px solid transparent;
    border-top-color: var(--orange); border-right-color: var(--teal);
    border-bottom-color: var(--purple); border-left-color: #4ade80;
}
.ch-title { font-family: var(--font-display); font-size: 16px; font-weight: 800; color: #fff; margin: 0; }
.ch-sub   { font-size: 10px; color: var(--muted); margin: 0; }
.grad-text {
    background: linear-gradient(90deg, var(--teal), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.rag-badge {
    margin-left: auto; padding: 3px 10px;
    background: var(--orange-dim); border: 1px solid var(--orange-mid);
    border-radius: 20px; font-size: 9px; color: var(--orange);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
}

/* ── Chat bubbles ── */
.chat-wrapper { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.25rem; }
.msg-row { display: flex; align-items: flex-start; gap: 8px; animation: fadeUp 0.22s ease; }
.msg-row.user { flex-direction: row-reverse; }
@keyframes fadeUp { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }

.avatar {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; flex-shrink: 0;
    font-family: var(--font-display);
}
.avatar.bot  { background: var(--teal-dim); border: 1.5px solid rgba(34,211,238,0.28); color: var(--teal); }
.avatar.user { background: var(--orange-dim); border: 1.5px solid var(--orange-mid); color: var(--orange); }

.bubble { padding: 9px 13px; border-radius: 14px; max-width: 78%; font-size: 0.88rem; line-height: 1.68; word-break: break-word; }
.bubble.bot  { background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-top-left-radius: 4px; color: var(--text); }
.bubble.user { background: var(--orange-dim); border: 1px solid var(--orange-mid); border-top-right-radius: 4px; color: #fff; text-align: right; }

.ts { font-size: 0.65rem; color: var(--muted); margin-top: 3px; opacity: 0.7; }
.msg-row.user .ts { text-align: right; }

/* ── Metric ── */
[data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 0.5rem 0.75rem; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 8.5px !important; text-transform: uppercase; letter-spacing: 0.08em; }
[data-testid="stMetricValue"] { color: var(--orange) !important; font-family: var(--font-display) !important; font-size: 1.4rem !important; }

/* ── Alert ── */
[data-testid="stAlert"] { border-radius: 10px; }

/* ── Divider ── */
hr { border: none; border-top: 1px solid var(--border-light); margin: 0.75rem 0; }
</style>
""", unsafe_allow_html=True)


def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Jai Rotaract! 🌀 I'm RCBA ImpactBot — your guide to the Rotaract Club of Bombay Airport.\n\nI answer only from our official knowledge base, so you'll always get accurate info. Ask me about projects, events, how to join, or anything RCBA!",
                "time": datetime.now().strftime("%H:%M"),
            }
        ]
    if "lead_submitted" not in st.session_state:
        st.session_state.lead_submitted = False


init_session()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # Brand
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-logo-row">
            <div class="sb-logo"><div class="sb-logo-ring"></div></div>
            <div>
                <div class="sb-club">Rotaract Club</div>
                <div class="sb-sub">Bombay Airport</div>
            </div>
        </div>
        <div class="sb-pill">
            <div class="sb-dot"></div>
            <span class="sb-pill-text">Live · Knowledge-grounded</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(f"""
    <div class="sb-stats">
        <div class="stat-card">
            <div class="stat-label">Messages</div>
            <div class="stat-val orange">{msg_count}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Projects</div>
            <div class="stat-val teal">21</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Actions
    st.markdown('<span class="sb-section">Actions</span>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Reload KB"):
            st.session_state.show_admin_prompt = True
    with col2:
        if st.button("✕ Clear"):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared! How can I help you learn about RCBA?",
                    "time": datetime.now().strftime("%H:%M"),
                }
            ]
            st.rerun()

    if st.session_state.show_admin_prompt:
        pwd = st.text_input("Admin password", type="password", key="admin_pwd")
        if st.button("Confirm", key="admin_confirm"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.show_admin_prompt = False
                ok, msg = reload_knowledge()
                st.success(msg) if ok else st.error(msg)
            else:
                st.error("Incorrect password")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Get in touch form
    st.markdown("""
    <div class="sb-form-header">
        <span class="sb-form-title">Get in touch</span>
        <span class="sb-form-badge">FREE</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.lead_submitted:
        st.success("Thanks! We'll be in touch soon.")
    else:
        with st.form("lead_form", clear_on_submit=True):
            name  = st.text_input("Name *", placeholder="Jane Smith")
            email = st.text_input("Email *", placeholder="jane@example.com")
            phone = st.text_input("Phone", placeholder="+91 98765 43210")
            submitted = st.form_submit_button("+ Join the Movement", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.error("Name is required.")
                elif not email.strip() or "@" not in email:
                    st.error("A valid email is required.")
                else:
                    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    lead = {"name": name.strip(), "email": email.strip(), "phone": phone.strip() or "—", "timestamp": ts}
                    s3_ok, s3_msg = upload_lead_to_s3(lead)
                    if not s3_ok: st.warning(f"S3: {s3_msg}")
                    mail_ok, mail_msg = send_lead_email(lead)
                    if not mail_ok: st.warning(f"Email: {mail_msg}")
                    st.session_state.lead_submitted = True
                    st.rerun()

    # Social links
    st.markdown("""
    <hr>
    <span class="sb-section" style="padding-left:0;display:block;margin-bottom:8px;">Find us online</span>
    <div class="sb-social">
        <a class="soc-btn" href="https://www.instagram.com/rc_bombayairport/" target="_blank">IG</a>
        <a class="soc-btn" href="https://www.linkedin.com/in/rotaract-club-of-bombay-airport-6a35621a7/" target="_blank">LI</a>
        <a class="soc-btn" href="https://www.facebook.com/RCBombayAirport/" target="_blank">FB</a>
        <a class="soc-btn" href="https://www.rcbombayairport.org" target="_blank">WEB</a>
    </div>
    """, unsafe_allow_html=True)


# ── MAIN CHAT ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="chat-header">
    <div class="ch-logo"><div class="ch-ring"></div></div>
    <div>
        <p class="ch-title">RCBA <span class="grad-text">ImpactBot</span></p>
        <p class="ch-sub">Act for Impact · District 3141</p>
    </div>
    <div class="rag-badge">RAG only</div>
</div>
""", unsafe_allow_html=True)

# Render messages
chat_html = '<div class="chat-wrapper">'
for msg in st.session_state.messages:
    role     = msg["role"]
    content  = msg["content"].replace("\n", "<br>")
    ts       = msg.get("time", "")
    css_role = "bot" if role == "assistant" else "user"
    icon     = "RC" if role == "assistant" else "You"

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

# Chat input
if prompt := st.chat_input("Ask about RCBA — projects, events, how to join…"):
    now = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})

    with st.spinner("Looking that up…"):
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        reply, err = get_ai_response(prompt, history)

    if err:
        reply = f"Error: {err}"

    st.session_state.messages.append({"role": "assistant", "content": reply, "time": now})
    st.rerun()