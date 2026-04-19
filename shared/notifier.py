"""
shared/notifier.py — Multi-platform daily email report
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

PLATFORM_EMOJIS = {
    "linkedin":    "💼",
    "indeed":      "🔵",
    "internshala": "🎓",
    "freelancer":  "🧑‍💻",
}


def _platform_block(report: dict) -> str:
    name    = report["platform"]
    emoji   = PLATFORM_EMOJIS.get(name, "🌐")
    login   = "✅" if report.get("login_success")   else "❌"
    profile = "✅" if report.get("profile_updated") else "❌"
    found   = report.get("jobs_found", 0)
    matched = report.get("jobs_matched", 0)
    applied = report.get("total_applied", 0)

    matched_block = ""
    for job in report.get("matched_jobs", [])[:5]:
        matched_block += (
            f"\n    [{job.get('score',0):>3}/100] {job.get('title','?')} @ {job.get('company','N/A')}"
            f"\n           Reason : {job.get('reason','')}"
            f"\n           Link   : {job.get('url','')}  \n"
        )
    if not matched_block:
        matched_block = "    No matches today."

    applied_block = ""
    for job in report.get("applied_jobs", []):
        applied_block += f"\n    ✅ {job.get('title')} @ {job.get('company','N/A')}"
    if not applied_block:
        applied_block = "    None today."

    errors = report.get("errors", [])
    error_str = ", ".join(errors) if errors else "None"

    return f"""
{emoji} {name.upper()}
  Login: {login}  |  Profile: {profile}  |  Found: {found}  |  Matched: {matched}  |  Applied: {applied}
  
  Top Matches:
{matched_block}
  Applied Today:
{applied_block}
  Errors: {error_str}
"""


def send_daily_report(config: dict, reports: list, phase: int):
    try:
        sender       = config["notifications"]["email"]
        app_password = config["notifications"]["gmail_app_password"]
        subject      = f"[Job Agent] Daily Report — {datetime.now().strftime('%d %b %Y')}"

        total_applied = sum(r.get("total_applied", 0) for r in reports)
        total_matched = sum(r.get("jobs_matched",  0) for r in reports)
        total_found   = sum(r.get("jobs_found",    0) for r in reports)

        platforms_block = "\n".join(_platform_block(r) for r in reports)

        body = f"""
╔══════════════════════════════════════════════╗
   MULTI-PLATFORM JOB AGENT — DAILY REPORT
   {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}
   Phase {phase} Active
╚══════════════════════════════════════════════╝

📊 SUMMARY
  Total Jobs Found   : {total_found}
  Total Good Matches : {total_matched}
  Total Applied      : {total_applied}

═══════════════════════════════════════════════
  PER-PLATFORM BREAKDOWN
═══════════════════════════════════════════════
{platforms_block}

═══════════════════════════════════════════════
  Runs daily 9AM IST — GitHub Actions
═══════════════════════════════════════════════
"""

        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = sender
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, sender, msg.as_string())

        logger.info("📧 Daily report sent!")

    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
