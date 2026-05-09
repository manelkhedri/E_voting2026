"""
tth.py — Toy Tetragraph Hash
Method: Merkle Tree + SHA256
"""
import hashlib


def hash_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def split_blocks(data: str, block_size: int = 16) -> list:
    data = data.upper().replace(" ", "").replace("-", "")
    while len(data) % block_size != 0:
        data += 'A'
    return [data[i:i + block_size] for i in range(0, len(data), block_size)]


def compute_tth(data: str) -> str:
    """
    Compute TTH hash using Merkle Tree + SHA256.
    
    Property (Exercise 3):
      ONE-WAY / Preimage resistance:
      Given TTH(N2), it is impossible to find N2.
      This prevents the commissioner from reconstructing
      valid N2 codes to stuff the ballot box.
    """
    blocks = split_blocks(data)
    hashes = [hash_data(b) for b in blocks]

    while len(hashes) > 1:
        new_hashes = []
        for i in range(0, len(hashes), 2):
            if i + 1 < len(hashes):
                combined = hashes[i] + hashes[i + 1]
            else:
                combined = hashes[i]
            new_hashes.append(hash_data(combined))
        hashes = new_hashes

    return hashes[0]


if __name__ == "__main__":
    print("=== TTH Test ===")
    n2 = "AF15GH258ZQP"
    h  = compute_tth(n2)
    print(f"TTH('{n2}') = {h[:30]}...")
    print(f"Deterministic : {compute_tth(n2) == h} ✅")
