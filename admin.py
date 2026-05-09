"""
=============================================================
  admin.py — The Administrator
=============================================================
  Uses RSA with small parameters from the project:
    N = 55   (= 5 × 11)
    e = 27   (public key)
    d = 3    (private key, because 27×3 = 81 ≡ 1 mod 40)
    φ(N) = (5-1)(11-1) = 40

  BLIND SIGNATURE PROTOCOL (Exercise 1 & 2):
  
    VOTER side:
      1. Choose k coprime with N  (masking factor)
      2. Compute m' = vote * k^e mod N  (mask the vote)
      3. Send m' to admin  (admin sees m', NOT the vote!)
      4. Receive m'' from admin
      5. Compute s = m'' * k^(-1) mod N  (unmask)
      6. Verify: s^e mod N == vote  ✅
    
    ADMIN side:
      1. Receive m'  (just a number, cannot see the vote)
      2. Compute m'' = (m')^d mod N  (sign blindly)
      3. Return m'' to voter
=============================================================
"""
from math import gcd


# ── RSA Parameters (from Exercise 2) ──────────────────────
N = 55    # RSA modulus = 5 × 11
e = 27    # public key exponent
d = 3     # private key  (27 × 3 mod 40 = 1)

# Proof that d=3 is correct:
# φ(55) = (5-1)(11-1) = 40
# 27 × 3 = 81 = 2×40 + 1 ≡ 1 (mod 40) ✅


# ══════════════════════════════════════════════════════════
#   RSA CORE FUNCTIONS
# ══════════════════════════════════════════════════════════

def mod_inverse(k: int, n: int) -> int:
    """
    Compute modular inverse of k mod n.
    Finds x such that k*x ≡ 1 (mod n).
    Uses Extended Euclidean Algorithm.
    """
    if gcd(k, n) != 1:
        raise ValueError(f"k={k} is not coprime with N={n}!")

    # Extended Euclidean Algorithm
    old_r, r = k, n
    old_s, s = 1, 0

    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s

    result = old_s % n
    return result


def get_valid_k_values() -> list:
    """
    Return all valid masking factors k (coprime with N, 2 ≤ k ≤ N-1).
    Voter picks one of these randomly.
    """
    return [k for k in range(2, N) if gcd(k, N) == 1]


# ══════════════════════════════════════════════════════════
#   VOTER SIDE — Masking and Unmasking
# ══════════════════════════════════════════════════════════

def mask_vote(vote: int, k: int) -> int:
    """
    VOTER: Mask the vote before sending to admin.
    
    Formula: m' = vote * k^e mod N
    
    Parameters:
      vote : the real vote (1-10)
      k    : masking factor (coprime with N)
    
    Returns:
      m' : masked vote (sent to admin — admin cannot see real vote!)
    
    Example (Exercise 2):
      vote=7, k=8, e=27, N=55
      m' = 7 * 8^27 mod 55 = 14
    """
    if gcd(k, N) != 1:
        raise ValueError(f"k={k} must be coprime with N={N}!")
    if not (0 < vote < N):
        raise ValueError(f"vote={vote} must be between 1 and {N-1}!")

    m_prime = (vote * pow(k, e, N)) % N

    print(f"[VOTER]  🎭 Masking vote:")
    print(f"         vote={vote}, k={k}, e={e}, N={N}")
    print(f"         m' = {vote} × {k}^{e} mod {N} = {m_prime}")
    print(f"         Sending m'={m_prime} to admin (admin cannot see vote={vote}!)")

    return m_prime


def unmask_signature(m_double_prime: int, k: int) -> int:
    """
    VOTER: Unmask the signature received from admin.
    
    Formula: s = m'' × k^(-1) mod N
    
    This gives a valid RSA signature of the vote:
      s^e mod N == vote  ✅
    
    PROOF (Exercise 1):
      s = m'' × k^(-1) mod N
        = (m')^d × k^(-1) mod N
        = (vote × k^e)^d × k^(-1) mod N
        = vote^d × k^(e×d) × k^(-1) mod N
        = vote^d × k^1 × k^(-1) mod N   (since e×d ≡ 1 mod φ(N))
        = vote^d mod N
      → s IS the standard RSA signature of vote! ✅
    
    Parameters:
      m_double_prime : masked signature received from admin (m'')
      k              : same masking factor used in mask_vote()
    
    Returns:
      s : the real RSA signature of the vote
    """
    k_inv = mod_inverse(k, N)
    s     = (m_double_prime * k_inv) % N

    print(f"[VOTER]  🔓 Unmasking signature:")
    print(f"         m''={m_double_prime}, k^(-1)={k_inv}, N={N}")
    print(f"         s = {m_double_prime} × {k_inv} mod {N} = {s}")

    return s


