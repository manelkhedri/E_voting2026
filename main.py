
import os, json
from commissioner import load_data, save_data, commissioner_menu
from voter import voter_flow
from email_sender import setup_email, load_config
from anonymizer import anonymizer_menu
from counter import counter_menu


def get_urne_size():
    """Safely get urne size."""
    try:
        if not os.path.exists("urne.json"):
            return 0
        with open("urne.json") as f:
            content = f.read().strip()
            if not content:
                return 0
            return len(json.loads(content))
    except:
        return 0


def get_status():
    email_ok    = load_config() is not None
    codes_ready = os.path.exists("codes.json")
    comm_ready  = os.path.exists("commissioner_data.json")
    data        = load_data() if comm_ready else {}
    used        = data.get("used_codes", {})
    is_open     = data.get("election_open", False)
    return {
        "email_ok":      email_ok,
        "codes_ready":   codes_ready,
        "is_open":       is_open,
        "nb_sent":       len(used),
        "nb_voted":      sum(1 for v in used.values() if v.get("has_voted")),
        "urne_size":     get_urne_size(),
        "results_exist": os.path.exists("results.json"),
    }


def print_status(s):
    print("\n  ┌─────────────────────────────────────────┐")
    print("  │           SYSTEM STATUS                 │")
    print("  ├─────────────────────────────────────────┤")
    print(f"  │  Gmail config   : {'✅ Ready' if s['email_ok'] else '❌ Not configured':<30}│")
    print(f"  │  Codes generated: {'✅ Ready' if s['codes_ready'] else '❌ Not yet':<30}│")
    print(f"  │  Election       : {'🟢 OPEN' if s['is_open'] else '🔴 CLOSED':<30}│")
    print(f"  │  Cards sent     : {str(s['nb_sent']):<30}│")
    print(f"  │  Voted          : {str(s['nb_voted']):<30}│")
    print(f"  │  Ballots in urne: {str(s['urne_size']):<30}│")
    print(f"  │  Results        : {'✅ Done' if s['results_exist'] else '⏳ Not yet':<30}│")
    print("  └─────────────────────────────────────────┘")


def main():
    while True:
        s = get_status()
        print("\n" + "="*55)
        print("  🗳️  ELECTRONIC VOTING SYSTEM")
        print("  Asymmetric Cryptography — ENSTA Alger 2026")
        print("="*55)
        print_status(s)

        # Warnings
        if not s["email_ok"]:
            print("\n  ⚠️  STEP 1: Setup Gmail first! (option 1)")
        if not s["codes_ready"]:
            print("  ⚠️  STEP 2: Generate codes! (option 2 → Commissioner → option 1)")
        if s["codes_ready"] and not s["is_open"]:
            print("  ⚠️  STEP 3: Open the election! (option 2 → Commissioner → option 2)")

        print("\n  1. 📧 Setup Gmail         (one time only)")
        print("  2. 👮 Commissioner        (generate codes / open / close / reset)")
        print("  3. 🗳️  Voter               (enter email → get card → vote)")
        print("  4. 📮 Anonymizer          (view ballot box)")
        print("  5. 🔢 Counter             (count votes after election closes)")
        print("  6. 🚪 Exit")
        print("="*55)

        choice = input("  Choose: ").strip()

        if choice == "1":
            setup_email()

        elif choice == "2":
            if not s["email_ok"]:
                print("\n  ❌ Setup Gmail first! (option 1)")
            else:
                commissioner_menu()

        elif choice == "3":
            if not s["email_ok"]:
                print("\n  ❌ Gmail not configured!")
            elif not s["codes_ready"]:
                print("\n  ❌ Codes not generated! Commissioner → option 1")
            elif not s["is_open"]:
                print("\n  ❌ Election not open yet! Commissioner → option 2")
            else:
                voter_flow()

        elif choice == "4":
            anonymizer_menu()

        elif choice == "5":
            if s["is_open"]:
                print("\n  ❌ Election still open! Close it first.")
            elif s["urne_size"] == 0:
                print("\n  ❌ No ballots in urne yet!")
            else:
                counter_menu()

        elif choice == "6":
            print("\n  Goodbye! 👋")
            break
        else:
            print("\n  ❌ Invalid choice.")


if __name__ == "__main__":
    main()