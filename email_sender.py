"""
=============================================================
  email_sender.py — Email Service
=============================================================
  Sends voter cards (N1 + N2) to students by email.
  Uses Gmail SMTP with App Password.
=============================================================
"""
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ── Gmail Configuration ────────────────────────────────────
CONFIG_FILE = "email_config.json"


def save_config(gmail: str, app_password: str):
    """Save Gmail credentials to config file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "gmail":        gmail,
            "app_password": app_password
        }, f, indent=4)
    print(f"[EMAIL] ✅ Config saved to '{CONFIG_FILE}'")


def load_config() -> dict:
    """Load Gmail credentials from config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def test_connection() -> bool:
    """Test Gmail SMTP connection."""
    config = load_config()
    if not config:
        print("[EMAIL] ❌ No config found. Run setup first.")
        return False
    try:
        print("[EMAIL] 🔄 Testing Gmail connection...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(config["gmail"], config["app_password"])
        server.quit()
        print("[EMAIL] ✅ Connection successful!")
        return True
    except Exception as ex:
        print(f"[EMAIL] ❌ Connection failed: {ex}")
        return False


def send_voter_card(to_email: str, N1: str, N2: str) -> bool:
    """
    Send voter card (N1 + N2) to student by email.

    Parameters:
      to_email : student's email (ex: ahmed.benali@ensta.dz)
      N1       : voter code N1
      N2       : voter secret code N2

    Returns:
      True  → email sent successfully
      False → failed
    """
    config = load_config()
    if not config:
        print("[EMAIL] ❌ No email config found!")
        return False

    # ── Build email ────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🗳️ Your Voter Card — ENSTA Cryptography Vote 2026"
    msg["From"]    = config["gmail"]
    msg["To"]      = to_email

    # Plain text version
    text_body = f"""
Dear Student,

You are registered to vote in the ENSTA Cryptography Course Evaluation.

Here are your personal voting credentials:

  N1 (identity code) : {N1}
  N2 (secret code)   : {N2}

HOW TO VOTE:
  1. Go to the voting terminal
  2. Choose option 3 (Voter)
  3. Enter your N1 and N2
  4. Choose your rating (1-10)

IMPORTANT:
  - Keep your N2 secret! Never share it.
  - You can only vote once.
  - After voting, you can verify your vote using your N2.

Good luck!
ENSTA Alger — Cryptography Department 2026
    """

    # HTML version (nicer)
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">

        <div style="background: #1F4E79; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h1>🗳️ Electronic Voting System</h1>
            <p>ENSTA Alger — Cryptography Course Evaluation 2026</p>
        </div>

        <div style="padding: 20px;">
            <p>Dear Student,</p>
            <p>You are registered to vote. Here are your personal credentials:</p>

            <div style="background: #f0f7ff; border: 2px solid #1F4E79; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
                <h2 style="color: #1F4E79; margin-bottom: 20px;">🪪 YOUR VOTER CARD</h2>
                <table style="margin: auto; font-size: 1.1em;">
                    <tr>
                        <td style="padding: 10px; color: #555;">N1 (identity code):</td>
                        <td style="padding: 10px;">
                            <code style="background: #1F4E79; color: white; padding: 8px 15px; border-radius: 5px; font-size: 1.2em; letter-spacing: 2px;">
                                {N1}
                            </code>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; color: #555;">N2 (secret code):</td>
                        <td style="padding: 10px;">
                            <code style="background: #27ae60; color: white; padding: 8px 15px; border-radius: 5px; font-size: 1.2em; letter-spacing: 2px;">
                                {N2}
                            </code>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="background: #fff8e1; border-left: 4px solid #f39c12; padding: 15px; margin: 20px 0;">
                <h3 style="color: #f39c12; margin: 0 0 10px 0;">📋 How to Vote</h3>
                <ol>
                    <li>Go to the voting terminal</li>
                    <li>Choose option <strong>3 (Voter)</strong></li>
                    <li>Enter your <strong>N1</strong> and <strong>N2</strong></li>
                    <li>Choose your rating <strong>(1 to 10)</strong></li>
                </ol>
            </div>

            <div style="background: #fde8e8; border-left: 4px solid #e74c3c; padding: 15px; margin: 20px 0;">
                <h3 style="color: #e74c3c; margin: 0 0 10px 0;">⚠️ Important</h3>
                <ul>
                    <li>Keep your <strong>N2 secret</strong> — never share it!</li>
                    <li>You can only vote <strong>once</strong></li>
                    <li>After voting, verify using your <strong>N2</strong> in results</li>
                </ul>
            </div>

            <p style="color: #555; font-size: 0.9em; text-align: center; margin-top: 30px;">
                ENSTA Alger — Asymmetric Cryptography Department 2026<br>
                <em>This email was sent automatically. Do not reply.</em>
            </p>
        </div>

    </body>
    </html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    # ── Send email ─────────────────────────────────────────
    try:
        print(f"[EMAIL] 📧 Sending voter card to {to_email}...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(config["gmail"], config["app_password"])
        server.sendmail(config["gmail"], to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] ✅ Email sent to {to_email}!")
        return True
    except Exception as ex:
        print(f"[EMAIL] ❌ Failed to send email: {ex}")
        return False


def setup_email():
    """Interactive setup for Gmail credentials."""
    print("\n" + "=" * 55)
    print("  EMAIL SETUP — Gmail Configuration")
    print("=" * 55)
    print("""
  BEFORE CONTINUING — Setup Gmail App Password:
  ─────────────────────────────────────────────
  1. Go to: myaccount.google.com
  2. Security → 2-Step Verification → Enable it
  3. Security → App passwords
  4. Select "Mail" → Generate
  5. Copy the 16-character password (xxxx xxxx xxxx xxxx)
  ─────────────────────────────────────────────
    """)

    gmail = input("  Enter Gmail address (ex: vote.ensta.2026@gmail.com): ").strip()
    pwd   = input("  Enter App Password (16 chars, no spaces): ").strip().replace(" ", "")

    if not gmail or not pwd:
        print("  ❌ Email and password required!")
        return False

    save_config(gmail, pwd)

    # Test connection
    if test_connection():
        print("\n  ✅ Email system is ready!")
        return True
    else:
        print("\n  ❌ Connection failed. Check your credentials.")
        return False


if __name__ == "__main__":
    setup_email()
