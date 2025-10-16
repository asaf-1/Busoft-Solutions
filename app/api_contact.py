from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import os, smtplib
from email.message import EmailMessage
from starlette.concurrency import run_in_threadpool

# קלט מהטופס
class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)

app = FastAPI(title="Contact API")

def send_email_sync(subject: str, body: str, mail_to: str,
                    mail_from: str, smtp_host: str, smtp_port: int,
                    smtp_user: str | None, smtp_password: str | None,
                    use_tls: bool = True):
    import os, smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from               # חייב להיות ה-Single Sender המאומת
    msg["To"] = mail_to                   # המקבל (uri@busoft.co.il)
    msg["Reply-To"] = mail_to             # אפשר לשים כאן גם את כתובת השולח מהטופס
    msg.set_content(body, charset="utf-8")

    use_ssl = os.getenv("SMTP_SSL", "0") == "1"

    if use_ssl:
        # SSL מלא (פורט 465)
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as s:
            s.ehlo()
            if smtp_user and smtp_password:
                s.login(smtp_user, smtp_password)
            s.send_message(msg)
    else:
        # STARTTLS (פורט 587)
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as s:
            s.ehlo()
            if use_tls:
                s.starttls()
                s.ehlo()
            if smtp_user and smtp_password:
                s.login(smtp_user, smtp_password)
            s.send_message(msg)


@app.post("/contact")
async def contact(payload: ContactIn):
    # ENV
    MAIL_TO = os.getenv("MAIL_TO", "uri@busoft.co.il")
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@busoft.co.il")
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    DRY_RUN = os.getenv("DRY_RUN", "0")

    subject = f"פניית צור קשר מהאתר – {payload.name}"
    body = f"שם: {payload.name}\nאימייל: {payload.email}\n\nהודעה:\n{payload.message}"

    if DRY_RUN == "1" or not SMTP_HOST:
        print("--- DRY RUN / DEBUG ---")
        print("To:", MAIL_TO)
        print("From:", MAIL_FROM)
        print("Subject:", subject)
        print(body)
        return {"ok": True, "debug": True}

    try:
        await run_in_threadpool(
            send_email_sync, subject, body, MAIL_TO, MAIL_FROM,
            SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, True
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")
