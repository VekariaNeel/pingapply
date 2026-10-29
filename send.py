import os, smtplib, re
from email.message import EmailMessage
from neonize.utils import build_jid

RESUME_PDF_PATH = "resume.pdf"

def _ensure_resume_pdf():
    if not os.path.exists(RESUME_PDF_PATH):
        raise FileNotFoundError(
            f"'{RESUME_PDF_PATH}' not found! Please place your resume PDF named 'resume.pdf' in the project root directory."
        )

def send_email(to: str, job: dict):
    _ensure_resume_pdf()
    role_name = job.get('role') or 'the position'
    msg = EmailMessage()
    msg["Subject"] = f"Application for {role_name}"
    msg["From"] = os.environ.get("GMAIL_USER", "")
    msg["To"] = to
    msg.set_content(
        f"Hi,\n\nI'm applying for the {role_name} role I saw posted. Resume attached.\n\nThanks,\nNeel"
    )

    with open(RESUME_PDF_PATH, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename="Resume.pdf"
        )

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)

def send_whatsapp(client, phone: str, job: dict):
    _ensure_resume_pdf()
    clean_phone = re.sub(r"[^\d]", "", phone)
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    jid = build_jid(clean_phone)
    role_name = job.get('role') or 'position'
    with open(RESUME_PDF_PATH, "rb") as f:
        resume_bytes = f.read()
    client.send_document(
        jid,
        resume_bytes,
        filename="Resume.pdf",
        mimetype="application/pdf",
        caption=f"Hi, I'm applying for the {role_name} I saw posted. Resume attached."
    )
