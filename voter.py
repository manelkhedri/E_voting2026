"""
=============================================================
  voter.py — The Voter
=============================================================
  FLOW:
    PHASE 1 : Enter email → receive N1+N2 by email
    PHASE 2 : Enter N1+N2 → verified by commissioner
    PHASE 3 : Choose vote (1-10)
    PHASE 4 : Blind signature shown step by step
    PHASE 5 : Send ballot to ANONYMIZER
=============================================================
"""
import json, os, random, string
from tth import compute_tth
from admin import mask_vote, blind_sign, unmask_signature, verify_signature, get_valid_k_values, N, e
from commissioner import request_voter_card, verify_voter
from anonymizer import receive_ballot


def generate_random_bits(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def voter_flow():
    print("\n" + "="*55)
    print("  🗳️  ELECTRONIC VOTING SYSTEM")
    print("  Asymmetric Cryptography Course Rating")
    print("="*55)

    if not os.path.exists("commissioner_data.json"):
        print("\n❌ System not ready. Contact the commissioner.")
        return

    # ══════════════════════════════════════════════════
    # PHASE 1 : REQUEST VOTER CARD BY EMAIL
    # ══════════════════════════════════════════════════
    print("\n" + "─"*55)
    print("  PHASE 1 — Request your voter card")
    print("─"*55)
    print("  Enter your @ensta.edu.dz email.\n")

    email = input("  Your email: ").strip().lower()
    if not email:
        print("❌ Email required!")
        return

    print(f"\n[SYSTEM] Checking '{email}'...")
    ok, reason = request_voter_card(email)
    if not ok:
        print(f"\n❌ {reason}")
        return

    print(f"\n✅ {reason}")
    print("  📧 Check your inbox!")
    input("\n  Press ENTER when you have your N1 and N2...")

    # ══════════════════════════════════════════════════
    # PHASE 2 : ENTER N1 + N2
    # ══════════════════════════════════════════════════
    print("\n" + "─"*55)
    print("  PHASE 2 — Enter credentials from email")
    print("─"*55)

    N1 = input("\n  Your N1 (from email): ").strip().upper()
    N2 = input("  Your N2 (from email): ").strip().upper()

    if not N1 or not N2:
        print("❌ N1 and N2 required!")
        return

    print(f"\n[SYSTEM] Verifying credentials...")
    ok, reason = verify_voter(N1, N2)
    if not ok:
        print(f"\n❌ ACCESS DENIED: {reason}")
        return
    print("✅ Identity verified! You can vote.")

    # ══════════════════════════════════════════════════
    # PHASE 3 : CHOOSE VOTE
    # ══════════════════════════════════════════════════
    print("\n" + "─"*55)
    print("  PHASE 3 — Choose your rating")
    print("─"*55)
    print("\n  Rate the Asymmetric Cryptography course:\n")
    for i in range(1, 11):
        print(f"   {i:2} — {'★' * i}")

    while True:
        try:
            vote = int(input("\n  Your rating (1-10): ").strip())
            if 1 <= vote <= 10: break
            print("  ❌ Enter between 1 and 10.")
        except ValueError:
            print("  ❌ Invalid input.")

    # ══════════════════════════════════════════════════
    # PHASE 4 : BLIND SIGNATURE
    # ══════════════════════════════════════════════════
    print("\n" + "─"*55)
    print("  PHASE 4 — Blind Signature Protocol")
    print(f"  RSA: N={N}, e={e}, d=3")
    print("─"*55)

    valid_ks = get_valid_k_values()
    k = random.choice(valid_ks)

    # STEP A : Voter masks vote
    print("\n  ┌─ STEP A : VOTER masks the vote ──────────────┐")
    m_prime = mask_vote(vote, k)
    print(f"  │  m'={m_prime} sent to Admin (Admin sees {m_prime}, NOT {vote}!)")
    print("  └──────────────────────────────────────────────┘")
    input("\n  [Admin receives m'... Press ENTER]")

    # STEP B : Admin signs blindly
    print("\n  ┌─ STEP B : ADMIN signs blindly ───────────────┐")
    m_double_prime = blind_sign(m_prime)
    print(f"  │  Admin returns m''={m_double_prime} (never saw vote={vote}!)")
    print("  └──────────────────────────────────────────────┘")

    # STEP C : Voter unmasks
    print("\n  ┌─ STEP C : VOTER unmasks signature ───────────┐")
    s = unmask_signature(m_double_prime, k)
    print(f"  │  Real signature s={s}")
    print("  └──────────────────────────────────────────────┘")

    # STEP D : Verify
    print("\n  ┌─ STEP D : VERIFY signature ───────────────────┐")
    valid = verify_signature(vote, s)
    if not valid:
        print("  │  ❌ Signature invalid! Ballot rejected.")
        print("  └──────────────────────────────────────────────┘")
        return
    print("  └──────────────────────────────────────────────┘")

    # ══════════════════════════════════════════════════
    # PHASE 5 : SEND TO ANONYMIZER
    # ══════════════════════════════════════════════════
    print("\n" + "─"*55)
    print("  PHASE 5 — Sending ballot to Anonymizer")
    print("─"*55)

    random_bits = generate_random_bits()
    ballot_str  = f"{vote}|{N2}|{random_bits}"
    tth_n2      = compute_tth(N2)

    ballot = {
        "N1":          N1,
        "N2":          N2,
        "tth_n2":      tth_n2,
        "vote":        vote,
        "random_bits": random_bits,
        "ballot_str":  ballot_str,
        "signature":   s,
    }

    # Send to anonymizer
    # Anonymizer verifies N1, invalidates it, stores ballot
    ok, reason = receive_ballot(ballot)
    if not ok:
        print(f"\n❌ Anonymizer rejected ballot: {reason}")
        return

    # FINAL SUMMARY
    print("\n" + "="*55)
    print("  ✅ VOTE SUBMITTED SUCCESSFULLY!")
    print("="*55)
    print(f"  Vote         : {vote}/10  {'★' * vote}")
    print(f"  k (masking)  : {k}")
    print(f"  m' (masked)  : {m_prime}   ← what admin saw")
    print(f"  m'' (signed) : {m_double_prime}")
    print(f"  s (signature): {s}")
    print(f"  Verify       : {s}^{e} mod {N} = {pow(s,e,N)} == {vote} ✅")
    print("="*55)
    print(f"\n  💡 Verify your vote later using N2: {N2}")


if __name__ == "__main__":
    voter_flow()