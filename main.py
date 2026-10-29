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
from db import seen, save, get_pending_job, update_status
from approval import ask_approval
from send import send_email, send_whatsapp

TARGET_JID = os.environ["TARGET_GROUP_JID"]
MY_PHONE = os.environ.get("YOUR_PHONE", "").replace("+", "").strip()

def handle_approval_reply(client, reply_jid: str, text: str):
    text_clean = text.strip()
    text_lower = text_clean.lower()
    if not text_lower.startswith("yes"):
        return

    # Check if a custom contact was specified (e.g. "yes +91 81400 39454" or "yes hr@company.com")
    parts = text_clean.split(maxsplit=1)
    custom_contact = parts[1].strip() if len(parts) > 1 else None

    pending = get_pending_job(custom_contact)
    if not pending:
        client.send_message(reply_jid, message="No pending job application found.")
        return

    job = pending["job"]
    msg_id = pending["msg_id"]
    role_desc = job.get('role') or 'the position'

    phone = job.get("contact_phone")
    email = job.get("contact_email")

    sent_channels = []
    errors = []

    # If user explicitly provided a specific contact after "yes", send only to that target
    if custom_contact:
        if "@" in custom_contact:
            try:
                print(f"[Approval] Sending email for '{role_desc}' to {custom_contact}...")
                send_email(custom_contact, job)
                sent_channels.append(f"Email ({custom_contact})")
            except Exception as e:
                errors.append(f"Email to {custom_contact}: {e}")
        else:
            try:
                print(f"[Approval] Sending WhatsApp for '{role_desc}' to {custom_contact}...")
                send_whatsapp(client, custom_contact, job)
                sent_channels.append(f"WhatsApp ({custom_contact})")
            except Exception as e:
                errors.append(f"WhatsApp to {custom_contact}: {e}")
    else:
        # Default "yes": Send to BOTH WhatsApp and Email if available!
        if phone:
            try:
                print(f"[Approval] Sending WhatsApp for '{role_desc}' to {phone}...")
                send_whatsapp(client, phone, job)
                sent_channels.append(f"WhatsApp ({phone})")
            except Exception as e:
                errors.append(f"WhatsApp to {phone}: {e}")

        if email:
            try:
                print(f"[Approval] Sending email for '{role_desc}' to {email}...")
                send_email(email, job)
                sent_channels.append(f"Email ({email})")
            except Exception as e:
                errors.append(f"Email to {email}: {e}")

    if sent_channels:
        update_status(msg_id, "sent")
        summary = " & ".join(sent_channels)
        reply_msg = f"Application sent for {role_desc} via {summary}!"
        if errors:
            reply_msg += f"\n(Warnings: {'; '.join(errors)})"
        client.send_message(reply_jid, message=reply_msg)
        print(f"[Approval SUCCESS] {reply_msg}")
    elif errors:
        client.send_message(reply_jid, message=f"Failed to send application: {'; '.join(errors)}")
        print(f"[Approval ERROR] {errors}")
    else:
        client.send_message(
            reply_jid,
            message=f"No contact phone or email found for {role_desc}. Reply 'yes <phone/email>'."
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

    if score < 50:
        save(msg_id, job, score, "skipped")
        print(f"[Skipped] Score {score} < 50.")
        return

    save(msg_id, job, score, "pending")
    print(f"[Pending Approval] Match found! Sending alert to your phone...")
    ask_approval(client, job, score)

print(f"Starting bot listener on target group: {TARGET_JID}")
start_listener(handle_message)
