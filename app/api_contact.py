# app/api_contact.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from email.message import EmailMessage
from email.utils import formataddr
from starlette.concurrency import run_in_threadpool
import os, smtplib, socket

class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)

app = FastAPI(title="Contact API")

def _build_msg(subject: str, body: str, mail_to: str, mail_from: str, reply_to: str|None=None) -> EmailMessage:
    msg = EmailMessage()
    # אם תרצה לתייג בשם העסק, אפשר לשים "Busoft" כשם התצוגה
    msg["From"] = formataddr(("Busoft", mail_from))
    msg["To"] = mail_to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body, subtype="plain", charset="utf-8")
    return msg

def _send_smtp_starttls(msg: EmailMessage, host: str, port: int, user: str|None, pwd: str|None):
    with smtplib.SMTP(host, port, timeout=25) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)

def _send_smtp_ssl(msg: EmailMessage, host: str, port_ssl: int, user: str|None, pwd: str|None):
    with smtplib.SMTP_SSL(host, port_ssl, timeout=25) as s:
        s.ehlo()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)

@app.post("/contact")
async def contact(payload: ContactIn):
    MAIL_TO = os.getenv("MAIL_TO", "uri@busoft.co.il")
    MAIL_FROM = os.getenv("MAIL_FROM", "asaf@busoft.co.il")  # חייב להיות מאומת ב-SendGrid
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "apikey")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # ה-API Key
    DRY_RUN = os.getenv("DRY_RUN", "0")

    subject = f"פניית צור קשר מהאתר – {payload.name}"
    body = f"שם: {payload.name}\nאימייל: {payload.email}\n\nהודעה:\n{payload.message}"

    # DEV / אימון
    if DRY_RUN == "1":
        print("--- DRY RUN ---")
        print("From:", MAIL_FROM, "| To:", MAIL_TO)
        print(body)
        return {"ok": True, "debug": True}

    if not (SMTP_HOST and SMTP_PASSWORD and MAIL_FROM and MAIL_TO):
        raise HTTPException(status_code=500, detail="SMTP/ENV missing")

    msg = _build_msg(subject, body, MAIL_TO, MAIL_FROM, reply_to=str(payload.email))

    try:
        # ניסיון 1: STARTTLS על 587
        await run_in_threadpool(_send_smtp_starttls, msg, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
        return {"ok": True}
    except Exception as e1:
        # ניסיון 2: SSL ישיר על 465 (SendGrid תומך בשניהם)
        try:
            await run_in_threadpool(_send_smtp_ssl, msg, SMTP_HOST, 465, SMTP_USER, SMTP_PASSWORD)
            return {"ok": True, "fallback": "ssl465"}
        except Exception as e2:
            # נחזיר שגיאה עם הודעה נקייה (בלי סודות)
            human = f"send failed: {type(e2).__name__}: {e2}"
            raise HTTPException(status_code=500, detail=human)
