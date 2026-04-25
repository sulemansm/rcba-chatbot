"""
app.py — RCBA ImpactBot
Themed to match release.rcbombayairport.in
Logo imported from logo_b64.py (base64, no file-serving needed).
RAG-only with expressive, youth-energy tone.
"""

import os
import streamlit as st
from datetime import datetime

from ai_service import get_ai_response, reload_knowledge
from s3_service import upload_lead_to_s3
from email_service import send_lead_email
from logo_b64 import LOGO_SRC

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

for key, val in [
    ("sidebar_open", True),
    ("admin_authenticated", False),
    ("show_admin_prompt", False),
]:
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(
    page_title="RCBA ImpactBot",
    page_icon="\U0001f300",
    layout="wide",
    initial_sidebar_state="expanded" if st.session_state.sidebar_open else "collapsed",
)

# ── CSS ── plain string concatenation — no f-string, no brace conflicts ───────
CSS = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');"
    ":root {"
    "  --orange:     #f97316;"
    "  --orange-dim: rgba(249,115,22,0.12);"
    "  --orange-mid: rgba(249,115,22,0.28);"
    "  --teal:       #22d3ee;"
    "  --teal-dim:   rgba(34,211,238,0.10);"
    "  --purple:     #a855f7;"
    "  --bg:         #0d0d10;"
    "  --surface:    rgba(255,255,255,0.04);"
    "  --border:     rgba(255,255,255,0.08);"
    "  --border-lt:  rgba(255,255,255,0.05);"
    "  --text:       rgba(255,255,255,0.88);"
    "  --muted:      rgba(255,255,255,0.38);"
    "  --font:       'Plus Jakarta Sans', sans-serif;"
    "}"
    "html,body,[data-testid='stApp']{font-family:var(--font);background:var(--bg);color:var(--text);}"
    "[data-testid='stApp']::before{"
    "  content:'';position:fixed;inset:0;z-index:0;pointer-events:none;"
    "  background:"
    "    radial-gradient(ellipse 360px 360px at -80px -80px,rgba(192,57,10,0.42),transparent 70%),"
    "    radial-gradient(ellipse 280px 280px at 18% 92%,rgba(107,33,168,0.36),transparent 70%),"
    "    radial-gradient(ellipse 260px 260px at 90% 10%,rgba(14,116,144,0.33),transparent 70%),"
    "    radial-gradient(ellipse 220px 220px at 94% 82%,rgba(147,51,234,0.28),transparent 70%);"
    "}"
    "#MainMenu,footer,header{visibility:hidden;}"
    "[data-testid='stToolbar']{display:none;}"
    "[data-testid='stSidebar']{background:rgba(13,13,16,0.85)!important;border-right:1px solid var(--border)!important;backdrop-filter:blur(16px);}"
    "[data-testid='stSidebar']>div{padding-top:0!important;}"
    ".block-container{padding:1.5rem 2rem;max-width:880px;position:relative;z-index:1;}"
    ".sb-brand{padding:1.25rem 1rem 1rem;border-bottom:1px solid var(--border-lt);}"
    ".sb-logo-row{display:flex;align-items:center;gap:10px;margin-bottom:12px;}"
    ".sb-logo{width:42px;height:42px;border-radius:50%;flex-shrink:0;border:2px solid rgba(255,255,255,0.12);overflow:hidden;background:#000;}"
    ".sb-logo img{width:100%;height:100%;object-fit:cover;}"
    ".sb-club{font-size:13px;font-weight:800;color:#fff;line-height:1.2;}"
    ".sb-sub{font-size:9px;color:var(--orange);font-weight:700;letter-spacing:0.06em;text-transform:uppercase;}"
    ".sb-pill{display:inline-flex;align-items:center;gap:6px;background:var(--teal-dim);border:1px solid rgba(34,211,238,0.22);border-radius:20px;padding:3px 10px;}"
    ".sb-dot{width:6px;height:6px;border-radius:50%;background:var(--teal);animation:blink 2s infinite;}"
    "@keyframes blink{0%,100%{opacity:1;}50%{opacity:0.25;}}"
    ".sb-pill-text{font-size:9px;color:var(--teal);font-weight:700;letter-spacing:0.04em;}"
    ".sb-stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:14px 16px;border-bottom:1px solid var(--border-lt);}"
    ".stat-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:8px 10px;}"
    ".stat-label{font-size:8.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:1px;}"
    ".stat-val{font-size:20px;font-weight:800;}"
    ".c-orange{color:var(--orange);}"
    ".c-teal{color:var(--teal);}"
    ".sb-section{font-size:8.5px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;padding:12px 16px 6px;display:block;}"
    ".sb-form-header{display:flex;align-items:center;justify-content:space-between;padding:0 16px 10px;}"
    ".sb-form-title{font-size:12px;font-weight:800;color:#fff;}"
    ".sb-form-badge{font-size:8px;padding:2px 7px;border-radius:20px;background:var(--orange-dim);border:1px solid var(--orange-mid);color:var(--orange);font-weight:700;letter-spacing:0.05em;}"
    ".sb-social{display:flex;gap:6px;padding:0 16px 16px;}"
    ".soc-btn{flex:1;padding:5px 0;border-radius:7px;text-align:center;background:var(--surface);border:1px solid var(--border);font-size:10px;font-weight:600;color:var(--muted);text-decoration:none;display:block;}"
    ".soc-btn:hover{background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.85);}"
    "[data-testid='stTextInput'] input,[data-testid='stTextArea'] textarea{background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.09)!important;border-radius:8px!important;color:rgba(255,255,255,0.82)!important;font-family:var(--font)!important;font-size:11px!important;}"
    "[data-testid='stTextInput'] input:focus,[data-testid='stTextArea'] textarea:focus{border-color:rgba(249,115,22,0.5)!important;box-shadow:0 0 0 2px rgba(249,115,22,0.08)!important;}"
    "[data-testid='stTextInput'] label,[data-testid='stTextArea'] label{color:var(--muted)!important;font-size:9px!important;text-transform:uppercase;letter-spacing:0.08em;font-family:var(--font)!important;}"
    "[data-testid='stButton']>button{background:rgba(255,255,255,0.06)!important;color:rgba(255,255,255,0.7)!important;border:1px solid rgba(255,255,255,0.1)!important;border-radius:9px!important;font-family:var(--font)!important;font-weight:700!important;font-size:11px!important;padding:0.45rem 0.85rem;transition:all 0.15s;}"
    "[data-testid='stButton']>button:hover{background:rgba(255,255,255,0.1)!important;color:#fff!important;}"
    "[data-testid='stFormSubmitButton']>button{background:var(--orange)!important;color:#fff!important;font-weight:800!important;width:100%!important;border-radius:9px!important;font-family:var(--font)!important;border:none!important;}"
    "[data-testid='stFormSubmitButton']>button:hover{background:#ea6c0a!important;transform:translateY(-1px);}"
    "[data-testid='stChatInput'] textarea{background:rgba(255,255,255,0.05)!important;border:1px solid rgba(255,255,255,0.09)!important;border-radius:14px!important;color:rgba(255,255,255,0.85)!important;font-family:var(--font)!important;}"
    "[data-testid='stChatInput'] textarea:focus{border-color:rgba(249,115,22,0.4)!important;box-shadow:0 0 0 3px rgba(249,115,22,0.07)!important;}"
    ".chat-header{display:flex;align-items:center;gap:12px;padding-bottom:14px;border-bottom:1px solid var(--border);margin-bottom:1.25rem;}"
    ".ch-logo{width:46px;height:46px;border-radius:50%;flex-shrink:0;border:2px solid rgba(255,255,255,0.14);overflow:hidden;background:#000;}"
    ".ch-logo img{width:100%;height:100%;object-fit:cover;}"
    ".ch-title{font-size:17px;font-weight:800;color:#fff;margin:0;line-height:1.2;}"
    ".ch-sub{font-size:10px;color:var(--muted);margin:0;}"
    ".grad-text{background:linear-gradient(90deg,var(--teal),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}"
    ".rag-badge{margin-left:auto;padding:4px 11px;background:var(--orange-dim);border:1px solid var(--orange-mid);border-radius:20px;font-size:9px;color:var(--orange);font-weight:700;text-transform:uppercase;letter-spacing:0.05em;white-space:nowrap;}"
    ".chat-wrapper{display:flex;flex-direction:column;gap:1rem;margin-bottom:1.25rem;}"
    ".msg-row{display:flex;align-items:flex-start;gap:9px;animation:fadeUp 0.2s ease;}"
    ".msg-row.user{flex-direction:row-reverse;}"
    "@keyframes fadeUp{from{opacity:0;transform:translateY(5px);}to{opacity:1;transform:translateY(0);}}"
    ".avatar{width:32px;height:32px;border-radius:50%;flex-shrink:0;overflow:hidden;border:1.5px solid rgba(255,255,255,0.12);background:#000;}"
    ".avatar img{width:100%;height:100%;object-fit:cover;}"
    ".avatar.user{background:var(--orange-dim);border:1.5px solid var(--orange-mid);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:var(--orange);overflow:visible;}"
    ".bubble{padding:10px 14px;border-radius:16px;max-width:78%;font-size:0.88rem;line-height:1.7;word-break:break-word;}"
    ".bubble.bot{background:rgba(255,255,255,0.05);border:1px solid var(--border);border-top-left-radius:4px;color:var(--text);}"
    ".bubble.user{background:var(--orange-dim);border:1px solid var(--orange-mid);border-top-right-radius:4px;color:#fff;text-align:right;}"
    ".ts{font-size:0.65rem;color:var(--muted);margin-top:3px;opacity:0.65;}"
    ".msg-row.user .ts{text-align:right;}"
    "[data-testid='stMetric']{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:0.5rem 0.75rem;}"
    "[data-testid='stMetricLabel']{color:var(--muted)!important;font-size:8.5px!important;text-transform:uppercase;letter-spacing:0.08em;font-family:var(--font)!important;}"
    "[data-testid='stMetricValue']{color:var(--orange)!important;font-family:var(--font)!important;font-size:1.4rem!important;font-weight:800!important;}"
    "[data-testid='stAlert']{border-radius:10px;}"
    "hr{border:none;border-top:1px solid var(--border-lt);margin:0.75rem 0;}"
    "</style>"
)

