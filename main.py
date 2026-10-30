import os, sys
from dotenv import load_dotenv

load_dotenv()

# Startup environment validation
REQUIRED_ENV_VARS = ["GROQ_API_KEY", "YOUR_PHONE", "TARGET_GROUP_JID"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var) or "your_" in os.environ.get(var, "")]

if missing_vars:
    print("\n" + "=" * 60)
    print("❌ CONFIGURATION ERROR")
    print("=" * 60)
    print(f"Missing or unconfigured environment variables: {', '.join(missing_vars)}")
    print("Please copy '.env.example' to '.env' and fill in your actual settings.")
    print("=" * 60 + "\n")
    sys.exit(1)

from whatsapp_bot import start_listener
from extract import extract_job
from fitcheck import fit_check
from db import (
    seen,
    save,
    get_today_str,
    get_next_daily_id,
    find_job_by_daily_id,
    get_latest_pending,
    update_status
)
from approval import ask_approval
from send import send_email, send_whatsapp

TARGET_JID = os.environ["TARGET_GROUP_JID"]
MY_PHONE = os.environ.get("YOUR_PHONE", "").replace("+", "").strip()

def parse_approval_command(text: str) -> tuple[int | None, str | None, str | None]:
    """
    Parses commands like:
    - yes 1 both
    - yes 1 wa
    - yes 1 email
    - yes 1
    - yes wa
    - yes
    Returns (daily_id, channel, error_message).
    Channel will be normalized to: 'both', 'wa', or 'email'.
    """
    tokens = text.strip().split()
    if not tokens or tokens[0].lower() != "yes":
        return None, None, "Not a yes command"

    args = tokens[1:]
    daily_id = None
    channel = None

    for arg in args:
        arg_clean = arg.lstrip("#").strip().lower()
        if arg_clean.isdigit():
            daily_id = int(arg_clean)
        elif arg_clean in ["wa", "whatsapp"]:
            channel = "wa"
        elif arg_clean in ["email", "mail"]:
            channel = "email"
        elif arg_clean in ["both", "all"]:
            channel = "both"
        else:
            return None, None, f"Unknown option '{arg}'. Usage: yes <id> <wa/email/both>"

    if not channel:
        channel = "both"

    return daily_id, channel, None

def handle_approval_reply(client, reply_jid: str, text: str):
    daily_id, channel, err = parse_approval_command(text)
    if err:
        client.send_message(
            reply_jid,
            message=f"{err}\nExample: 'yes 1 both', 'yes 1 wa', 'yes 1 email'"
        )
        return

    today_str = get_today_str()

    if daily_id is not None:
        job_data, lookup_err = find_job_by_daily_id(daily_id, today_str)
        if lookup_err == "already_sent":
            client.send_message(reply_jid, message=f"Job #{daily_id} has already been applied to today.")
            return
        elif lookup_err == "expired":
            client.send_message(
                reply_jid,
                message=f"Job #{daily_id} was from a previous day and has expired. Daily jobs can only be applied on the day they appear."
            )
            return
        elif lookup_err:
            client.send_message(
                reply_jid,
                message=f"Job #{daily_id} not found for today ({today_str})."
            )
            return
    else:
        # Default to latest pending job for today
        job_data = get_latest_pending(today_str)
        if not job_data:
            client.send_message(
                reply_jid,
                message=f"No pending job matches waiting for approval today ({today_str})."
            )
            return
        daily_id = job_data.get("daily_id")

    job = job_data["job"]
    msg_id = job_data["msg_id"]
    role_desc = job.get('role') or 'the position'

    phone = job.get("contact_phone")
    email = job.get("contact_email")

    sent_channels = []
    errors = []

    if channel in ["wa", "both"]:
        if phone:
            try:
                print(f"[Approval] Sending WhatsApp for Job #{daily_id} ('{role_desc}') to {phone}...")
                send_whatsapp(client, phone, job)
                sent_channels.append(f"WhatsApp ({phone})")
            except Exception as e:
                errors.append(f"WhatsApp: {e}")
        elif channel == "wa":
            client.send_message(
                reply_jid,
                message=f"Job #{daily_id} does not have a WhatsApp contact (Email available: {email or 'None'}). Reply 'yes {daily_id} email' to apply via email."
            )
            return

    if channel in ["email", "both"]:
        if email:
            try:
                print(f"[Approval] Sending Email for Job #{daily_id} ('{role_desc}') to {email}...")
                send_email(email, job)
                sent_channels.append(f"Email ({email})")
            except Exception as e:
                errors.append(f"Email: {e}")
        elif channel == "email":
            client.send_message(
                reply_jid,
                message=f"Job #{daily_id} does not have an email contact (WhatsApp available: {phone or 'None'}). Reply 'yes {daily_id} wa' to apply via WhatsApp."
            )
            return

    if sent_channels:
        update_status(msg_id, "sent")
        summary = " & ".join(sent_channels)
        reply_msg = f"Application sent for Job #{daily_id} ({role_desc}) via {summary}!"
        if errors:
            reply_msg += f"\n(Warnings: {'; '.join(errors)})"
        client.send_message(reply_jid, message=reply_msg)
        print(f"[Approval SUCCESS] {reply_msg}")
    elif errors:
        client.send_message(reply_jid, message=f"Failed to send Job #{daily_id}: {'; '.join(errors)}")
        print(f"[Approval ERROR] {errors}")
    else:
        client.send_message(
            reply_jid,
            message=f"No contact details found for Job #{daily_id}."
        )

def handle_message(client, jid, text, msg_id, is_group=False, is_from_me=False, sender_jid=""):
    # If not a group message, it's a direct message (DM / self-chat approval command)
    if not is_group:
        if text.strip().lower().startswith("yes"):
            print(f"[DM Command] Approval reply received: '{text.strip()}'")
            handle_approval_reply(client, jid, text)
        return

    # If it's a group, only process the target job group
    if jid != TARGET_JID:
        return

    if seen(msg_id):
        return

    print(f"\n[Group Post] New message in target group (ID: {msg_id})")
    job = extract_job(text)
    if not job.get("is_job_posting"):
        save(msg_id, job, 0, "not_job")
        print("[Group Post] Not a job posting, ignored.")
        return

    result = fit_check(job)
    score = result.get("score", 0)
    role_desc = job.get("role") or "Unspecified Role"
    print(f"[Fit Check] Score {score}/100: {role_desc} — {result.get('reason')}")

    today_str = get_today_str()

    if score < 50:
        save(msg_id, job, score, "skipped", job_date=today_str)
        print(f"[Skipped] Score {score} < 50.")
        return

    daily_id = get_next_daily_id(today_str)
    save(msg_id, job, score, "pending", daily_id=daily_id, job_date=today_str)
    print(f"[Pending Approval] Match found! Assigned Job #{daily_id} for today ({today_str}). Sending alert to your phone...")
    ask_approval(client, job, score, daily_id=daily_id)

def main():
    print(f"Starting bot listener on target group: {TARGET_JID}")
    start_listener(handle_message)

if __name__ == "__main__":
    main()
