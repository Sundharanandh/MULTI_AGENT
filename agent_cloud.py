"""
agent_cloud.py — Multi-Platform Job Agent (LinkedIn + Indeed + Internshala + Freelancer)
Runs on GitHub Actions every day at 9:00 AM IST.

Phase activation (automatic, based on start date):
  Days  1–7  → Phase 1: Login + Profile Update on all platforms
  Days  8–14 → Phase 2: + Job Search + AI Matching (email results, no apply)
  Days 15+   → Phase 3: + Auto Apply / Bid (up to daily cap per platform)
"""

import json
import logging
import os
import sys
from datetime import datetime, date

from shared.resume_parser import extract_resume_text
from shared.job_matcher   import score_jobs
from shared.notifier      import send_daily_report

# Platform modules
from platforms.linkedin.browser    import LinkedInBrowser
from platforms.linkedin.job_search import search_jobs as linkedin_search
from platforms.linkedin.job_apply  import apply_to_jobs as linkedin_apply

from platforms.indeed.browser      import IndeedBrowser
from platforms.indeed.job_search   import search_jobs as indeed_search
from platforms.indeed.job_apply    import apply_to_jobs as indeed_apply

from platforms.internshala.browser    import IntershalaBrowser
from platforms.internshala.job_search import search_jobs as internshala_search
from platforms.internshala.job_apply  import apply_to_jobs as internshala_apply

from platforms.freelancer.browser    import FreelancerBrowser
from platforms.freelancer.job_search import search_projects as freelancer_search
from platforms.freelancer.job_apply  import bid_on_projects as freelancer_bid

# ── Logging ──────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.FileHandler("logs/agent_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)


def get_phase(config: dict) -> int:
    if os.environ.get("TEST_ALL_PHASES", "").lower() == "true":
        logger.info("🧪 TEST MODE — Running all 3 phases!")
        return 3

    start_str = config.get("agent_start_date")
    if not start_str:
        today = date.today().isoformat()
        config["agent_start_date"] = today
        save_config(config)
        logger.info(f"📅 First run! Start date: {today}")
        return 1

    start = date.fromisoformat(start_str)
    days  = (date.today() - start).days + 1
    phase = 1 if days <= 7 else (2 if days <= 14 else 3)
    logger.info(f"📅 Day {days} since {start_str} → Phase {phase}")
    return phase


def empty_report(platform: str) -> dict:
    return {
        "platform":       platform,
        "login_success":  False,
        "profile_updated":False,
        "jobs_found":     0,
        "jobs_matched":   0,
        "matched_jobs":   [],
        "total_applied":  0,
        "applied_jobs":   [],
        "failed_jobs":    [],
        "errors":         []
    }


def run_platform(platform_name, browser_cls, search_fn, apply_fn,
                 config, phase, resume_text) -> dict:
    """Generic runner for any platform."""
    report  = empty_report(platform_name)
    enabled = config["platforms"].get(platform_name, {}).get("enabled", False)

    if not enabled:
        logger.info(f"⏭️  {platform_name} is disabled in config — skipping.")
        return report

    logger.info(f"\n{'='*55}")
    logger.info(f"  🌐 Platform: {platform_name.upper()}")
    logger.info(f"{'='*55}")

    browser = browser_cls(config, headless=True)
    try:
        # ── Phase 1: Login + Profile ──────────────────────────────
        logger.info("── PHASE 1: Login & Profile Update ─────────")
        login_ok = browser.login()
        report["login_success"] = login_ok

        if not login_ok:
            report["errors"].append(f"{platform_name}: Login failed.")
            return report

        profile_ok = browser.update_profile()
        report["profile_updated"] = profile_ok
        logger.info("✅ Phase 1 done.")

        # ── Phase 2: Search + AI Match ────────────────────────────
        if phase >= 2:
            logger.info("── PHASE 2: Job Search & AI Matching ───────")
            jobs = search_fn(browser.driver, config)
            report["jobs_found"] = len(jobs)

            if jobs and resume_text:
                matched = score_jobs(jobs, resume_text, config)
                report["jobs_matched"] = len(matched)
                report["matched_jobs"] = matched
            logger.info("✅ Phase 2 done.")

        # ── Phase 3: Auto Apply ───────────────────────────────────
        if phase >= 3:
            logger.info("── PHASE 3: Auto Apply ──────────────────────")
            if report["matched_jobs"]:
                res = apply_fn(browser.driver, report["matched_jobs"], config)
                report["total_applied"] = res["total_applied"]
                report["applied_jobs"]  = res["applied"]
                report["failed_jobs"]   = res["failed"]
            else:
                logger.info("   No matched jobs to apply.")
            logger.info("✅ Phase 3 done.")

    except Exception as e:
        report["errors"].append(str(e))
        logger.error(f"❌ {platform_name} error: {e}")
    finally:
        browser.close()

    return report


def run():
    logger.info("=" * 55)
    logger.info("  🚀 Multi-Platform Job Agent — Daily Run")
    logger.info(f"  📅 {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')} UTC")
    logger.info("=" * 55)

    config = load_config()
    phase  = get_phase(config)

    # ── Load Resume ──────────────────────────────────────────────────
    resume_text = ""
    try:
        resume_text = extract_resume_text(config.get("resume_path", "resume.pdf"))
        logger.info("📄 Resume loaded successfully.")
    except Exception as e:
        logger.error(f"❌ Resume error: {e}")

    all_reports = []

    # ── LinkedIn ─────────────────────────────────────────────────────
    all_reports.append(run_platform(
        "linkedin", LinkedInBrowser, linkedin_search, linkedin_apply,
        config, phase, resume_text
    ))

    # ── Indeed ───────────────────────────────────────────────────────
    all_reports.append(run_platform(
        "indeed", IndeedBrowser, indeed_search, indeed_apply,
        config, phase, resume_text
    ))

    # ── Internshala ──────────────────────────────────────────────────
    all_reports.append(run_platform(
        "internshala", IntershalaBrowser, internshala_search, internshala_apply,
        config, phase, resume_text
    ))

    # ── Freelancer ───────────────────────────────────────────────────
    all_reports.append(run_platform(
        "freelancer", FreelancerBrowser, freelancer_search, freelancer_bid,
        config, phase, resume_text
    ))

    # ── Send Summary Email ───────────────────────────────────────────
    try:
        send_daily_report(config, all_reports, phase)
    except Exception as e:
        logger.error(f"Email failed: {e}")

    logger.info("=" * 55)
    logger.info("  🎉 All platforms done. Next run: tomorrow 9:00 AM IST")
    logger.info("=" * 55)


if __name__ == "__main__":
    run()
