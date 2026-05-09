"""
=============================================================
  anonymizer.py — The Anonymizer
=============================================================
  Role (from project PDF section 6.1):
    - Receives signed ballots from voters
    - Acts like a ballot box (urne)
    - Verifies N1 with commissioner before accepting
    - Does NOT know the vote content (encrypted)
    - Stores ballots in urne.json

  Security:
    - Knows N1 but NOT N2
    - Vote is encrypted → cannot see content
    - Random bits in ballot → cannot link to voter later
=============================================================
"""
import json
import os
from commissioner import verify_voter, invalidate_N1

URNE_FILE = "urne.json"


def load_urne() -> list:
    """Load all ballots from urne.json."""
    if not os.path.exists(URNE_FILE):
        return []
    with open(URNE_FILE) as f:
        return json.load(f)


def save_urne(urne: list):
    """Save all ballots to urne.json."""
    with open(URNE_FILE, "w") as f:
        json.dump(urne, f, indent=4)


def receive_ballot(ballot: dict) -> tuple:
    """
    Receive a signed ballot from a voter.

    Steps (from PDF section 6.3):
      1. Verify N1 is valid with commissioner
      2. If valid → commissioner invalidates N1
      3. Store ballot in urne.json
      4. Anonymizer does NOT see the vote (it's in ballot_str)

    Parameters:
      ballot : dict containing:
        - N1          : voter identity code
        - N2          : voter secret code
        - vote        : the rating (1-10)
        - ballot_str  : "vote|N2|random_bits"
        - signature   : blind RSA signature
        - tth_n2      : TTH(N2) hash

    Returns:
      (True, "OK")       → ballot accepted
      (False, "reason")  → ballot rejected
    """
    N1 = ballot.get("N1", "")
    N2 = ballot.get("N2", "")

    print(f"\n[ANONYMIZER] 📨 Received ballot from N1={N1}")

    # Verify N1 + N2 with commissioner
    ok, reason = verify_voter(N1, N2)
    if not ok:
        print(f"[ANONYMIZER] ❌ Ballot rejected: {reason}")
        return False, reason

    # Invalidate N1 → cannot vote again
    invalidate_N1(N1)

    # Store ballot in urne
    # Note: anonymizer stores the ballot but removes N1
    # to ensure anonymity after this point
    anonymous_ballot = {
        "N2":         ballot.get("N2"),
        "tth_n2":     ballot.get("tth_n2"),
        "vote":       ballot.get("vote"),
        "ballot_str": ballot.get("ballot_str"),
        "signature":  ballot.get("signature"),
    }
    # N1 is NOT stored → anonymity guaranteed!

    urne = load_urne()
    urne.append(anonymous_ballot)
    save_urne(urne)

    print(f"[ANONYMIZER] ✅ Ballot accepted and stored in urne.json")
    print(f"[ANONYMIZER] ℹ️  N1 removed → voter is now anonymous")
    print(f"[ANONYMIZER] 📦 Total ballots in urne: {len(urne)}")

    return True, "Ballot accepted."


def get_urne_size() -> int:
    """Return number of ballots in urne."""
    return len(load_urne())


def anonymizer_menu():
    """Interactive anonymizer interface."""
    while True:
        urne = load_urne()
        print("\n" + "="*55)
        print("  ANONYMIZER — Electronic Voting System")
        print("="*55)
        print(f"  Ballots in urne : {len(urne)}")
        print("="*55)
        print("  1. Show urne status")
        print("  2. Exit")
        print("="*55)
        choice = input("  Choose: ").strip()

        if choice == "1":
            print(f"\n  📦 {len(urne)} ballot(s) in urne.json")
            print("  (Ballots are anonymous — N1 is not stored)")
            for i, b in enumerate(urne):
                print(f"\n  Ballot {i+1}:")
                print(f"    N2          : {b.get('N2')}")
                print(f"    TTH(N2)     : {b.get('tth_n2','')[:20]}...")
                print(f"    Ballot str  : {b.get('ballot_str')}")
                print(f"    Signature   : {b.get('signature')}...")

        elif choice == "2":
            print("  Goodbye!")
            break
        else:
            print("  ❌ Invalid choice.")


if __name__ == "__main__":
    anonymizer_menu()