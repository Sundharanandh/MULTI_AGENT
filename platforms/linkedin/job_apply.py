"""
platforms/linkedin/job_apply.py — LinkedIn Easy Apply automation
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)
APPLIED_LOG = "logs/linkedin_applied.json"


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
    daily_cap = config["platforms"]["linkedin"].get("max_applications_per_day", 10)
    applied   = load_applied()
    new_jobs  = [j for j in matched_jobs if j["url"] not in applied]
    results   = {"applied": [], "failed": [], "total_applied": 0}

    logger.info(f"📨 LinkedIn: {len(new_jobs)} new jobs (cap: {daily_cap})")

    for job in new_jobs:
        if results["total_applied"] >= daily_cap:
            logger.info("   ⏹️  Daily cap reached.")
            break

        title, company, url = job["title"], job.get("company",""), job["url"]
        logger.info(f"   📩 Applying: {title} @ {company} (score: {job['score']})")

        if _easy_apply(driver, url, config):
            save_applied(url, title, company)
            results["applied"].append({"title": title, "company": company,
                                        "score": job["score"], "url": url})
            results["total_applied"] += 1
            logger.info("   ✅ Applied!")
        else:
            results["failed"].append({"title": title, "company": company})
            logger.warning("   ❌ Failed")

        time.sleep(random.uniform(10, 18))

    logger.info(f"✅ LinkedIn: Applied to {results['total_applied']} jobs")
    return results


def _easy_apply(driver, url: str, config: dict) -> bool:
    try:
        driver.get(url)
        time.sleep(3)

        # Click "Easy Apply" button
        btn = None
        for sel in [
            (By.CSS_SELECTOR, "button.jobs-apply-button"),
            (By.XPATH, '//button[contains(@aria-label,"Easy Apply")]'),
            (By.XPATH, '//button[contains(text(),"Easy Apply")]'),
        ]:
            try:
                btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(sel))
                break
            except Exception:
                continue

        if not btn:
            logger.warning("      No Easy Apply button found.")
            return False

        # Check if already applied
        if "applied" in btn.text.lower():
            logger.info("      Already applied.")
            return True

        btn.click()
        time.sleep(2)

        # Walk through multi-step form (max 5 steps)
        profile = config["profile"]
        for step in range(5):
            _fill_form_fields(driver, profile)
            time.sleep(1)

            # Try "Submit application"
            try:
                submit = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[contains(@aria-label,"Submit application")]')
                    )
                )
                submit.click()
                time.sleep(3)
                logger.info("      ✔ Submitted application")
                return True
            except TimeoutException:
                pass

            # Try "Next" / "Review"
            next_btn = None
            for sel in [
                (By.XPATH, '//button[contains(@aria-label,"Continue to next step")]'),
                (By.XPATH, '//button[contains(text(),"Next")]'),
                (By.XPATH, '//button[contains(text(),"Review")]'),
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
                break   # No next / submit — bail

        # Dismiss if not submitted
        _dismiss_modal(driver)
        return False

    except Exception as e:
        logger.error(f"      Easy Apply error: {e}")
        _dismiss_modal(driver)
        return False


def _fill_form_fields(driver, profile: dict):
    """Fill common Easy Apply form fields."""
    try:
        # Phone number
        phone_inputs = driver.find_elements(
            By.XPATH, '//input[@id[contains(.,"phoneNumber")] or @name[contains(.,"phone")]]'
        )
        for el in phone_inputs:
            if not el.get_attribute("value"):
                el.send_keys(profile.get("phone", ""))
    except Exception:
        pass

    try:
        # Years of experience (numeric inputs)
        exp_inputs = driver.find_elements(
            By.XPATH, '//input[@type="text" or @type="number"][contains(@id,"experience") or contains(@id,"years")]'
        )
        for el in exp_inputs:
            if not el.get_attribute("value"):
                el.clear()
                el.send_keys(str(profile.get("experience_years", "")))
    except Exception:
        pass


def _dismiss_modal(driver):
    try:
        discard = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[contains(@aria-label,"Dismiss") or contains(text(),"Discard")]')
            )
        )
        discard.click()
        time.sleep(1)
        confirm = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[contains(text(),"Discard")]')
            )
        )
        confirm.click()
    except Exception:
        pass
