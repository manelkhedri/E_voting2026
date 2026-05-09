"""
=============================================================
  counter.py — The Vote Counter (Décompteur)
=============================================================
  Role (from project PDF section 6.3):
    - Reads ballots from urne.json
    - Verifies each ballot signature (using admin public key)
    - Verifies each TTH(N2) with commissioner
    - Counts valid votes
    - Publishes results in results.json
    - Anyone can verify their vote using N2

  Security:
    - Knows the vote content BUT cannot link to voter
    - Knows N2 but voting period is closed
    - Admin no longer signs → cannot forge valid ballots
=============================================================
"""
import json
import os
from admin import verify_signature, e, N
from commissioner import verify_tth_n2

URNE_FILE    = "urne.json"
RESULTS_FILE = "results.json"


def load_urne() -> list:
    """Load ballots from urne.json."""
    if not os.path.exists(URNE_FILE):
        return []
    with open(URNE_FILE) as f:
        return json.load(f)


def count_votes() -> dict:
    """
    Count all votes from urne.json.

    Steps (from PDF section 6.5):
      1. Read all ballots from urne.json
      2. For each ballot:
         a. Verify signature using admin public key
         b. Verify TTH(N2) with commissioner
         c. If both valid → count the vote
      3. Save results to results.json
      4. Publish (N2, vote) pairs for public verification

    Returns:
      results dict with summary and ballot details
    """
    urne = load_urne()

    if not urne:
        print("[COUNTER] ❌ Urne is empty! No ballots to count.")
        return {}

    print(f"\n[COUNTER] 📦 {len(urne)} ballot(s) found. Counting...\n")

    results     = []
    vote_counts = {}
    valid       = 0
    invalid     = 0

    for i, ballot in enumerate(urne):
        print(f"  ── Ballot {i+1} ──────────────────────────────")

        vote       = ballot.get("vote")
        signature  = ballot.get("signature")
        N2         = ballot.get("N2")

        # Step 1: Verify blind signature
        sig_ok = verify_signature(vote, signature)
        print(f"     Blind signature : {'✅ Valid' if sig_ok else '❌ Invalid'}")

        # Step 2: Verify TTH(N2) with commissioner
        n2_ok = verify_tth_n2(N2)
        print(f"     TTH(N2)         : {'✅ Valid' if n2_ok else '❌ Invalid'}")

        if sig_ok and n2_ok:
            results.append({
                "N2":    N2,
                "vote":  vote,
                "valid": True
            })
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
            valid += 1
            print(f"     Result          : {vote}/10 ✅ COUNTED")
        else:
            results.append({
                "N2":    N2,
                "vote":  "?",
                "valid": False,
                "reason": "Invalid signature" if not sig_ok else "Invalid N2"
            })
            invalid += 1
            print(f"     Result          : ❌ REJECTED")

    # Calculate average
    avg = round(
        sum(r["vote"] for r in results if r["valid"]) / valid, 2
    ) if valid > 0 else 0

    # Build output
    output = {
        "summary": {
            "total":   len(urne),
            "valid":   valid,
            "invalid": invalid,
            "average": avg
        },
        "vote_counts": {str(k): v for k, v in sorted(vote_counts.items())},
        # Published pairs (N2, vote) — anyone can verify their vote
        "public_results": results
    }

    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=4)

    print(f"\n[COUNTER] 💾 Results saved to '{RESULTS_FILE}'")
    return output


def show_results():
    """Display results summary."""
    if not os.path.exists(RESULTS_FILE):
        print("\n[COUNTER] ⏳ No results yet. Run counting first.")
        return

    with open(RESULTS_FILE) as f:
        data = json.load(f)

    s = data["summary"]
    print("\n" + "="*55)
    print("  📊 ELECTION RESULTS")
    print("="*55)
    print(f"  Total ballots : {s['total']}")
    print(f"  Valid votes   : {s['valid']}")
    print(f"  Invalid       : {s['invalid']}")
    print(f"  Average grade : {s['average']}/10")
    print("\n  Breakdown:")
    for grade, count in data["vote_counts"].items():
        bar = "█" * count
        print(f"    {grade:2}/10 → {bar} ({count} vote{'s' if count>1 else ''})")

    print("\n" + "─"*55)
    print("  🔍 Public verification — (N2, Vote) pairs:")
    print("─"*55)
    for r in data["public_results"]:
        status = "✅" if r["valid"] else "❌"
        print(f"  {status} N2={r['N2']}  →  vote={r['vote']}")


def verify_my_vote(N2: str) -> bool:
    """
    Allow a voter to verify their vote was counted.
    Called with their personal N2 code.

    Parameters:
      N2 : voter's secret code

    Returns:
      True  → vote was counted correctly
      False → vote not found or rejected
    """
    if not os.path.exists(RESULTS_FILE):
        print("[COUNTER] ⏳ Results not available yet.")
        return False

    with open(RESULTS_FILE) as f:
        data = json.load(f)

    for r in data["public_results"]:
        if r["N2"] == N2:
            if r["valid"]:
                print(f"[COUNTER] ✅ Your vote ({r['vote']}/10) was counted!")
                return True
            else:
                print(f"[COUNTER] ❌ Your ballot was rejected: {r.get('reason','')}")
                return False

    print("[COUNTER] ⚠️  N2 not found in results.")
    return False


def counter_menu():
    """Interactive counter interface."""
    while True:
        urne_size     = len(load_urne())
        results_exist = os.path.exists(RESULTS_FILE)

        print("\n" + "="*55)
        print("  COUNTER — Electronic Voting System")
        print("="*55)
        print(f"  Ballots in urne : {urne_size}")
        print(f"  Results         : {'✅ Done' if results_exist else '⏳ Not yet'}")
        print("="*55)
        print("  1. Count votes (dépouillement)")
        print("  2. Show results")
        print("  3. Verify my vote (enter N2)")
        print("  4. Exit")
        print("="*55)
        choice = input("  Choose: ").strip()

        if choice == "1":
            if urne_size == 0:
                print("\n  ❌ No ballots in urne!")
                continue
            output = count_votes()
            if output:
                s = output["summary"]
                print("\n" + "="*55)
                print("  📊 COUNTING COMPLETE")
                print("="*55)
                print(f"  Total   : {s['total']}")
                print(f"  Valid   : {s['valid']}")
                print(f"  Invalid : {s['invalid']}")
                print(f"  Average : {s['average']}/10")
                print("\n  Breakdown:")
                for grade, count in output["vote_counts"].items():
                    print(f"    {grade:2}/10 → {'█' * count} ({count} vote{'s' if count>1 else ''})")
                print("="*55)

        elif choice == "2":
            show_results()

        elif choice == "3":
            N2 = input("\n  Enter your N2: ").strip().upper()
            verify_my_vote(N2)

        elif choice == "4":
            print("  Goodbye!")
            break
        else:
            print("  ❌ Invalid choice.")


if __name__ == "__main__":
    counter_menu()