# ══════════════════════════════════════════════════════════
#   ADMIN SIDE — Blind Signing
# ══════════════════════════════════════════════════════════

def blind_sign(m_prime: int) -> int:
    """
    ADMIN: Sign the masked vote WITHOUT seeing the real vote.
    
    Formula: m'' = (m')^d mod N
    
    Admin receives m' (just a number).
    Admin does NOT know the real vote!
    Admin signs anyway.
    
    Parameters:
      m_prime : masked vote received from voter
    
    Returns:
      m'' : masked signature (sent back to voter)
    
    Example (Exercise 2):
      m'=14, d=3, N=55
      m'' = 14^3 mod 55 = 2744 mod 55 = 49
    """
    if not (0 <= m_prime < N):
        raise ValueError(f"m'={m_prime} must be between 0 and {N-1}!")

    m_double_prime = pow(m_prime, d, N)

    print(f"[ADMIN]  ✍️  Blind signing:")
    print(f"         Received m'={m_prime} (admin does NOT see the real vote!)")
    print(f"         m'' = {m_prime}^{d} mod {N} = {m_double_prime}")
    print(f"         Returning m''={m_double_prime} to voter")

    return m_double_prime


# ══════════════════════════════════════════════════════════
#   VERIFICATION — Used by counter during counting
# ══════════════════════════════════════════════════════════

def verify_signature(vote: int, s: int) -> bool:
    """
    Verify that s is a valid RSA signature of vote.
    
    Check: s^e mod N == vote
    
    This is the standard RSA signature verification.
    Called by counter.py during counting.
    
    Parameters:
      vote : the claimed vote value
      s    : the signature to verify
    
    Returns:
      True  → signature is valid ✅
      False → signature is invalid ❌
    
    Example (Exercise 1 proof):
      s=13, e=27, N=55, vote=7
      13^27 mod 55 = 7 == vote ✅
    """
    check = pow(s, e, N)
    valid = (check == vote % N)

    if valid:
        print(f"[ADMIN]  ✅ Signature valid: {s}^{e} mod {N} = {check} == {vote}")
    else:
        print(f"[ADMIN]  ❌ Signature INVALID: {s}^{e} mod {N} = {check} ≠ {vote}")

    return valid


# ══════════════════════════════════════════════════════════
#   COMPLETE DEMO — Shows full blind signature flow
# ══════════════════════════════════════════════════════════

def demo_blind_signature(vote: int, k: int):
    """
    Full demonstration of the blind signature protocol.
    Shows every step clearly.
    """
    print("\n" + "=" * 55)
    print(f"  BLIND SIGNATURE DEMO")
    print(f"  N={N}, e={e}, d={d}")
    print(f"  vote={vote}, k={k}")
    print("=" * 55)

    # VOTER: mask
    print("\n── STEP 1: VOTER masks the vote ──")
    m_prime = mask_vote(vote, k)

    # ADMIN: blind sign
    print("\n── STEP 2: ADMIN signs blindly ──")
    m_double_prime = blind_sign(m_prime)

    # VOTER: unmask
    print("\n── STEP 3: VOTER unmasks signature ──")
    s = unmask_signature(m_double_prime, k)

    # VERIFY
    print("\n── STEP 4: VERIFY signature ──")
    valid = verify_signature(vote, s)

    # SUMMARY
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print(f"  Real vote      = {vote}  (admin NEVER saw this!)")
    print(f"  Masked vote m' = {m_prime}  (what admin saw)")
    print(f"  Masked sig m'' = {m_double_prime}")
    print(f"  Final sig  s   = {s}")
    print(f"  Verify s^e mod N = {pow(s,e,N)} == {vote} → {'✅ VALID' if valid else '❌ INVALID'}")
    print("=" * 55)

    return s, valid


if __name__ == "__main__":
    # Reproduce Exercise 2 from the project
    print("Exercise 2: N=55, e=27, d=3")
    print(f"Verify d: e×d mod φ(N) = {e}×{d} mod 40 = {(e*d) % 40} (should be 1) ✅")

    # Test with vote=7, k=8 (as in exercise)
    demo_blind_signature(vote=7, k=8)
