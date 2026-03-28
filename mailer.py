"""
mailer.py — DailyNewsDrop
Handles all email: send digest, send post result, check replies via IMAP.
"""
import smtplib, imaplib, email, time
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.image     import MIMEImage
from pathlib import Path
from config import (GMAIL_ADDRESS, GMAIL_APP_PASS, NOTIFY_EMAIL,
                    BRAND_NAME, BRAND_SHORT, ACCENT_COLOR)


# ── Internal SMTP send ────────────────────────────────────────────────────────
def _send(msg):
    """Send via Gmail SMTP. Never raises — logs failure instead."""
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            recipients = [NOTIFY_EMAIL]
            s.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
        print(f"  [SMTP] ✓ Sent to {NOTIFY_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"  [SMTP] ✗ AUTH FAILED — check GMAIL_ADDRESS / GMAIL_APP_PASS: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"  [SMTP] ✗ Recipient refused ({NOTIFY_EMAIL}): {e}")
    except Exception as e:
        print(f"  [SMTP] ✗ Send failed: {e}")
    return False


# ── Send digest ───────────────────────────────────────────────────────────────
def send_digest(top_articles: list):
    """Send numbered digest to NOTIFY_EMAIL. User replies with numbers."""
    rows = ""
    for i, art in enumerate(top_articles, 1):
        src  = art.get("source", "")
        lang = "🇮🇳" if art.get("lang", "en") == "ta" else "🔵"
        rows += f"""
        <tr>
          <td style="padding:14px 16px;border-bottom:1px solid #1e1e2a;vertical-align:top;
                     font-size:28px;font-weight:700;color:{ACCENT_COLOR};width:44px">{i}</td>
          <td style="padding:14px 16px;border-bottom:1px solid #1e1e2a;">
            <div style="font-size:15px;font-weight:600;color:#F0F0F5;line-height:1.4">{art['title']}</div>
            <div style="font-size:12px;color:#606075;margin-top:4px">{lang} {src}</div>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#0a0a10;font-family:-apple-system,sans-serif">
<div style="max-width:600px;margin:0 auto">
  <div style="background:#111118;border-bottom:3px solid {ACCENT_COLOR};padding:20px 28px;display:flex;align-items:center;gap:12px">
    <div style="width:10px;height:10px;border-radius:50%;background:{ACCENT_COLOR}"></div>
    <span style="font-size:20px;font-weight:700;letter-spacing:3px;color:#fff">DAILY<span style="color:{ACCENT_COLOR}">NEWS</span>DROP</span>
    <span style="margin-left:auto;font-size:11px;color:#606075;letter-spacing:1px">TOP NEWS DIGEST</span>
  </div>
  <div style="padding:24px 28px 8px">
    <p style="font-size:15px;color:#9096b8;line-height:1.6;margin:0 0 20px">
      Here are today's top {len(top_articles)} stories. <strong style="color:#fff">Reply to this email</strong> with:
    </p>
    <div style="background:#111118;border-radius:10px;padding:16px 20px;margin-bottom:24px;border:1px solid #1e1e2a">
      <div style="font-size:13px;color:#9096b8;line-height:2">
        &bull; <strong style="color:#fff">1</strong> or <strong style="color:#fff">2,3</strong> &rarr; Generate posts for those stories<br>
        &bull; <strong style="color:#fff">all</strong> &rarr; Generate posts for all stories<br>
        &bull; <strong style="color:#fff">Any text or topic</strong> &rarr; Generate a custom post
      </div>
    </div>
  </div>
  <table style="width:100%;border-collapse:collapse;background:#0f0f16">
    {rows}
  </table>
  <div style="padding:20px 28px;font-size:12px;color:#404050;text-align:center;border-top:1px solid #1e1e2a">
    {BRAND_NAME} · Auto-refreshes every 2 hours
  </div>
</div>
</body></html>"""

    plain = (f"Top {len(top_articles)} stories. Reply with numbers (e.g. 1,3) to generate posts:\n\n" +
             "\n".join(f"{i}. {a['title']}" for i, a in enumerate(top_articles, 1)))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[DND] Top {len(top_articles)} Stories — Reply to Generate Posts"
    msg["From"]    = f"{BRAND_NAME} <{GMAIL_ADDRESS}>"
    msg["To"]      = NOTIFY_EMAIL
    msg["X-DND-Digest"] = "true"
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    ok = _send(msg)
    if ok:
        print(f"[Mailer] Digest sent to {NOTIFY_EMAIL} — {len(top_articles)} stories")
    else:
        print(f"[Mailer] ✗ Digest FAILED to send to {NOTIFY_EMAIL}")


# ── Send generated post result ────────────────────────────────────────────────
def send_post_result(post: dict, reply_to: str = ""):
    """Email the rendered post image back to NOTIFY_EMAIL."""
    img_path = post.get("post_image_path")
    headline = post.get("headline", "")
    caption  = post.get("caption", "")  # full caption, no truncation

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#0a0a10;font-family:-apple-system,sans-serif">
<div style="max-width:600px;margin:0 auto">
  <div style="background:#111118;border-bottom:3px solid {ACCENT_COLOR};padding:20px 28px">
    <span style="font-size:20px;font-weight:700;letter-spacing:3px;color:#fff">DAILY<span style="color:{ACCENT_COLOR}">NEWS</span>DROP</span>
    <span style="float:right;font-size:11px;color:#606075;letter-spacing:1px;line-height:2.5">POST READY</span>
  </div>
  <div style="padding:24px 28px">
    <div style="font-size:11px;color:{ACCENT_COLOR};font-weight:700;letter-spacing:2px;margin-bottom:8px">POST GENERATED</div>
    <div style="font-size:22px;font-weight:700;color:#F0F0F5;margin-bottom:16px">{headline}</div>
    <img src="cid:post_image" style="width:100%;border-radius:10px;margin-bottom:16px;display:block"/>
    <div style="background:#111118;border-radius:8px;padding:14px 16px;border:1px solid #1e1e2a">
      <div style="font-size:11px;color:#606075;letter-spacing:1px;margin-bottom:6px">CAPTION</div>
      <div style="font-size:13px;color:#9096b8;line-height:1.7;white-space:pre-wrap">{caption}</div>
    </div>
    <p style="font-size:13px;color:#606075;margin-top:16px">Reply with more numbers or a topic to generate more posts.</p>
  </div>
