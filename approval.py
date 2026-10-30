import os
from neonize.utils import build_jid

def ask_approval(client, job: dict, score: int, daily_id: int):
    my_jid = build_jid(os.environ["YOUR_PHONE"])
    role = job.get('role') or 'Position'
    loc = job.get('location') or 'Not specified'
    phone = job.get("contact_phone")
    email = job.get("contact_email")

    contacts = []
    if phone:
        contacts.append(f"• WhatsApp: {phone}")
    if email:
        contacts.append(f"• Email: {email}")
    contact_str = "\n".join(contacts) if contacts else "• No contact parsed"

    lines = [
        f"🎯 Job Match #{daily_id} ({score}%): {role} @ {loc}",
        contact_str,
        "",
        "Reply with:",
    ]

    if phone and email:
        lines.append(f"• yes {daily_id} both   (Send to WhatsApp + Email)")
        lines.append(f"• yes {daily_id} wa     (WhatsApp only)")
        lines.append(f"• yes {daily_id} email  (Email only)")
    elif phone:
        lines.append(f"• yes {daily_id} wa     (Send via WhatsApp)")
    elif email:
        lines.append(f"• yes {daily_id} email  (Send via Email)")
    else:
        lines.append(f"• yes {daily_id} both")

    client.send_message(my_jid, message="\n".join(lines))
