"""
=============================================================
  streamlit_app.py — Electronic Voting System (Web UI)
  ENSTA Alger — Asymmetric Cryptography 2026
=============================================================
  Run with:
    streamlit run streamlit_app.py

  Make sure all original files are in the same directory:
    admin.py, commissioner.py, voter.py, anonymizer.py,
    counter.py, tth.py, email_sender.py
=============================================================
"""

import streamlit as st
import json
import os
import random

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="🗳️ Electronic Voting System",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1F4E79, #2980b9);
        color: white;
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }
    .status-card {
        background: #f8f9fa;
        border-left: 5px solid #1F4E79;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .status-ok   { border-left-color: #27ae60; background: #eafaf1; }
    .status-warn { border-left-color: #f39c12; background: #fef9e7; }
    .status-err  { border-left-color: #e74c3c; background: #fdedec; }
    .phase-box {
        background: #eaf4ff;
        border: 1.5px solid #2980b9;
        border-radius: 10px;
        padding: 18px 22px;
        margin: 12px 0;
    }
    .result-bar {
        background: #1F4E79;
        height: 22px;
        border-radius: 4px;
        display: inline-block;
    }
    .step-box {
        background: #f4f6f8;
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: monospace;
        font-size: 0.9em;
        margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Import backend modules ───────────────────────────────────
try:
    from commissioner import (
        load_data, save_data, load_emails, save_emails,
        load_codes, generate_all_codes, backup_emails,
        restore_emails_from_backup, request_voter_card,
        verify_voter, invalidate_N1
    )
    from admin import mask_vote, blind_sign, unmask_signature, verify_signature, get_valid_k_values, N, e
    from anonymizer import receive_ballot, load_urne
    from counter import count_votes, verify_my_vote
    from email_sender import save_config, load_config, test_connection
    from tth import compute_tth
    BACKEND_OK = True
except ImportError as ex:
    BACKEND_OK = False
    IMPORT_ERROR = str(ex)


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def get_status():
    email_ok    = load_config() is not None
    codes_ready = os.path.exists("codes.json")
    comm_ready  = os.path.exists("commissioner_data.json")
    data        = load_data() if comm_ready else {}
    used        = data.get("used_codes", {})
    is_open     = data.get("election_open", False)
    urne_size   = 0
    if os.path.exists("urne.json"):
        try:
            with open("urne.json") as f:
                content = f.read().strip()
                urne_size = len(json.loads(content)) if content else 0
        except:
            pass
    return {
        "email_ok":      email_ok,
        "codes_ready":   codes_ready,
        "is_open":       is_open,
        "nb_sent":       len(used),
        "nb_voted":      sum(1 for v in used.values() if v.get("has_voted")),
        "urne_size":     urne_size,
        "results_exist": os.path.exists("results.json"),
        "used_codes":    used,
    }


def status_badge(condition, true_label, false_label):
    color = "#27ae60" if condition else "#e74c3c"
    label = true_label if condition else false_label
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:0.85em;">{label}</span>'


# ═══════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🗳️ Voting System")
    st.markdown("**ENSTA Alger — Crypto 2026**")
    st.divider()

    if not BACKEND_OK:
        st.error(f"❌ Backend error:\n{IMPORT_ERROR}\n\nMake sure all .py files are in the same folder.")
        st.stop()

    s = get_status()

    st.markdown("### 📊 System Status")
    st.markdown(f"Gmail Config : {status_badge(s['email_ok'], '✅ Ready', '❌ Not set')}", unsafe_allow_html=True)
    st.markdown(f"Codes Generated : {status_badge(s['codes_ready'], '✅ Ready', '❌ No')}", unsafe_allow_html=True)
    st.markdown(f"Election : {status_badge(s['is_open'], '🟢 OPEN', '🔴 CLOSED')}", unsafe_allow_html=True)
    st.metric("Cards Sent",    s["nb_sent"])
    st.metric("Voted",         s["nb_voted"])
    st.metric("Ballots in Urne", s["urne_size"])
    st.metric("Results",       "✅ Done" if s["results_exist"] else "⏳ Not yet")

    st.divider()
    page = st.radio("📌 Navigation", [
        "🏠 Home",
        "📧 Email Setup",
        "👮 Commissioner",
        "🗳️ Vote",
        "📮 Anonymizer",
        "🔢 Counter & Results",
    ])


# ═══════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🗳️ Electronic Voting System</h1>
    <p>Asymmetric Cryptography — ENSTA Alger 2026 | Blind RSA Signature Protocol</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  HOME
# ═══════════════════════════════════════════════════════════

if page == "🏠 Home":
    s = get_status()

    st.subheader("📋 Election Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📧 Emails Registered", len(load_emails()))
    col2.metric("📮 Cards Sent",        s["nb_sent"])
    col3.metric("✅ Voted",             s["nb_voted"])
    col4.metric("📦 Ballots in Urne",   s["urne_size"])

    st.divider()
    st.subheader("🚦 Setup Checklist")

    steps = [
        (s["email_ok"],      "1. Gmail configured",        "Go to **Email Setup** first"),
        (s["codes_ready"],   "2. Codes generated",         "Go to **Commissioner → Generate Codes**"),
        (s["is_open"],       "3. Election is open",        "Go to **Commissioner → Open Election**"),
        (s["urne_size"] > 0, "4. Votes received",          "Students must vote"),
        (s["results_exist"], "5. Results counted",         "Go to **Counter & Results**"),
    ]
    for done, label, hint in steps:
        icon = "✅" if done else "⏳"
        color = "status-ok" if done else "status-warn"
        st.markdown(
            f'<div class="status-card {color}">{icon} <b>{label}</b>'
            + (f' — {hint}' if not done else '') +
            '</div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.subheader("📖 How It Works")
    with st.expander("See the full voting flow"):
        st.markdown("""
**1. Commissioner** generates one code pair (N1, N2) per voter and sends them by email.

**2. Voter** receives N1 + N2, enters them into the system to authenticate.

**3. Blind Signature (RSA, N=55)**:
- Voter masks vote: `m' = vote × k^e mod N`
- Admin signs blindly: `m'' = (m')^d mod N`  *(never sees the real vote!)*
- Voter unmasks: `s = m'' × k⁻¹ mod N`
- Voter verifies: `s^e mod N == vote ✅`

**4. Anonymizer** receives the signed ballot, strips N1 (anonymity!), stores it.

**5. Counter** verifies all signatures + TTH(N2), counts valid votes, publishes results.

**6. Anyone** can verify their vote using their personal N2 code.
        """)


# ═══════════════════════════════════════════════════════════
#  EMAIL SETUP
# ═══════════════════════════════════════════════════════════

elif page == "📧 Email Setup":
    st.subheader("📧 Gmail Configuration")

    cfg = load_config()
    if cfg:
        st.success(f"✅ Gmail already configured: **{cfg['gmail']}**")
        if st.button("🔄 Test Connection"):
            with st.spinner("Testing..."):
                ok = test_connection()
            if ok:
                st.success("✅ Connection successful!")
            else:
                st.error("❌ Connection failed. Check credentials.")
        st.divider()

    with st.expander("📋 How to get a Gmail App Password", expanded=not bool(cfg)):
        st.markdown("""
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. **Security** → **2-Step Verification** → Enable it
3. **Security** → **App passwords**
4. Select **Mail** → Generate
5. Copy the 16-character password (e.g. `xxxx xxxx xxxx xxxx`)
        """)

    with st.form("email_form"):
        gmail = st.text_input("Gmail address", placeholder="vote.ensta.2026@gmail.com",
                              value=cfg["gmail"] if cfg else "")
        pwd   = st.text_input("App Password (16 chars)", type="password")
        submitted = st.form_submit_button("💾 Save & Test")

    if submitted:
        gmail = gmail.strip()
        pwd   = pwd.strip().replace(" ", "")
        if not gmail or not pwd:
            st.error("❌ Both fields are required!")
        else:
            save_config(gmail, pwd)
            with st.spinner("Testing connection..."):
                ok = test_connection()
            if ok:
                st.success("✅ Email system ready!")
                st.rerun()
            else:
                st.error("❌ Connection failed. Check your credentials.")


# ═══════════════════════════════════════════════════════════
#  COMMISSIONER
# ═══════════════════════════════════════════════════════════

elif page == "👮 Commissioner":
    st.subheader("👮 Commissioner Panel")

    s    = get_status()
    data = load_data()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Emails", "⚙️ Generate Codes", "🟢 Open / 🔴 Close", "📊 Status", "♻️ Reset"
    ])

    # ── Tab 1: Manage emails ────────────────────────────────
    with tab1:
        st.markdown("### 📋 Voter Email List")
        emails = load_emails()
        st.info(f"**{len(emails)}** email(s) currently registered")

        # Add single email
        with st.form("add_email"):
            new_email = st.text_input("Add an email", placeholder="student@ensta.edu.dz")
            if st.form_submit_button("➕ Add"):
                new_email = new_email.strip().lower()
                if not new_email:
                    st.error("Enter a valid email.")
                elif new_email in emails:
                    st.warning("Already in the list.")
                else:
                    emails.append(new_email)
                    save_emails(emails)
                    st.success(f"✅ Added: {new_email}")
                    st.rerun()

        # Add multiple emails
        with st.expander("📂 Add multiple emails (one per line)"):
            bulk = st.text_area("Paste emails here (one per line)")
            if st.button("➕ Add All"):
                new_ones = [e.strip().lower() for e in bulk.splitlines() if e.strip()]
                added = 0
                for em in new_ones:
                    if em not in emails:
                        emails.append(em)
                        added += 1
                save_emails(emails)
                st.success(f"✅ Added {added} new email(s).")
                st.rerun()

        st.divider()
        if emails:
            st.markdown("**Current list:**")
            for i, em in enumerate(emails):
                col_a, col_b = st.columns([5, 1])
                col_a.write(f"`{i+1}.` {em}")
                if col_b.button("🗑️", key=f"del_{i}"):
                    emails.pop(i)
                    save_emails(emails)
                    st.rerun()
        else:
            st.warning("No emails registered yet.")

    # ── Tab 2: Generate codes ───────────────────────────────
    with tab2:
        st.markdown("### ⚙️ Generate Voter Codes")
        emails = load_emails()

        if s["is_open"]:
            st.error("❌ Cannot generate codes while election is open!")
        elif not emails:
            st.warning("⚠️ No emails registered. Add emails first (Emails tab).")
        else:
            st.info(f"Will generate **{len(emails)}** code pair(s), one per registered voter.")
            if st.button("🔑 Generate Codes", type="primary"):
                with st.spinner("Generating codes..."):
                    backup_emails()
                    generate_all_codes(len(emails))
                st.success(f"✅ {len(emails)} code pairs generated in `codes.json`")
                st.rerun()

        codes = load_codes()
        if codes:
            st.metric("Codes remaining in pool", len(codes))

    # ── Tab 3: Open / Close ─────────────────────────────────
    with tab3:
        st.markdown("### 🟢 Open / 🔴 Close Election")
        codes  = load_codes()
        emails = load_emails()

        if s["is_open"]:
            st.success("🟢 Election is currently **OPEN**")
            if st.button("🔴 Close Election", type="secondary"):
                data["election_open"] = False
                save_data(data)
                st.success("🔴 Election closed.")
                st.rerun()
        else:
            st.error("🔴 Election is currently **CLOSED**")
            if not s["email_ok"]:
                st.warning("⚠️ Configure Gmail first (Email Setup page).")
            elif not s["codes_ready"]:
                st.warning("⚠️ Generate codes first (Generate Codes tab).")
            else:
                if st.button("🟢 Open Election", type="primary"):
                    data["election_open"] = True
                    save_data(data)
                    st.success("✅ Election is now OPEN! Students can vote.")
                    st.rerun()

    # ── Tab 4: Status ───────────────────────────────────────
    with tab4:
        st.markdown("### 📊 Detailed Status")
        used = data.get("used_codes", {})
        voted = sum(1 for v in used.values() if v.get("has_voted"))

        col1, col2, col3 = st.columns(3)
        col1.metric("Emails left",  len(load_emails()))
        col2.metric("Cards sent",   len(used))
        col3.metric("Voted",        voted)

        if used:
            st.divider()
            st.markdown("**Voter progress:**")
            rows = []
            for em, info in used.items():
                rows.append({
                    "Email":  em,
                    "N1":     info.get("N1", ""),
                    "Voted":  "✅ Yes" if info.get("has_voted") else "⏳ No",
                })
            st.dataframe(rows, use_container_width=True)

    # ── Tab 5: Reset ────────────────────────────────────────
    with tab5:
        st.markdown("### ♻️ Reset for New Election")
        st.warning("""
**This will:**
- 🗑️ Delete all votes, codes, urne, results
- ✅ Restore emails.json from backup
- ✅ Keep email_config.json (Gmail stays configured)
        """)
        confirm = st.text_input("Type **RESET** to confirm")
        if st.button("♻️ Reset Now", type="secondary"):
            if confirm == "RESET":
                save_data({"election_open": False, "used_codes": {}})
                for f in ["codes.json", "urne.json", "ballots.json", "results.json"]:
                    if os.path.exists(f):
                        os.remove(f)
                restore_emails_from_backup()
                st.success("✅ Reset complete! Ready for a new election.")
                st.rerun()
            else:
                st.error("❌ Type RESET exactly to confirm.")


# ═══════════════════════════════════════════════════════════
#  VOTER
# ═══════════════════════════════════════════════════════════

elif page == "🗳️ Vote":
    st.subheader("🗳️ Voter Portal")

    s = get_status()

    # Pre-flight checks
    if not s["email_ok"]:
        st.error("❌ Gmail not configured! Ask the commissioner to set it up.")
        st.stop()
    if not s["codes_ready"]:
        st.error("❌ Codes not generated yet! Wait for the commissioner.")
        st.stop()
    if not s["is_open"]:
        st.error("❌ Election is not open yet! Wait for the commissioner.")
        st.stop()

    # ── Phase 1: Request card ───────────────────────────────
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    st.markdown("### 📨 Phase 1 — Request your Voter Card")
    st.markdown("Enter your registered **@ensta.edu.dz** email to receive N1 + N2.")

    with st.form("phase1_form"):
        email_input = st.text_input("Your email", placeholder="student@ensta.edu.dz")
        send_btn    = st.form_submit_button("📧 Send my Voter Card")

    if send_btn:
        email_input = email_input.strip().lower()
        if not email_input:
            st.error("❌ Email required!")
        else:
            with st.spinner("Checking registration and sending email..."):
                ok, reason = request_voter_card(email_input)
            if ok:
                st.success(f"✅ {reason}")
                st.info("📬 Check your inbox for N1 and N2, then proceed to Phase 2 below.")
            else:
                st.error(f"❌ {reason}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── Phase 2–5: Full voting flow ─────────────────────────
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    st.markdown("### 🔐 Phase 2–5 — Authenticate & Vote")
    st.markdown("Enter the **N1** and **N2** you received by email.")

    with st.form("vote_form"):
        n1_input   = st.text_input("N1 (identity code from email)").strip().upper()
        n2_input   = st.text_input("N2 (secret code from email)").strip().upper()
        vote_input = st.slider("Your rating (1 = worst, 10 = best)", 1, 10, 5)
        vote_btn   = st.form_submit_button("🗳️ Cast My Vote", type="primary")

    if vote_btn:
        if not n1_input or not n2_input:
            st.error("❌ N1 and N2 are required!")
        else:
            # Phase 2: verify identity
            with st.spinner("Verifying credentials..."):
                ok, reason = verify_voter(n1_input, n2_input)

            if not ok:
                st.error(f"❌ ACCESS DENIED: {reason}")
            else:
                st.success("✅ Identity verified!")

                # Phase 3: show vote
                st.markdown(f"**Your rating:** {vote_input}/10 {'⭐' * vote_input}")

                # Phase 4: Blind signature
                st.markdown("---")
                st.markdown("#### 🔏 Phase 4 — Blind Signature Protocol")
                st.markdown(f"RSA Parameters: `N={N}`, `e={e}`, `d=3`")

                valid_ks = get_valid_k_values()
                k = random.choice(valid_ks)

                # Step A
                m_prime = mask_vote(vote_input, k)
                st.markdown(
                    f'<div class="step-box">🎭 <b>Step A — Voter masks vote:</b><br>'
                    f'm\' = {vote_input} × {k}^{e} mod {N} = <b>{m_prime}</b><br>'
                    f'<i>(Admin sees {m_prime}, NOT {vote_input}!)</i></div>',
                    unsafe_allow_html=True
                )

                # Step B
                m_double_prime = blind_sign(m_prime)
                st.markdown(
                    f'<div class="step-box">✍️ <b>Step B — Admin signs blindly:</b><br>'
                    f'm\'\' = {m_prime}^3 mod {N} = <b>{m_double_prime}</b><br>'
                    f'<i>(Admin never saw vote={vote_input}!)</i></div>',
                    unsafe_allow_html=True
                )

                # Step C
                s_sig = unmask_signature(m_double_prime, k)
                st.markdown(
                    f'<div class="step-box">🔓 <b>Step C — Voter unmasks:</b><br>'
                    f's = {m_double_prime} × k⁻¹ mod {N} = <b>{s_sig}</b></div>',
                    unsafe_allow_html=True
                )

                # Step D
                valid = verify_signature(vote_input, s_sig)
                if valid:
                    st.markdown(
                        f'<div class="step-box" style="background:#eafaf1;border-color:#27ae60;">✅ <b>Step D — Signature verified:</b><br>'
                        f'{s_sig}^{e} mod {N} = {pow(s_sig, e, N)} == {vote_input} ✅</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.error("❌ Signature invalid! Vote rejected.")
                    st.stop()

                # Phase 5: Send to anonymizer
                import string as _string
                random_bits = ''.join(random.choices(_string.ascii_uppercase + _string.digits, k=8))
                ballot_str  = f"{vote_input}|{n2_input}|{random_bits}"
                tth_n2      = compute_tth(n2_input)

                ballot = {
                    "N1":          n1_input,
                    "N2":          n2_input,
                    "tth_n2":      tth_n2,
                    "vote":        vote_input,
                    "random_bits": random_bits,
                    "ballot_str":  ballot_str,
                    "signature":   s_sig,
                }

                ok2, reason2 = receive_ballot(ballot)
                if ok2:
                    st.success("🎉 Vote submitted successfully!")
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    col1.metric("Your vote", f"{vote_input}/10")
                    col2.metric("Signature", str(s_sig))
                    st.info(f"💡 **Save your N2 to verify your vote later:** `{n2_input}`")
                else:
                    st.error(f"❌ Anonymizer rejected ballot: {reason2}")

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  ANONYMIZER
# ═══════════════════════════════════════════════════════════

elif page == "📮 Anonymizer":
    st.subheader("📮 Anonymizer — Ballot Box")

    urne = load_urne()
    st.metric("Total ballots in urne", len(urne))
    st.info("ℹ️ N1 is **not stored** — voter anonymity is guaranteed after submission.")

    if not urne:
        st.warning("No ballots yet.")
    else:
        st.divider()
        st.markdown("### 📦 Ballots in Urne")
        for i, b in enumerate(urne):
            with st.expander(f"Ballot {i+1}"):
                st.markdown(f"**N2:** `{b.get('N2', 'N/A')}`")
                tth = b.get("tth_n2", "")
                st.markdown(f"**TTH(N2):** `{tth[:30]}...`" if tth else "**TTH(N2):** N/A")
                st.markdown(f"**Ballot string:** `{b.get('ballot_str', 'N/A')}`")
                st.markdown(f"**Signature:** `{b.get('signature', 'N/A')}`")


# ═══════════════════════════════════════════════════════════
#  COUNTER & RESULTS
# ═══════════════════════════════════════════════════════════

elif page == "🔢 Counter & Results":
    st.subheader("🔢 Vote Counter & Results")

    s = get_status()

    tab_count, tab_results, tab_verify = st.tabs([
        "🔢 Count Votes", "📊 Results", "🔍 Verify My Vote"
    ])

    with tab_count:
        if s["is_open"]:
            st.error("❌ Election is still open! Close it first (Commissioner page).")
        elif s["urne_size"] == 0:
            st.warning("⚠️ No ballots in urne yet.")
        else:
            st.info(f"**{s['urne_size']}** ballot(s) ready to count.")
            if st.button("🔢 Count All Votes", type="primary"):
                with st.spinner("Counting votes..."):
                    output = count_votes()
                if output:
                    st.success("✅ Counting complete! See Results tab.")
                    st.rerun()

    with tab_results:
        if not os.path.exists("results.json"):
            st.info("⏳ No results yet. Run counting first.")
        else:
            with open("results.json") as f:
                data = json.load(f)

            summary = data["summary"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Ballots", summary["total"])
            col2.metric("Valid Votes",   summary["valid"])
            col3.metric("Invalid",       summary["invalid"])
            col4.metric("Average Grade", f"{summary['average']}/10")

            st.divider()
            st.markdown("### 📊 Vote Breakdown")
            vote_counts = data.get("vote_counts", {})
            if vote_counts:
                max_count = max(vote_counts.values()) if vote_counts else 1
                for grade in sorted(vote_counts.keys(), key=int):
                    count = vote_counts[grade]
                    bar_w = int((count / max_count) * 200)
                    st.markdown(
                        f'**{grade}/10** &nbsp; '
                        f'<span class="result-bar" style="width:{bar_w}px;"></span>'
                        f' &nbsp; {count} vote{"s" if count > 1 else ""}',
                        unsafe_allow_html=True
                    )

            st.divider()
            st.markdown("### 🔍 Public (N2 → Vote) Pairs")
            st.markdown("Anyone can verify their vote using their N2 code.")
            for r in data.get("public_results", []):
                icon = "✅" if r["valid"] else "❌"
                st.markdown(f"{icon} `N2={r['N2']}` → vote = **{r['vote']}**")

            st.divider()
            with st.expander("📥 Download raw results (JSON)"):
                st.json(data)

    with tab_verify:
        st.markdown("### 🔍 Verify Your Vote")
        st.markdown("Enter your personal **N2** code to confirm your vote was counted.")

        with st.form("verify_form"):
            n2_check = st.text_input("Your N2 code").strip().upper()
            if st.form_submit_button("🔍 Verify"):
                if not n2_check:
                    st.error("❌ Enter your N2 code.")
                elif not os.path.exists("results.json"):
                    st.warning("⏳ Results not available yet.")
                else:
                    with open("results.json") as f:
                        rdata = json.load(f)
                    found = False
                    for r in rdata.get("public_results", []):
                        if r["N2"] == n2_check:
                            found = True
                            if r["valid"]:
                                st.success(f"✅ Your vote **{r['vote']}/10** was counted!")
                            else:
                                st.error(f"❌ Your ballot was rejected: {r.get('reason','')}")
                    if not found:
                        st.warning("⚠️ N2 not found in results.")