"""
=============================================================
  streamlit_app.py — Electronic Voting System (Web UI)
  ENSTA Alger — Asymmetric Cryptography 2026
=============================================================
  Run with:
    streamlit run streamlit_app.py

  Default passwords:
    Admin       : admin
    Commissioner: comm
    Anonymizer:anony

  App lifecycle (controlled by Admin):
    OFFLINE  → App shows a closed screen to everyone
    SETUP    → Only Commissioner can prepare the election
    OPEN     → All roles are accessible
    CLOSED   → Election ended, only results visible
=============================================================
"""

import streamlit as st
import json, os, random, hashlib, string as _str
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#  PASSWORDS
# ═══════════════════════════════════════════════════════════
def _h(p): return hashlib.sha256(p.encode()).hexdigest()

ROLE_PASSWORDS = {
    "admin":        _h("admin"),
    "commissioner": _h("comm"),
    "anonymizer":_h("anony")
}

# ═══════════════════════════════════════════════════════════
#  APP PHASES
# ═══════════════════════════════════════════════════════════
PHASES = {
    "offline": {
        "label": "⚫ Offline",
        "color": "#555",
        "desc":  "Application is closed. Nobody can access it.",
    },
    "setup": {
        "label": "🟡 Setup",
        "color": "#d68910",
        "desc":  "Preparation phase. Commissioner configures the election.",
    },
    "open": {
        "label": "🟢 Open",
        "color": "#1e8449",
        "desc":  "Election is live. All roles are accessible.",
    },
    "closed": {
        "label": "🔴 Closed",
        "color": "#922b21",
        "desc":  "Election ended. Results are available for viewing.",
    },
}

APP_STATE_FILE = "app_state.json"

def load_app_state() -> dict:
    default = {
        "phase":   "offline",
        "message": "",
        "launched_at":  None,
        "closed_at":    None,
        "phase_history": [],
    }
    if not os.path.exists(APP_STATE_FILE):
        return default
    try:
        with open(APP_STATE_FILE) as f:
            data = json.load(f)
        for k, v in default.items():
            data.setdefault(k, v)
        return data
    except:
        return default

