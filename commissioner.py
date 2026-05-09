"""
=============================================================
  commissioner.py — The Voting Commissioner
=============================================================
  ELECTION LIFECYCLE:
  
  1. PREPARE  : Add emails to emails.json
                Generate codes (option 1)
  2. OPEN     : Open election (option 2)
  3. VOTE     : Students vote
  4. CLOSE    : Close election (option 3)
  5. COUNT    : counter.py counts votes
  6. RESULTS  : Published in results.json

  FOR A NEW ELECTION:
    Commissioner does RESET (option 5)
    → Restores emails.json from backup
    → Clears all votes and codes
    → Ready for a new election!
=============================================================
"""
import json, os, random, string
from tth import compute_tth
from email_sender import send_voter_card, load_config

EMAILS_FILE        = "emails.json"
EMAILS_BACKUP_FILE = "emails_backup.json"  # backup restored on reset
CODES_FILE         = "codes.json"
DATA_FILE          = "commissioner_data.json"


def generate_code(length=12):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"election_open": False, "used_codes": {}}
    with open(DATA_FILE) as f: return json.load(f)

def load_emails():
    if not os.path.exists(EMAILS_FILE): return []
    with open(EMAILS_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return [e.strip().lower() for e in data if e.strip()]
    return []

def save_emails(emails):
    clean = [e.strip().lower() for e in emails if e.strip()]
    with open(EMAILS_FILE, "w") as f: json.dump(clean, f, indent=4)

def load_codes():
    if not os.path.exists(CODES_FILE): return []
    with open(CODES_FILE) as f: return json.load(f)

def save_codes(codes):
    with open(CODES_FILE, "w") as f: json.dump(codes, f, indent=4)

def backup_emails():
    """Save a backup of emails.json for reset purposes."""
    emails = load_emails()
    with open(EMAILS_BACKUP_FILE, "w") as f:
        json.dump(emails, f, indent=4)
    print(f"[COMMISSIONER] 💾 Emails backup saved ({len(emails)} emails)")

def restore_emails_from_backup():
    """Restore emails.json from backup after reset."""
    if not os.path.exists(EMAILS_BACKUP_FILE):
        print("[COMMISSIONER] ⚠️  No backup found! Add emails manually.")
        return
    with open(EMAILS_BACKUP_FILE) as f:
        emails = json.load(f)
    save_emails(emails)
    print(f"[COMMISSIONER] ✅ Emails restored ({len(emails)} emails)")

def generate_all_codes(n):
    """Generate n code pairs and save to codes.json."""
    codes, used = [], set()
    for _ in range(n):
        N1 = generate_code()
        while N1 in used: N1 = generate_code()
        used.add(N1)
        codes.append({"N1": N1, "N2": generate_code()})
    save_codes(codes)
    print(f"[COMMISSIONER] ✅ {n} code pairs generated in '{CODES_FILE}'")


# ── Called by voter.py ─────────────────────────────────────

def request_voter_card(email: str) -> tuple:
    """Student enters email → system sends N1+N2 by email."""
    data  = load_data()
    email = email.strip().lower()

    if not data.get("election_open", False):
        return False, "Election is not open yet."

    # Card already sent → just confirm
    if email in data.get("used_codes", {}):
        info = data["used_codes"][email]
        if info.get("has_voted"):
            return False, "You already voted!"
        print(f"[COMMISSIONER] ℹ️  Card already sent to {email}")
        print(f"               N1 = {info['N1']}")
        return True, "Card already sent! Check your inbox and enter N1+N2."

    # First time → check email list
    emails = load_emails()
    if email not in emails:
        return False, f"'{email}' is not registered. Contact commissioner."

    codes = load_codes()
    if not codes:
        return False, "No codes available! Contact commissioner."

    N1     = codes[0]["N1"]
    N2     = codes[0]["N2"]
    tth_n2 = compute_tth(N2)

    # Send email
    ok = send_voter_card(email, N1, N2)
    if not ok:
        return False, "Failed to send email. Try again."

    # Remove email from list
    emails.remove(email)
    save_emails(emails)

    # Remove code from pool
    codes.pop(0)
    save_codes(codes)

    # Store N1 + TTH(N2) for voter verification
    if "used_codes" not in data:
        data["used_codes"] = {}
    data["used_codes"][email] = {
        "N1":        N1,
        "tth_n2":    tth_n2,
        "has_voted": False
    }
    save_data(data)

    remaining = len(emails)
    print(f"[COMMISSIONER] ✅ Card sent to {email} | N1={N1} | {remaining} remaining")
    return True, f"Card sent to {email}! Check your inbox."


def verify_voter(N1: str, N2: str) -> tuple:
    """Verify N1+N2. Called by voter.py."""
    data = load_data()
    if not data.get("election_open", False):
        return False, "Election is not open."
    for email, info in data.get("used_codes", {}).items():
        if info.get("N1") == N1:
            if info.get("has_voted"):
                return False, "You already voted!"
            if compute_tth(N2) != info.get("tth_n2", ""):
                return False, "N2 is incorrect. Check your email."
            return True, "OK"
    return False, f"N1 '{N1}' not found."


def invalidate_N1(N1: str):
    """Mark as voted. Called by anonymizer.py."""
    data = load_data()
    for email, info in data.get("used_codes", {}).items():
        if info.get("N1") == N1:
            data["used_codes"][email]["has_voted"] = True
            save_data(data)
            print(f"[COMMISSIONER] ✅ N1 '{N1}' invalidated.")
            return


def verify_tth_n2(N2: str) -> bool:
    """Called by counter.py during counting."""
    data = load_data()
    tth  = compute_tth(N2)
    return any(v.get("tth_n2") == tth for v in data.get("used_codes", {}).values())


# ── Commissioner menu ──────────────────────────────────────

def commissioner_menu():
    while True:
        data    = load_data()
        used    = data.get("used_codes", {})
        is_open = data.get("election_open", False)
        emails  = load_emails()
        codes   = load_codes()
        voted   = sum(1 for v in used.values() if v.get("has_voted"))
        email_ok = load_config() is not None
        backup_exists = os.path.exists(EMAILS_BACKUP_FILE)

        print("\n" + "="*55)
        print("  COMMISSIONER — Electronic Voting System")
        print("="*55)
        print(f"  Gmail           : {'✅ Ready' if email_ok else '❌ Not configured'}")
        print(f"  Emails left     : {len(emails)}")
        print(f"  Codes left      : {len(codes)}")
        print(f"  Cards sent      : {len(used)}")
        print(f"  Voted           : {voted}")
        print(f"  Election        : {'🟢 OPEN' if is_open else '🔴 CLOSED'}")
        print("="*55)
        print("  1. Generate codes (FIRST TIME ONLY per election)")
        print("  2. Open election")
        print("  3. Close election")
        print("  4. Show status")
        print("  5. ♻️  RESET for NEW election")
        print("  6. Exit")
        print("="*55)

        choice = input("  Choose: ").strip()

        if choice == "1":
            if is_open:
                print("\n  ❌ Cannot generate codes once election is open!")
                continue
            nb = len(emails)
            if nb == 0:
                print("\n  ❌ emails.json is empty!")
                continue
            if input(f"\n  Generate {nb} codes? (yes/no): ").strip().lower() == "yes":
                # Save backup before starting
                backup_emails()
                generate_all_codes(nb)

        elif choice == "2":
            if not emails and not codes:
                print("\n  ❌ Generate codes first!"); continue
            if not email_ok:
                print("\n  ❌ Setup Gmail first!"); continue
            if is_open:
                print("\n  ⚠️  Already open."); continue
            if input(f"\n  Open election? (yes/no): ").strip().lower() == "yes":
                data["election_open"] = True
                save_data(data)
                print("\n  ✅ Election OPEN!")
                print("  Students can now enter their email to get their card.")

        elif choice == "3":
            if not is_open:
                print("\n  ⚠️  Already closed."); continue
            if input("\n  Close election? (yes/no): ").strip().lower() == "yes":
                data["election_open"] = False
                save_data(data)
                print("\n  🔴 Election CLOSED.")
                print("  Run counter.py to count votes.")

        elif choice == "4":
            print(f"\n  Emails remaining : {len(emails)}")
            print(f"  Codes remaining  : {len(codes)}")
            print(f"  Cards sent       : {len(used)}")
            print(f"  Voted            : {voted}")
            if used:
                print("\n  ┌──────────────────────────────┬─────────┐")
                print("  │ Email                        │ Voted   │")
                print("  ├──────────────────────────────┼─────────┤")
                for em, info in used.items():
                    v = "✅ Yes" if info.get("has_voted") else "⏳ No"
                    print(f"  │ {em:<28} │ {v:<7} │")
                print("  └──────────────────────────────┴─────────┘")

        elif choice == "5":
            print("\n" + "="*55)
            print("  ♻️  RESET — Start a NEW election")
            print("="*55)
            print("  This will:")
            print("  ✅ Restore emails.json from backup")
            print("  🗑️  Delete all votes and codes")
            print("  🗑️  Delete commissioner_data.json")
            print("  🗑️  Delete codes.json")
            print("  🗑️  Delete urne.json")
            print("  🗑️  Delete results.json")
            print("  ✅ Keep email_config.json (Gmail config)")
            print("="*55)

            if not backup_exists:
                print("\n  ⚠️  WARNING: No backup found!")
                print("  You will need to add emails manually after reset.")

            confirm = input("\n  Are you sure? Type 'RESET' to confirm: ").strip()
            if confirm == "RESET":
                # Clear all election data
                save_data({"election_open": False, "used_codes": {}})
                for f in ["codes.json", "urne.json", "ballots.json", "results.json"]:
                    if os.path.exists(f):
                        os.remove(f)
                        print(f"  🗑️  Deleted {f}")

                # Restore emails from backup
                restore_emails_from_backup()

                print("\n  ✅ RESET COMPLETE!")
                print("  → Run option 1 to generate new codes")
                print("  → Run option 2 to open new election")
            else:
                print("\n  ❌ Reset cancelled.")

        elif choice == "6":
            print("  Goodbye!")
            break
        else:
            print("  ❌ Invalid.")


if __name__ == "__main__":
    commissioner_menu()