"""
platforms/internshala/job_apply.py — Internshala apply with cover letter
"""

import time
import logging
import json
import os
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)
APPLIED_LOG = "logs/internshala_applied.json"


def load_applied() -> set:
    if os.path.exists(APPLIED_LOG):
        try:
            with open(APPLIED_LOG) as f:
                return set(json.load(f).get("urls", []))
        except Exception:
            return set()
    return set()


def save_applied(url, title, company):
    os.makedirs("logs", exist_ok=True)
    data = {}
    if os.path.exists(APPLIED_LOG):
        try:
            with open(APPLIED_LOG) as f:
                data = json.load(f)
        except Exception:
            data = {}
    urls    = data.get("urls", [])
    details = data.get("details", [])
    if url not in urls:
        urls.append(url)
        details.append({"title": title, "company": company, "url": url,
                         "applied_on": datetime.now().strftime("%Y-%m-%d %H:%M")})
    with open(APPLIED_LOG, "w") as f:
        json.dump({"urls": urls, "details": details}, f, indent=2)


def apply_to_jobs(driver, matched_jobs: list, config: dict) -> dict:
    daily_cap    = config["platforms"]["internshala"].get("max_applications_per_day", 10)
    cover_letter = config["platforms"]["internshala"].get(
        "cover_letter",
        "I am highly interested in this position and confident that my skills align well with your requirements. I would love to contribute to your team."
    )
    applied  = load_applied()
    new_jobs = [j for j in matched_jobs if j["url"] not in applied]
    results  = {"applied": [], "failed": [], "total_applied": 0}

    logger.info(f"📨 Internshala: {len(new_jobs)} new jobs (cap: {daily_cap})")

    for job in new_jobs:
        if results["total_applied"] >= daily_cap:
            logger.info("   ⏹️  Daily cap reached.")
            break

        title, company, url = job["title"], job.get("company",""), job["url"]
        logger.info(f"   📩 Applying: {title} @ {company} (score: {job['score']})")

        if _apply_single(driver, url, cover_letter):
            save_applied(url, title, company)
            results["applied"].append({"title": title, "company": company,
                                        "score": job["score"], "url": url})
            results["total_applied"] += 1
            logger.info("   ✅ Applied!")
        else:
            results["failed"].append({"title": title, "company": company})
            logger.warning("   ❌ Failed")

        time.sleep(random.uniform(8, 15))

    logger.info(f"✅ Internshala: Applied to {results['total_applied']} jobs")
    return results


def _apply_single(driver, url: str, cover_letter: str) -> bool:
    try:
        driver.get(url)
        time.sleep(3)

        # Click Apply button
        apply_btn = None
        for sel in [
            (By.XPATH, '//button[contains(text(),"Apply now")]'),
            (By.ID,    "apply_button"),
            (By.CSS_SELECTOR, "#apply-button-container button"),
            (By.XPATH, '//button[contains(@class,"apply")]'),
        ]:
            try:
                apply_btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(sel))
                break
            except Exception:
                continue

        if not apply_btn:
            logger.warning("      No apply button found.")
            return False

        apply_btn.click()
        time.sleep(3)

        # Fill cover letter / "Why should you be hired?"
        for sel in [
            (By.ID,   "cover_letter_holder"),
            (By.CSS_SELECTOR, "textarea#cover_letter_holder"),
            (By.XPATH, '//textarea[contains(@placeholder,"cover letter") or contains(@placeholder,"Cover")]'),
            (By.XPATH, '//textarea[contains(@placeholder,"why")]'),
        ]:
            try:
                cl_field = WebDriverWait(driver, 6).until(EC.presence_of_element_located(sel))
                cl_field.clear()
                cl_field.send_keys(cover_letter)
                logger.info("      ✔ Cover letter filled")
                break
            except Exception:
                continue

        time.sleep(1)

        # Submit
        for sel in [
            (By.XPATH, '//input[@id="submit"]'),
            (By.XPATH, '//button[contains(text(),"Submit")]'),
            (By.CSS_SELECTOR, "input[type='submit']"),
        ]:
            try:
                submit = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(sel))
                driver.execute_script("arguments[0].click();", submit)
                time.sleep(3)
                logger.info("      ✔ Application submitted")
                return True
            except Exception:
                continue

        return False

    except Exception as e:
        logger.error(f"      Internshala apply error: {e}")
        return False
