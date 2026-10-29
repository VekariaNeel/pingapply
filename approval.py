import os
from neonize.utils import build_jid

def ask_approval(client, job: dict, score: int):
    my_jid = build_jid(os.environ["YOUR_PHONE"])
    role = job.get('role') or 'Position'
    loc = job.get('location') or 'Not specified'
    phone = job.get("contact_phone")
    email = job.get("contact_email")

    contacts = []
    if phone:
        contacts.append(f"Phone: {phone}")
    if email:
        contacts.append(f"Email: {email}")
    contact_str = " | ".join(contacts) if contacts else "None found"

    client.send_message(
        my_jid,
        message=(
            f"Job match ({score}%): {role} @ {loc}\n"
            f"Contacts: {contact_str}\n\n"
            f"• Reply \"yes\" to send to both (WhatsApp + Email)\n"
            f"• Reply \"yes <contact>\" to send only to a specific one"
        )
    )
