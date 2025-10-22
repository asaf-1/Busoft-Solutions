# app/api_contact.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from email.message import EmailMessage
from email.utils import formataddr
from starlette.concurrency import run_in_threadpool
import os, smtplib

class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)

app = FastAPI(title="Contact API")

def _build_msg(subject: str, body: str, mail_to: str, mail_from: str, reply_to: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr(("Busoft", mail_from))  # שם תצוגה + הכתובת המאומתת ב-SendGrid
    msg["To"] = mail_to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body, subtype="plain", charset="utf-8")
    return msg

def _send_smtp_starttls(msg: EmailMessage, host: str, port: int, user: str | None, pwd: str | None):
    with smtplib.SMTP(host, port, timeout=25) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)

def _send_smtp_ssl(msg: EmailMessage, host: str, port_ssl: int, user: str | None, pwd: str | None):
    with smtplib.SMTP_SSL(host, port_ssl, timeout=25) as s:
        s.ehlo()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)

# ---- Fallback: שליחה דרך SendGrid HTTP API (443) ----
def _send_via_sendgrid_http(subject: str, body: str, mail_to: str, mail_from: str, reply_to: str | None, api_key: str):
    # לא צריך תלות כבדה; נשתמש ב-http.client כדי להימנע מתוספות,
    # אם כבר הוספת httpx—אפשר להחליף ל-httpx (ראה הערה למטה).
    import json, http.client
    payload = {
        "from": {"email": mail_from, "name": "Busoft"},
        "reply_to": {"email": reply_to or mail_from},
        "personalizations": [{"to": [{"email": mail_to}], "subject": subject}],
        "content": [{"type": "text/plain; charset=utf-8", "value": body}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    conn = http.client.HTTPSConnection("api.sendgrid.com", timeout=20)
    conn.request("POST", "/v3/mail/send", body=json.dumps(payload), headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode()
    if resp.status not in (200, 202):
        raise RuntimeError(f"SendGrid HTTP {resp.status}: {data[:300]}")

@app.post("/contact")
async def contact(payload: ContactIn):
    MAIL_TO = os.getenv("MAIL_TO", "uri@busoft.co.il")
    MAIL_FROM = os.getenv("MAIL_FROM", "asaf@busoft.co.il")  # חייב להיות Single Sender מאומת ב-SendGrid
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "apikey")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")              # ה-API Key
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY") or SMTP_PASSWORD  # מאפשר להשתמש באותו ערך
    DRY_RUN = os.getenv("DRY_RUN", "0")

    subject = f"פניית צור קשר מהאתר – {payload.name}"
    body = f"שם: {payload.name}\nאימייל: {payload.email}\n\nהודעה:\n{payload.message}"

    # DEV / אימון
    if DRY_RUN == "1":
        print("--- DRY RUN ---")
        print("From:", MAIL_FROM, "| To:", MAIL_TO)
        print(body)
        return {"ok": True, "debug": True}

    if not (MAIL_FROM and MAIL_TO and SENDGRID_API_KEY):
        raise HTTPException(status_code=500, detail="missing MAIL_FROM / MAIL_TO / API key")

    msg = _build_msg(subject, body, MAIL_TO, MAIL_FROM, reply_to=str(payload.email))

    # 1) ניסיון SMTP 587 (STARTTLS)
    try:
        await run_in_threadpool(_send_smtp_starttls, msg, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
        return {"ok": True, "via": "smtp587"}
    except Exception:
        pass

    # 2) ניסיון SMTP SSL 465
    try:
        await run_in_threadpool(_send_smtp_ssl, msg, SMTP_HOST, 465, SMTP_USER, SMTP_PASSWORD)
        return {"ok": True, "via": "smtp465"}
    except Exception:
        pass

    # 3) Fallback יציב: SendGrid HTTP API (443)
    try:
        await run_in_threadpool(_send_via_sendgrid_http, subject, body, MAIL_TO, MAIL_FROM, str(payload.email), SENDGRID_API_KEY)
        return {"ok": True, "via": "http"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"send failed: {type(e).__name__}: {e}")