</div></body></html>"""

    # Build message — use "mixed" so image attachment works in all clients
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[DND] Post Ready: {headline[:50]}"
    msg["From"]    = f"{BRAND_NAME} <{GMAIL_ADDRESS}>"
    msg["To"]      = NOTIFY_EMAIL
    msg["X-DND-Post"] = "true"
    if reply_to:
        msg["In-Reply-To"] = reply_to
        msg["References"]  = reply_to

    # Text + HTML alternative part
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(f"Post ready: {headline}\n\nCaption:\n{caption}", "plain"))
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    # Attach post image
    if img_path and Path(img_path).exists():
        with open(img_path, "rb") as f:
            img = MIMEImage(f.read(), "png")
            img.add_header("Content-ID", "<post_image>")
            img.add_header("Content-Disposition", "inline", filename="post.png")
            msg.attach(img)
        print(f"  [Mailer] Attaching image: {img_path}")
    else:
        print(f"  [Mailer] ⚠ No image at {img_path} — sending without image")

    ok = _send(msg)
    if ok:
        print(f"[Mailer] Post result sent to {NOTIFY_EMAIL}: {headline[:50]}")
    else:
        print(f"[Mailer] ✗ Post result FAILED to send: {headline[:50]}")


# ── Status / error email ──────────────────────────────────────────────────────
def send_status(subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"]    = f"{BRAND_NAME} <{GMAIL_ADDRESS}>"
        msg["To"]      = NOTIFY_EMAIL
        msg.attach(MIMEText(body, "plain"))
        _send(msg)
    except Exception as e:
        print(f"[Mailer] Status email error: {e}")


# ── Check IMAP for replies ────────────────────────────────────────────────────
def check_for_replies() -> list[dict]:
    """
    Check Gmail IMAP for unread replies to DND digest emails.
    Returns list of {text, message_id} dicts.

    FIXES vs original:
    1. No FROM filter — user replies come from their personal email, not GMAIL_ADDRESS.
    2. Search 'DND' not '[DND]' — IMAP bracket handling is unreliable.
    3. Skip emails the bot sent itself (X-DND-Digest or X-DND-Post header).
    4. Detailed logging so you can see exactly what IMAP finds.
    """
    replies = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        mail.select("inbox")

        # Search for any UNSEEN email with DND in the subject.
        # Matches "[DND] Top 5 Stories..." and "Re: [DND] Top 5 Stories..."
        # Do NOT add FROM filter — your replies come from pvpraveen190505@gmail.com
        _, data = mail.search(None, 'UNSEEN SUBJECT "DND"')
        ids = data[0].split() if data[0] else []
        print(f"[Mailer] IMAP: {len(ids)} unread DND email(s) in inbox")

        for eid in ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subj   = msg.get("Subject", "")
            sender = msg.get("From",    "")

            # Skip emails the bot sent itself
            if msg.get("X-DND-Digest") or msg.get("X-DND-Post"):
                print(f"  [Mailer] Skipping own outgoing: {subj[:60]}")
                mail.store(eid, "+FLAGS", "\\Seen")
                continue

            # Also skip if it's from the bot address and not a reply
            if GMAIL_ADDRESS in sender and not subj.lower().startswith("re:"):
                print(f"  [Mailer] Skipping non-reply from bot: {subj[:60]}")
                mail.store(eid, "+FLAGS", "\\Seen")
                continue

            print(f"  [Mailer] Found reply from: {sender[:60]}")
            print(f"  [Mailer] Subject: {subj[:60]}")

            # Extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    cd = str(part.get("Content-Disposition", ""))
                    if ct == "text/plain" and "attachment" not in cd:
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                        except Exception:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            # Strip quoted text — keep only the new reply
            lines = []
            for line in body.strip().splitlines():
                s = line.strip()
                if s.startswith(">"):
                    break
                if s.startswith("On ") and ("wrote:" in s or "@" in s or "<" in s or "DailyNewsDrop" in s):
                    break
                if "wrote:" in s and len(s) < 80:
                    break
                if "-----" in s and "Original" in s:
                    break
                if s.startswith("From:") or s.startswith("Sent:") or s.startswith("Date:"):
                    break
                lines.append(line)

            reply_text = "\n".join(lines).strip()
            print(f"  [Mailer] Reply text: '{reply_text[:80]}'")

            if reply_text:
                replies.append({
                    "text":       reply_text,
                    "message_id": msg.get("Message-ID", ""),
                })

            mail.store(eid, "+FLAGS", "\\Seen")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"[Mailer] IMAP error (check credentials): {e}")
    except Exception as e:
        print(f"[Mailer] IMAP check error: {e}")

    return replies