def save_app_state(state: dict):
    with open(APP_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def set_phase(new_phase: str, message: str = ""):
    state = load_app_state()
    old   = state["phase"]
    state["phase_history"].append({
        "from": old, "to": new_phase,
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    })
    state["phase"]   = new_phase
    state["message"] = message
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if new_phase == "open":    state["launched_at"] = now_str
    if new_phase == "closed":  state["closed_at"]   = now_str
    save_app_state(state)

ROLES = {
    "voter":        {"label": "🗳️ Voter",       "color": "#2980b9", "desc": "Cast your anonymous vote"},
    "commissioner": {"label": "👮 Commissioner", "color": "#8e44ad", "desc": "Manage the election lifecycle"},
    "admin":        {"label": "🔐 Admin",         "color": "#1F4E79", "desc": "System administration"},
    "anonymizer":   {"label": "📮 Anonymizer",    "color": "#16a085", "desc": "View the ballot box"},
    "counter":      {"label": "🔢 Counter",       "color": "#d35400", "desc": "Count votes & publish results"},
}

# Which roles are allowed in each phase
PHASE_ACCESS = {
    "offline": [],
    "setup":   ["commissioner"],
    "open":    ["voter", "commissioner", "anonymizer", "counter"],
    "closed":  ["counter", "anonymizer"],
}

# ═══════════════════════════════════════════════════════════
#  PAGE CONFIG & CSS
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EVS — ENSTA 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── General ── */
body { font-family: 'Segoe UI', sans-serif; }

/* ── Headers ── */
.main-header {
    background: linear-gradient(135deg, #1F4E79, #2980b9);
    color: white; padding: 22px 30px; border-radius: 14px;
    margin-bottom: 24px; text-align: center;
}
.role-header {
    padding: 14px 24px; border-radius: 10px; color: white;
    margin-bottom: 20px;
}

/* ── Offline / closed screens ── */
.closed-screen {
    text-align: center; padding: 80px 20px;
    max-width: 640px; margin: 60px auto;
}
.closed-icon { font-size: 5em; margin-bottom: 16px; }
.phase-badge {
    display: inline-block; padding: 6px 20px;
    border-radius: 20px; font-weight: 700;
    font-size: .95em; color: white; margin-bottom: 20px;
}

/* ── Role cards ── */
.role-card-wrap {
    text-align: center; border-radius: 14px; padding: 24px 10px;
    background: white; cursor: pointer;
}

/* ── Misc ── */
.status-card { background:#f8f9fa; border-left:5px solid #1F4E79;
               padding:14px 20px; border-radius:8px; margin:7px 0; }
.status-ok   { border-left-color:#27ae60; background:#eafaf1; }
.status-warn { border-left-color:#f39c12; background:#fef9e7; }
.phase-box   { background:#eaf4ff; border:1.5px solid #2980b9;
               border-radius:10px; padding:18px 22px; margin:12px 0; }
.step-box    { background:#f4f6f8; border:1px solid #ccc;
               border-radius:8px; padding:12px 16px;
               font-family:monospace; font-size:.9em; margin:6px 0; }
.timeline-item { display:flex; gap:14px; align-items:flex-start;
                 padding:10px 0; border-bottom:1px solid #eee; }
.timeline-dot  { width:14px; height:14px; border-radius:50%;
                 margin-top:4px; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  BACKEND IMPORT
# ═══════════════════════════════════════════════════════════
try:
    from commissioner import (
        load_data, save_data, load_emails, save_emails, load_codes,
        generate_all_codes, backup_emails, restore_emails_from_backup,
        request_voter_card, verify_voter, invalidate_N1,
    )
    from admin import (
        mask_vote, blind_sign, unmask_signature,
        verify_signature, get_valid_k_values, N as RSA_N, e as RSA_e,
    )
    from anonymizer import receive_ballot, load_urne
    from counter import count_votes
    from email_sender import save_config, load_config, test_connection
    from tth import compute_tth
    BACKEND_OK = True
except ImportError as _err:
    BACKEND_OK = False
    _IMPORT_ERR = str(_err)

# ═══════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════
for _k, _v in [("role", None), ("authenticated", False)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def get_status():
    email_ok  = load_config() is not None
    codes_rdy = os.path.exists("codes.json")
    comm_rdy  = os.path.exists("commissioner_data.json")
    data      = load_data() if comm_rdy else {}
    used      = data.get("used_codes", {})
    is_open   = data.get("election_open", False)
    urne_size = 0
    if os.path.exists("urne.json"):
        try:
            with open("urne.json") as f:
                c = f.read().strip()
            urne_size = len(json.loads(c)) if c else 0
        except: pass
    return {
        "email_ok":      email_ok,
        "codes_ready":   codes_rdy,
        "is_open":       is_open,
        "nb_sent":       len(used),
        "nb_voted":      sum(1 for v in used.values() if v.get("has_voted")),
        "urne_size":     urne_size,
        "results_exist": os.path.exists("results.json"),
        "used_codes":    used,
    }

def logout():
    st.session_state.role          = None
    st.session_state.authenticated = False

def role_header(role):
    rv = ROLES[role]
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(
            f'<div class="role-header" style="background:{rv["color"]};">'
            f'<span style="font-size:1.5em">{rv["label"].split()[0]}</span>&nbsp;&nbsp;'
            f'<b style="font-size:1.1em">{" ".join(rv["label"].split()[1:])}</b>'
            f'&nbsp;<span style="font-size:.82em;opacity:.85">— {rv["desc"]}</span></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            logout(); st.rerun()

def phase_badge_html(phase):
    p = PHASES[phase]
    return (f'<span class="phase-badge" style="background:{p["color"]};">'
            f'{p["label"]}</span>')

# ═══════════════════════════════════════════════════════════
#  BACKEND CHECK
# ═══════════════════════════════════════════════════════════
if not BACKEND_OK:
    st.error(f"❌ Backend import error: `{_IMPORT_ERR}`\n\nPlace all `.py` files in the same folder.")
    st.stop()


# ═══════════════════════════════════════════════════════════
#  SCREEN: SYSTEM OFFLINE / CLOSED  (shown to non-admins)
# ═══════════════════════════════════════════════════════════
def show_system_offline(app_state):
    phase = app_state["phase"]
    msg   = app_state.get("message", "")

    icons   = {"offline": "🔒", "setup": "🛠️", "closed": "🏁"}
    titles  = {
        "offline": "System Offline",
        "setup":   "Election in Preparation",
        "closed":  "Election Ended",
    }
    subtitles = {
        "offline": "The voting system is currently offline.\nPlease wait for the administrator to launch it.",
        "setup":   "The election is being set up by the commissioner.\nVoting has not started yet.",
        "closed":  "The election has ended.\nResults will be published shortly.",
    }

    icon  = icons.get(phase, "🔒")
    title = titles.get(phase, "Unavailable")
    sub   = subtitles.get(phase, "")

    st.markdown(f"""
    <div class="closed-screen">
        <div class="closed-icon">{icon}</div>
        <div>{phase_badge_html(phase)}</div>
        <h2 style="margin:10px 0 8px">{title}</h2>
        <p style="color:#555;font-size:1em;white-space:pre-line">{sub}</p>
        {"<hr style='border:none;border-top:1px solid #ddd;margin:20px 0'><p style='color:#888;font-style:italic'>📢 " + msg + "</p>" if msg else ""}
        <p style="margin-top:40px;color:#aaa;font-size:.82em">
            ENSTA Alger — Asymmetric Cryptography 2026
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Small admin login link at the bottom
    st.markdown("---")
    col_l, col_m, col_r = st.columns([2,1,2])
    with col_m:
        if st.button("🔐 Admin Login", use_container_width=True):
            st.session_state.role          = "admin"
            st.session_state.authenticated = False
            st.rerun()


# ═══════════════════════════════════════════════════════════
#  SCREEN: ROLE SELECTION
# ═══════════════════════════════════════════════════════════
def show_role_selection(allowed_roles, app_state):
    phase = app_state["phase"]

    st.markdown(f"""
    <div class="main-header">
        <h1>🗳️ Electronic Voting System</h1>
        <p>ENSTA Alger — Asymmetric Cryptography 2026</p>
        <div style="margin-top:10px">{phase_badge_html(phase)}</div>
    </div>
    """, unsafe_allow_html=True)

    if app_state.get("message"):
        st.info(f"📢 {app_state['message']}")

    st.markdown("## 👤 Who are you?")
    st.markdown("Select your role to access your interface.")
    st.markdown("")

    # Show only roles allowed in current phase + always show Admin
    display_roles = {k: v for k, v in ROLES.items()
                     if k in allowed_roles or k == "admin"}

    cols = st.columns(len(display_roles))
    for col, (rk, rv) in zip(cols, display_roles.items()):
        with col:
            emoji = rv["label"].split()[0]
            name  = " ".join(rv["label"].split()[1:])
            lock  = " 🔒" if rk in ROLE_PASSWORDS else ""
            disabled = rk not in allowed_roles and rk != "admin"
            border_color = rv["color"] if not disabled else "#ccc"
            text_color   = rv["color"] if not disabled else "#aaa"
            bg_color     = "white"     if not disabled else "#f9f9f9"

            st.markdown(
                f'<div class="role-card-wrap" style="border:2px solid {border_color};'
                f'background:{bg_color};">'
                f'<div style="font-size:2.4em">{emoji}</div>'
                f'<div style="font-weight:700;color:{text_color};margin-top:8px">{name}{lock}</div>'
                f'<div style="font-size:.75em;color:#666;margin-top:6px">{rv["desc"]}</div>'
                f'{"" if not disabled else "<div style=\'font-size:.72em;color:#e74c3c;margin-top:6px\'>🚫 Not available now</div>"}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
            if not disabled:
                if st.button("Select", key=f"sel_{rk}", use_container_width=True):
                    st.session_state.role          = rk
                    st.session_state.authenticated = rk not in ROLE_PASSWORDS
                    st.rerun()
            else:
                st.button("Unavailable", key=f"dis_{rk}", disabled=True,
                          use_container_width=True)


# ═══════════════════════════════════════════════════════════
#  SCREEN: LOGIN
# ═══════════════════════════════════════════════════════════
def show_login(role):
    rv = ROLES[role]
    st.markdown(f"""
    <div class="main-header">
        <h2>{rv['label']}</h2>
        <p>Protected area — please authenticate</p>
    </div>
    """, unsafe_allow_html=True)

    _, col_m, _ = st.columns([1, 1.6, 1])
    with col_m:
        st.markdown(
            f'<div style="text-align:center;padding:20px 0 10px">'
            f'<span style="font-size:3.5em">🔒</span>'
            f'<h3 style="color:{rv["color"]};margin:8px 0">{rv["label"]} Login</h3>'
            f'<p style="color:#666;font-size:.9em">Enter the password for this role</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            pwd  = st.text_input("Password", type="password", placeholder="••••••••")
            c1, c2 = st.columns(2)
            submitted = c1.form_submit_button("🔓 Login",  use_container_width=True, type="primary")
            go_back   = c2.form_submit_button("← Back", use_container_width=True)

        if submitted:
            if _h(pwd) == ROLE_PASSWORDS[role]:
                st.session_state.authenticated = True; st.rerun()
            else:
                st.error("❌ Incorrect password.")
        if go_back:
            logout(); st.rerun()


# ═══════════════════════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════════════════════
def show_admin():
    role_header("admin")
    app_state = load_app_state()
    s         = get_status()
    phase     = app_state["phase"]

    tab_launch, tab_status, tab_email, tab_results, tab_settings = st.tabs([
        "🚀 Launch Control", "📊 System Status", "📧 Email Setup", "📈 Results", "⚙️ Settings",
    ])

    # ════════════════════════════════════════════════════════
    #  TAB: LAUNCH CONTROL
    # ════════════════════════════════════════════════════════
    with tab_launch:
        st.markdown("### 🚀 Application Launch Control")
        st.markdown("You control the full lifecycle of the application. "
                    "Nobody can access it without your action.")

        # ── Current phase display ────────────────────────────
        ph = PHASES[phase]
        st.markdown(
            f'<div style="background:{ph["color"]};color:white;border-radius:12px;'
            f'padding:20px 28px;margin:16px 0;">'
            f'<div style="font-size:1.5em;font-weight:700">{ph["label"]}</div>'
            f'<div style="opacity:.85;margin-top:4px">{ph["desc"]}</div>'
            f'{"<div style=\'margin-top:8px;font-style:italic;opacity:.8\'>📢 " + app_state["message"] + "</div>" if app_state.get("message") else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Phase transition buttons ─────────────────────────
        st.markdown("#### 🎛️ Change Phase")

        ann_msg = st.text_input(
            "📢 Announcement message (optional — shown to all users)",
            placeholder="e.g. Voting opens today at 14:00 — Good luck!",
            value=app_state.get("message",""),
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**⚫ Offline**")
            st.markdown("<small>Shut down the app completely. Nobody sees anything.</small>",
                        unsafe_allow_html=True)
            if st.button("⚫ Set Offline", disabled=(phase == "offline"),
                         use_container_width=True):
                set_phase("offline", ann_msg)
                st.success("⚫ Application is now OFFLINE."); st.rerun()

        with col2:
            st.markdown("**🟡 Setup**")
            st.markdown("<small>Preparation only. Commissioner can configure, no voting yet.</small>",
                        unsafe_allow_html=True)
            if st.button("🟡 Set Setup", disabled=(phase == "setup"),
                         use_container_width=True):
                set_phase("setup", ann_msg)
                st.success("🟡 Application is in SETUP mode."); st.rerun()

        with col3:
            st.markdown("**🟢 Open**")
            st.markdown("<small>Launch the election. All roles become accessible.</small>",
                        unsafe_allow_html=True)
            can_open = s["email_ok"] and s["codes_ready"]
            if not can_open and phase != "open":
                st.warning("⚠️ Configure Gmail + generate codes first.")
            if st.button("🟢 Launch Election", disabled=(phase == "open" or not can_open),
                         use_container_width=True, type="primary"):
                set_phase("open", ann_msg)
                st.success("🟢 Election is now LIVE!"); st.rerun()

        with col4:
            st.markdown("**🔴 Closed**")
            st.markdown("<small>End the election. Only results remain accessible.</small>",
                        unsafe_allow_html=True)
            if st.button("🔴 Close Election", disabled=(phase == "closed"),
                         use_container_width=True):
                set_phase("closed", ann_msg)
                st.success("🔴 Election CLOSED."); st.rerun()

        # ── Roadmap ──────────────────────────────────────────
        st.divider()
        st.markdown("#### 📋 Recommended Lifecycle")
        steps_done = {
            "offline": True,
            "setup":   phase in ("setup","open","closed"),
            "open":    phase in ("open","closed"),
            "closed":  phase == "closed",
        }
        for ph_key, ph_val in PHASES.items():
            done = steps_done[ph_key]
            current = ph_key == phase
            border = f"3px solid {ph_val['color']}" if current else "1px solid #eee"
            bg     = "#fff8f0" if current else "white"
            icon   = "✅" if done and not current else ("▶️" if current else "⏳")
            st.markdown(
                f'<div style="border:{border};background:{bg};border-radius:10px;'
                f'padding:12px 18px;margin:6px 0;display:flex;align-items:center;gap:14px;">'
                f'<span style="font-size:1.3em">{icon}</span>'
                f'<div><b style="color:{ph_val["color"]}">{ph_val["label"]}</b>'
                f'{"  ← <b>Current</b>" if current else ""}'
                f'<br><small style="color:#666">{ph_val["desc"]}</small></div></div>',
                unsafe_allow_html=True,
            )

        # ── History ──────────────────────────────────────────
        history = app_state.get("phase_history", [])
        if history:
            st.divider()
            st.markdown("#### 🕒 Phase History")
            for h in reversed(history[-10:]):
                fr_col = PHASES.get(h["from"],{}).get("color","#888")
                to_col = PHASES.get(h["to"],  {}).get("color","#888")
                st.markdown(
                    f'<div class="timeline-item">'
                    f'<div class="timeline-dot" style="background:{to_col}"></div>'
                    f'<div><span style="color:{fr_col};font-weight:600">'
                    f'{PHASES.get(h["from"],{}).get("label",h["from"])}</span>'
                    f' → <span style="color:{to_col};font-weight:600">'
                    f'{PHASES.get(h["to"],{}).get("label",h["to"])}</span>'
                    f'<br><small style="color:#888">{h["at"]}'
                    f'{"  —  " + h["message"] if h.get("message") else ""}</small></div></div>',
                    unsafe_allow_html=True,
                )

    # ════════════════════════════════════════════════════════
    #  TAB: SYSTEM STATUS
    # ════════════════════════════════════════════════════════
    with tab_status:
        st.markdown("### 📊 System Overview")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Cards Sent",       s["nb_sent"])
        c2.metric("Voted",            s["nb_voted"])
        c3.metric("Ballots in Urne",  s["urne_size"])
        c4.metric("Results",          "✅ Done" if s["results_exist"] else "⏳ Not yet")
        st.divider()
        items = [
            (s["email_ok"],      "Gmail configured",  "Gmail NOT configured"),
            (s["codes_ready"],   "Codes generated",   "Codes not generated"),
            (s["is_open"],       "Election OPEN",     "Election CLOSED"),
            (s["urne_size"] > 0, "Votes received",    "No votes yet"),
            (s["results_exist"], "Results published", "Not counted yet"),
        ]
        for ok, t, f in items:
            css = "status-ok" if ok else "status-warn"
            st.markdown(
                f'<div class="status-card {css}">{"✅" if ok else "⏳"} '
                f'{"<b>"+t+"</b>" if ok else f}</div>',
                unsafe_allow_html=True,
            )
        used = s["used_codes"]
        if used:
            st.divider(); st.markdown("### 👥 Voter Progress")
            st.dataframe(
                [{"Email": em, "N1": v.get("N1",""),
                  "Voted": "✅ Yes" if v.get("has_voted") else "⏳ No"}
                 for em, v in used.items()],
                use_container_width=True,
            )

    # ════════════════════════════════════════════════════════
    #  TAB: EMAIL SETUP
    # ════════════════════════════════════════════════════════
    with tab_email:
        st.markdown("### 📧 Gmail Configuration")
        cfg = load_config()
        if cfg:
            st.success(f"✅ Configured: **{cfg['gmail']}**")
            if st.button("🔄 Test Connection"):
                with st.spinner("Testing..."):
                    ok = test_connection()
                st.success("✅ Connected!") if ok else st.error("❌ Failed.")
            st.divider()
        with st.expander("How to get a Gmail App Password", expanded=not bool(cfg)):
            st.markdown("""
1. [myaccount.google.com](https://myaccount.google.com) → **Security**
2. Enable **2-Step Verification**
3. **App passwords** → Select *Mail* → Generate
4. Copy the 16-character password
            """)
        with st.form("email_form"):
            gmail = st.text_input("Gmail address", value=cfg["gmail"] if cfg else "")
            apwd  = st.text_input("App Password (16 chars)", type="password")
            if st.form_submit_button("💾 Save & Test", type="primary"):
                g = gmail.strip(); p = apwd.strip().replace(" ","")
                if g and p:
                    save_config(g, p)
                    with st.spinner("Testing..."): ok = test_connection()
                    st.success("✅ Ready!") if ok else st.error("❌ Connection failed.")
                else:
                    st.error("Both fields required.")

    # ════════════════════════════════════════════════════════
    #  TAB: RESULTS
    # ════════════════════════════════════════════════════════
    with tab_results:
        st.markdown("### 📈 Election Results")
        if not os.path.exists("results.json"):
            st.info("⏳ Not available yet.")
        else:
            with open("results.json") as f: data = json.load(f)
            sm = data["summary"]
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total", sm["total"]); c2.metric("Valid", sm["valid"])
            c3.metric("Invalid", sm["invalid"]); c4.metric("Average", f"{sm['average']}/10")
            st.divider()
            vc = data.get("vote_counts",{})
            if vc:
                mx = max(vc.values())
                for g in sorted(vc, key=int):
                    cnt = vc[g]; bar = int((cnt/mx)*220)
                    st.markdown(
                        f'**{g}/10** &nbsp;<span style="background:#1F4E79;height:20px;'
                        f'width:{bar}px;display:inline-block;border-radius:4px;"></span>'
                        f'&nbsp; {cnt} vote{"s" if cnt>1 else ""}',
                        unsafe_allow_html=True,
                    )
            st.divider()
            for r in data.get("public_results",[]):
                st.markdown(f'{"✅" if r["valid"] else "❌"} `N2={r["N2"]}` → **{r["vote"]}**/10')
            with st.expander("📥 Raw JSON"): st.json(data)

    # ════════════════════════════════════════════════════════
    #  TAB: SETTINGS
    # ════════════════════════════════════════════════════════
    with tab_settings:
        st.markdown("### ⚙️ Change Passwords")
        st.info("Changes are valid for the current session. Update the script for permanent changes.")

        st.markdown("#### 🔐 Admin Password")
        with st.form("pwd_admin"):
            old_a = st.text_input("Current admin password", type="password")
            new_a = st.text_input("New password", type="password")
            cfm_a = st.text_input("Confirm new", type="password")
            if st.form_submit_button("Update"):
                if _h(old_a) != ROLE_PASSWORDS["admin"]: st.error("❌ Wrong current password.")
                elif new_a != cfm_a: st.error("❌ Passwords don't match.")
                elif len(new_a) < 6:  st.error("❌ Minimum 6 characters.")
                else:
                    ROLE_PASSWORDS["admin"] = _h(new_a)
                    st.success("✅ Admin password updated.")

        st.divider()
        st.markdown("#### 👮 Commissioner Password")
        with st.form("pwd_comm"):
            adm_c = st.text_input("Confirm with admin password", type="password")
            new_c = st.text_input("New commissioner password",   type="password")
            cfm_c = st.text_input("Confirm new",                 type="password")
            if st.form_submit_button("Update"):
                if _h(adm_c) != ROLE_PASSWORDS["admin"]: st.error("❌ Wrong admin password.")
                elif new_c != cfm_c: st.error("❌ Passwords don't match.")
                elif len(new_c) < 6:  st.error("❌ Minimum 6 characters.")
                else:
                    ROLE_PASSWORDS["commissioner"] = _h(new_c)
                    st.success("✅ Commissioner password updated.")


# ═══════════════════════════════════════════════════════════
#  COMMISSIONER PANEL
# ═══════════════════════════════════════════════════════════
def show_commissioner():
    role_header("commissioner")
    s    = get_status()
    data = load_data()

    tab_em, tab_cd, tab_el, tab_st, tab_rs = st.tabs([
        "📋 Emails", "⚙️ Generate Codes", "🟢 Open / 🔴 Close", "📊 Status", "♻️ Reset",
    ])

    with tab_em:
        st.markdown("### 📋 Registered Voters")
        emails = load_emails()
        st.info(f"**{len(emails)}** email(s) registered")
        with st.form("add_email"):
            ne = st.text_input("Add email", placeholder="student@ensta.edu.dz")
            if st.form_submit_button("➕ Add"):
                ne = ne.strip().lower()
                if not ne: st.error("Enter a valid email.")
                elif ne in emails: st.warning("Already in list.")
                else:
                    emails.append(ne); save_emails(emails)
                    st.success(f"✅ Added: {ne}"); st.rerun()
        with st.expander("📂 Bulk add (one per line)"):
            bulk = st.text_area("Paste emails")
            if st.button("➕ Add All"):
                new_ones = [x.strip().lower() for x in bulk.splitlines() if x.strip()]
                added = 0
                for e in new_ones:
                    if e not in emails: emails.append(e); added += 1
                save_emails(emails)
                st.success(f"✅ Added {added} email(s)."); st.rerun()
        st.divider()
        if emails:
            for i, em in enumerate(emails):
                ca, cb = st.columns([5,1])
                ca.write(f"`{i+1}.` {em}")
                if cb.button("🗑️", key=f"del_{i}"):
                    emails.pop(i); save_emails(emails); st.rerun()
        else:
            st.warning("No emails registered.")

    with tab_cd:
        st.markdown("### ⚙️ Generate Voter Codes")
        emails = load_emails()
        if s["is_open"]: st.error("❌ Cannot generate codes while election is open!")
        elif not emails:  st.warning("⚠️ Add voter emails first.")
        else:
            st.info(f"Will generate **{len(emails)}** code pair(s).")
            if st.button("🔑 Generate Codes", type="primary"):
                with st.spinner("Generating..."):
                    backup_emails(); generate_all_codes(len(emails))
                st.success(f"✅ {len(emails)} code pairs generated!"); st.rerun()
        codes = load_codes()
        if codes: st.metric("Codes remaining", len(codes))

    with tab_el:
        st.markdown("### 🟢 Open / 🔴 Close Internal Election")
        st.info("ℹ️ This controls the internal voting flag. The overall app access is managed by the Admin (Launch Control).")
        if s["is_open"]:
            st.success("🟢 Voting is **OPEN**")
            if st.button("🔴 Close Voting", type="secondary"):
                data["election_open"] = False; save_data(data)
                st.success("🔴 Voting closed."); st.rerun()
        else:
            st.error("🔴 Voting is **CLOSED**")
            if not s["email_ok"]: st.warning("⚠️ Admin must configure Gmail first.")
            elif not s["codes_ready"]: st.warning("⚠️ Generate codes first.")
            else:
                if st.button("🟢 Open Voting", type="primary"):
                    data["election_open"] = True; save_data(data)
                    st.success("✅ Voting is now OPEN!"); st.rerun()

    with tab_st:
        st.markdown("### 📊 Status")
        used  = data.get("used_codes", {})
        voted = sum(1 for v in used.values() if v.get("has_voted"))
        c1,c2,c3 = st.columns(3)
        c1.metric("Emails left", len(load_emails()))
        c2.metric("Cards sent",  len(used))
        c3.metric("Voted",       voted)
        if used:
            st.divider()
            st.dataframe(
                [{"Email": em, "N1": v.get("N1",""),
                  "Voted": "✅ Yes" if v.get("has_voted") else "⏳ No"}
                 for em, v in used.items()],
                use_container_width=True,
            )

    with tab_rs:
        st.markdown("### ♻️ Reset for New Election")
        st.warning("Deletes all votes, codes, urne & results. Restores emails from backup.")
        confirm = st.text_input("Type **RESET** to confirm")
        if st.button("♻️ Reset Now", type="secondary"):
            if confirm == "RESET":
                save_data({"election_open": False, "used_codes": {}})
                for ff in ["codes.json","urne.json","ballots.json","results.json"]:
                    if os.path.exists(ff): os.remove(ff)
                restore_emails_from_backup()
                st.success("✅ Reset complete!"); st.rerun()
            else:
                st.error("❌ Type RESET exactly.")


# ═══════════════════════════════════════════════════════════
#  VOTER PANEL
# ═══════════════════════════════════════════════════════════
def show_voter():
    role_header("voter")
    s = get_status()
    if not s["email_ok"]:
        st.error("❌ Gmail not configured. Contact the administrator."); return
    if not s["codes_ready"]:
        st.error("❌ Codes not generated. Wait for the commissioner."); return
    if not s["is_open"]:
        st.error("❌ Voting is not open yet. Wait for the commissioner."); return

    st.markdown("""
    <div class="main-header">
        <h2>🗳️ Course Evaluation — ENSTA 2026</h2>
        <p>Your vote is anonymous — Blind RSA Signature Protocol</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    st.markdown("### 📨 Step 1 — Request your Voter Card")
    with st.form("phase1"):
        email_in = st.text_input("Your email", placeholder="student@ensta.edu.dz")
        if st.form_submit_button("📧 Send Voter Card", type="primary"):
            email_in = email_in.strip().lower()
            if not email_in: st.error("❌ Email required!")
            else:
                with st.spinner("Sending..."): ok, reason = request_voter_card(email_in)
                if ok: st.success(f"✅ {reason}"); st.info("📬 Check inbox, then go to Step 2.")
                else:  st.error(f"❌ {reason}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Step 2 — Authenticate & Vote")
    with st.form("vote_form"):
        c1, c2 = st.columns(2)
        n1   = c1.text_input("N1 — identity code").strip().upper()
        n2   = c2.text_input("N2 — secret code").strip().upper()
        vote = st.select_slider("Your rating:",
                                options=list(range(1,11)),
                                format_func=lambda x: f"{x}/10  {'⭐'*x}")
        cast = st.form_submit_button("🗳️ Cast My Vote", type="primary")

    if cast:
        if not n1 or not n2: st.error("❌ N1 and N2 required!")
        else:
            with st.spinner("Verifying..."):
                ok, reason = verify_voter(n1, n2)
            if not ok: st.error(f"❌ ACCESS DENIED: {reason}")
            else:
                st.success("✅ Identity verified!")
                st.markdown("---")
                st.markdown(f"#### 🔏 Blind Signature  `N={RSA_N}, e={RSA_e}, d=3`")
                k     = random.choice(get_valid_k_values())
                m1    = mask_vote(vote, k)
                m2    = blind_sign(m1)
                s_sig = unmask_signature(m2, k)
                valid = verify_signature(vote, s_sig)

                st.markdown(
                    f'<div class="step-box">🎭 <b>A — Mask:</b> '
                    f'm\' = {vote}×{k}^{RSA_e} mod {RSA_N} = <b>{m1}</b></div>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<div class="step-box">✍️ <b>B — Blind sign:</b> '
                    f'm\'\' = {m1}³ mod {RSA_N} = <b>{m2}</b></div>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<div class="step-box">🔓 <b>C — Unmask:</b> '
                    f's = {m2}×k⁻¹ mod {RSA_N} = <b>{s_sig}</b></div>',
                    unsafe_allow_html=True)

                if not valid:
                    st.error("❌ Signature invalid!")
                else:
                    st.markdown(
                        f'<div class="step-box" style="background:#eafaf1;border-color:#27ae60;">'
                        f'✅ <b>D — Verified:</b> {s_sig}^{RSA_e} mod {RSA_N} = '
                        f'{pow(s_sig,RSA_e,RSA_N)} == {vote} ✅</div>',
                        unsafe_allow_html=True)
                    rb  = ''.join(random.choices(_str.ascii_uppercase+_str.digits, k=8))
                    tth = compute_tth(n2)
                    ballot = {"N1": n1, "N2": n2, "tth_n2": tth, "vote": vote,
                              "random_bits": rb, "ballot_str": f"{vote}|{n2}|{rb}", "signature": s_sig}
                    ok2, reason2 = receive_ballot(ballot)
                    if ok2:
                        st.balloons()
                        st.success("🎉 Vote submitted!")
                        st.metric("Your vote", f"{vote}/10")
                        st.info(f"💡 Save your N2 to verify later: `{n2}`")
                    else:
                        st.error(f"❌ Rejected: {reason2}")
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  ANONYMIZER PANEL
# ═══════════════════════════════════════════════════════════
def show_anonymizer():
    role_header("anonymizer")
    urne = load_urne()
    st.metric("Total ballots stored", len(urne))
    st.info("🔒 N1 is never stored — anonymity guaranteed.")
    if not urne: st.warning("No ballots yet."); return
    st.divider()
    for i, b in enumerate(urne):
        with st.expander(f"Ballot #{i+1}"):
            st.markdown(f"**N2:** `{b.get('N2','N/A')}`")
            tth = b.get("tth_n2","")
            st.markdown(f"**TTH(N2):** `{tth[:30]}...`" if tth else "**TTH(N2):** N/A")
            st.markdown(f"**Ballot:** `{b.get('ballot_str','N/A')}`")
            st.markdown(f"**Signature:** `{b.get('signature','N/A')}`")


# ═══════════════════════════════════════════════════════════
#  COUNTER PANEL
# ═══════════════════════════════════════════════════════════
def show_counter():
    role_header("counter")
    s = get_status()
    tab_c, tab_r, tab_v = st.tabs(["🔢 Count Votes", "📊 Results", "🔍 Verify My Vote"])

    with tab_c:
        if s["is_open"]: st.error("❌ Voting still open! Commissioner must close it first.")
        elif s["urne_size"] == 0: st.warning("⚠️ No ballots yet.")
        else:
            st.info(f"**{s['urne_size']}** ballot(s) ready.")
            if st.button("🔢 Count All Votes", type="primary"):
                with st.spinner("Verifying & counting..."):
                    output = count_votes()
                if output: st.success("✅ Done! See Results tab."); st.rerun()

    with tab_r:
        if not os.path.exists("results.json"): st.info("⏳ No results yet.")
        else:
            with open("results.json") as f: data = json.load(f)
            sm = data["summary"]
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total", sm["total"]); c2.metric("Valid", sm["valid"])
            c3.metric("Invalid", sm["invalid"]); c4.metric("Average", f"{sm['average']}/10")
            st.divider()
            vc = data.get("vote_counts",{})
            if vc:
                mx = max(vc.values())
                for g in sorted(vc, key=int):
                    cnt = vc[g]; bar = int((cnt/mx)*220)
                    st.markdown(
                        f'**{g}/10** &nbsp;<span style="background:#d35400;height:20px;'
                        f'width:{bar}px;display:inline-block;border-radius:4px;"></span>'
                        f'&nbsp; {cnt} vote{"s" if cnt>1 else ""}',
                        unsafe_allow_html=True)
            st.divider()
            for r in data.get("public_results",[]):
                st.markdown(f'{"✅" if r["valid"] else "❌"} `N2={r["N2"]}` → **{r["vote"]}**/10')

    with tab_v:
        with st.form("verify_form"):
            n2_check = st.text_input("Your N2 code").strip().upper()
            if st.form_submit_button("🔍 Verify", type="primary"):
                if not n2_check: st.error("❌ Enter N2.")
                elif not os.path.exists("results.json"): st.warning("⏳ No results yet.")
                else:
                    with open("results.json") as f: rdata = json.load(f)
                    found = False
                    for r in rdata.get("public_results",[]):
                        if r["N2"] == n2_check:
                            found = True
                            if r["valid"]: st.success(f"✅ Vote **{r['vote']}/10** counted!")
                            else:          st.error(f"❌ Rejected: {r.get('reason','')}")
                    if not found: st.warning("⚠️ N2 not found.")


# ═══════════════════════════════════════════════════════════
#  MAIN ROUTER
# ═══════════════════════════════════════════════════════════
app_state     = load_app_state()
phase         = app_state["phase"]
allowed_roles = PHASE_ACCESS[phase]

role = st.session_state.role
auth = st.session_state.authenticated

# ── Admin is always reachable (hidden login button) ─────────
if role == "admin":
    if not auth:
        show_login("admin")
    else:
        show_admin()
    st.stop()

# ── System offline: show closed screen ──────────────────────
if phase == "offline":
    show_system_offline(app_state)
    st.stop()

# ── Role not selected yet ────────────────────────────────────
if role is None:
    show_role_selection(allowed_roles, app_state)
    st.stop()

# ── Role selected but needs login ───────────────────────────
if role in ROLE_PASSWORDS and not auth:
    show_login(role)
    st.stop()

# ── Role not allowed in current phase ───────────────────────
if role not in allowed_roles:
    show_system_offline(app_state)
    st.stop()

# ── Route to the right panel ────────────────────────────────
if   role == "commissioner": show_commissioner()
elif role == "voter":        show_voter()
elif role == "anonymizer":   show_anonymizer()
elif role == "counter":      show_counter()
