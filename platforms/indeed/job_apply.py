"""
platforms/indeed/job_apply.py — Indeed Apply automation (IndeedApply / Easily Apply)
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
APPLIED_LOG = "logs/indeed_applied.json"


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
    daily_cap = config["platforms"]["indeed"].get("max_applications_per_day", 10)
    applied   = load_applied()
    new_jobs  = [j for j in matched_jobs if j["url"] not in applied]
    results   = {"applied": [], "failed": [], "total_applied": 0}

    logger.info(f"📨 Indeed: {len(new_jobs)} new jobs (cap: {daily_cap})")

    for job in new_jobs:
        if results["total_applied"] >= daily_cap:
            logger.info("   ⏹️  Daily cap reached.")
            break

        title, company, url = job["title"], job.get("company",""), job["url"]
        logger.info(f"   📩 Applying: {title} @ {company} (score: {job['score']})")

        if _apply_single(driver, url, config):
            save_applied(url, title, company)
            results["applied"].append({"title": title, "company": company,
                                        "score": job["score"], "url": url})
            results["total_applied"] += 1
            logger.info("   ✅ Applied!")
        else:
            results["failed"].append({"title": title, "company": company})
            logger.warning("   ❌ Failed")

        time.sleep(random.uniform(10, 18))

    logger.info(f"✅ Indeed: Applied to {results['total_applied']} jobs")
    return results


def _apply_single(driver, url: str, config: dict) -> bool:
    try:
        driver.get(url)
        time.sleep(3)

        # Find Apply / Easily Apply button
        apply_btn = None
        for sel in [
            (By.XPATH, '//button[contains(@id,"indeedApplyButton")]'),
            (By.XPATH, '//button[contains(text(),"Apply now")]'),
            (By.XPATH, '//a[contains(text(),"Apply now")]'),
            (By.CSS_SELECTOR, '#applyButtonLinkContainer button'),
            (By.XPATH, '//button[contains(text(),"Easily Apply")]'),
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

        # Indeed Apply modal — walk through steps
        profile = config["profile"]
        for step in range(6):
            _fill_indeed_form(driver, profile, config)
            time.sleep(1)

            # Submit
            try:
                submit = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[contains(text(),"Submit your application") or contains(text(),"Submit application")]')
                    )
                )
                submit.click()
                time.sleep(3)
                logger.info("      ✔ Application submitted")
                return True
            except TimeoutException:
                pass

            # Continue
            next_btn = None
            for sel in [
                (By.XPATH, '//button[contains(text(),"Continue")]'),
                (By.XPATH, '//button[contains(text(),"Next")]'),
                (By.XPATH, '//button[@type="submit"]'),
            ]:
                try:
                    next_btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable(sel))
                    break
                except Exception:
                    continue

            if next_btn:
                next_btn.click()
                time.sleep(2)
            else:
                break

        return False

    except Exception as e:
        logger.error(f"      Indeed apply error: {e}")
        return False


def _fill_indeed_form(driver, profile: dict, config: dict):
    """Fill common Indeed apply form fields."""
    try:
        # Name fields
        for field_id in ["input-applicant.name", "input-applicant.firstName"]:
            try:
                el = driver.find_element(By.ID, field_id)
                if not el.get_attribute("value"):
                    el.send_keys(profile.get("name", ""))
            except Exception:
                pass

        # Phone
        for sel in ['input[name*="phone"]', 'input[id*="phone"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if not el.get_attribute("value"):
                    el.send_keys(profile.get("phone", ""))
            except Exception:
                pass

        # Years of experience
        for sel in ['input[id*="experience"]', 'input[name*="experience"]']:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if not el.get_attribute("value"):
                    el.clear()
                    el.send_keys(str(profile.get("experience_years", "")))
            except Exception:
                pass

    except Exception:
        pass