st.markdown(CSS, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Jai Rotaract! \U0001f300 Hey there! I\u2019m RCBA ImpactBot, powered by the energy of the "
                    "Rotaract Club of Bombay Airport.\n\n"
                    "Whether you want to know about our projects, upcoming events, how to join, "
                    "or just vibe with what we do \u2014 I\u2019ve got you! "
                    "Everything I share comes straight from our knowledge base, so it\u2019s always legit. "
                    "What would you like to know? \U0001f91c"
                ),
                "time": datetime.now().strftime("%H:%M"),
            }
        ]
    if "lead_submitted" not in st.session_state:
        st.session_state.lead_submitted = False


init_session()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:

    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-logo-row">'
        f'<div class="sb-logo"><img src="{LOGO_SRC}" alt="RCBA Logo"/></div>'
        '<div><div class="sb-club">Rotaract Club</div>'
        '<div class="sb-sub">Bombay Airport</div></div>'
        '</div>'
        '<div class="sb-pill"><div class="sb-dot"></div>'
        '<span class="sb-pill-text">Live \u00b7 Knowledge-grounded</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(
        '<div class="sb-stats">'
        '<div class="stat-card"><div class="stat-label">Messages</div>'
        f'<div class="stat-val c-orange">{msg_count}</div></div>'
        '<div class="stat-card"><div class="stat-label">Projects</div>'
        '<div class="stat-val c-teal">21</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<span class="sb-section">Actions</span>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("\u21ba Reload KB"):
            st.session_state.show_admin_prompt = True
    with col2:
        if st.button("\u2715 Clear"):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared! Fresh start \u2014 what\u2019s on your mind? \U0001f60a",
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

    st.markdown(
        '<div class="sb-form-header">'
        '<span class="sb-form-title">Get in touch</span>'
        '<span class="sb-form-badge">FREE</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.lead_submitted:
        st.success("You\u2019re on our radar! We\u2019ll be in touch soon \U0001f91c")
    else:
        with st.form("lead_form", clear_on_submit=True):
            name  = st.text_input("Name *",  placeholder="Jane Smith")
            email = st.text_input("Email *", placeholder="jane@example.com")
            phone = st.text_input("Phone",   placeholder="+91 98765 43210")
            submitted = st.form_submit_button("+ Join the Movement", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.error("Name is required.")
                elif not email.strip() or "@" not in email:
                    st.error("A valid email is required.")
                else:
                    ts   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    lead = {
                        "name":      name.strip(),
                        "email":     email.strip(),
                        "phone":     phone.strip() or "\u2014",
                        "timestamp": ts,
                    }
                    s3_ok,   s3_msg   = upload_lead_to_s3(lead)
                    mail_ok, mail_msg = send_lead_email(lead)
                    if not s3_ok:   st.warning(f"S3: {s3_msg}")
                    if not mail_ok: st.warning(f"Email: {mail_msg}")
                    st.session_state.lead_submitted = True
                    st.rerun()

    st.markdown(
        '<hr>'
        '<span class="sb-section" style="padding-left:0;display:block;margin-bottom:8px;">Find us online</span>'
        '<div class="sb-social">'
        '<a class="soc-btn" href="https://www.instagram.com/rc_bombayairport/" target="_blank">IG</a>'
        '<a class="soc-btn" href="https://www.linkedin.com/in/rotaract-club-of-bombay-airport-6a35621a7/" target="_blank">LI</a>'
        '<a class="soc-btn" href="https://www.facebook.com/RCBombayAirport/" target="_blank">FB</a>'
        '<a class="soc-btn" href="https://www.rcbombayairport.org" target="_blank">WEB</a>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── MAIN CHAT ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="chat-header">'
    f'<div class="ch-logo"><img src="{LOGO_SRC}" alt="RCBA"/></div>'
    '<div>'
    '<p class="ch-title">RCBA <span class="grad-text">ImpactBot</span></p>'
    '<p class="ch-sub">Act for Impact \u00b7 District 3141</p>'
    '</div>'
    '<div class="rag-badge">RAG only</div>'
    '</div>',
    unsafe_allow_html=True,
)

chat_html = '<div class="chat-wrapper">'
for msg in st.session_state.messages:
    role     = msg["role"]
    content  = msg["content"].replace("\n", "<br>")
    ts       = msg.get("time", "")
    css_role = "bot" if role == "assistant" else "user"

    if role == "assistant":
        avatar_html = f'<div class="avatar"><img src="{LOGO_SRC}" alt="RCBA"/></div>'
    else:
        avatar_html = '<div class="avatar user">Y</div>'

    chat_html += (
        f'<div class="msg-row {css_role}">'
        f'{avatar_html}'
        f'<div>'
        f'<div class="bubble {css_role}">{content}</div>'
        f'<div class="ts">{ts}</div>'
        f'</div>'
        f'</div>'
    )

chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

if prompt := st.chat_input("Ask me anything about RCBA \u2014 projects, events, how to join\u2026 \U0001f300"):
    now = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})

    with st.spinner("On it\u2026"):
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        reply, err = get_ai_response(prompt, history)

    if err:
        reply = f"Hmm, something went wrong: {err}"

    st.session_state.messages.append({"role": "assistant", "content": reply, "time": now})
    st.rerun()