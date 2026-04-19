"""
platforms/freelancer/job_apply.py — Auto-bid on Freelancer.com projects
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
APPLIED_LOG = "logs/freelancer_bids.json"


def load_applied() -> set:
    if os.path.exists(APPLIED_LOG):
        try:
            with open(APPLIED_LOG) as f:
                return set(json.load(f).get("urls", []))
        except Exception:
            return set()
    return set()


def save_applied(url, title):
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
        details.append({"title": title, "url": url,
                         "bid_on": datetime.now().strftime("%Y-%m-%d %H:%M")})
    with open(APPLIED_LOG, "w") as f:
        json.dump({"urls": urls, "details": details}, f, indent=2)


def bid_on_projects(driver, matched_projects: list, config: dict) -> dict:
    """Entry-point — named bid_on_projects but aliased as apply_fn in agent_cloud."""
    fl_cfg    = config["platforms"]["freelancer"]
    daily_cap = fl_cfg.get("max_bids_per_day", 8)
    bid_days  = fl_cfg.get("bid_delivery_days", 7)
    proposal  = fl_cfg.get(
        "bid_proposal",
        "Hi! I have strong experience with the skills required for this project. "
        "I can deliver high-quality work within the timeline. Let's discuss the details!"
    )

    already_bid = load_applied()
    new_projects = [p for p in matched_projects if p["url"] not in already_bid]
    results = {"applied": [], "failed": [], "total_applied": 0}

    logger.info(f"📨 Freelancer: {len(new_projects)} new projects (cap: {daily_cap})")

    for project in new_projects:
        if results["total_applied"] >= daily_cap:
            logger.info("   ⏹️  Daily bid cap reached.")
            break

        title, url  = project["title"], project["url"]
        budget_str  = project.get("budget", "")
        bid_amount  = _calculate_bid(budget_str, fl_cfg)

        logger.info(f"   📩 Bidding: {title} | Budget: {budget_str} | My bid: ${bid_amount}")

        if _place_bid(driver, url, bid_amount, bid_days, proposal):
            save_applied(url, title)
            results["applied"].append({
                "title":   title,
                "company": "Freelancer Client",
                "score":   project["score"],
                "url":     url,
                "bid":     bid_amount
            })
            results["total_applied"] += 1
            logger.info("   ✅ Bid placed!")
        else:
            results["failed"].append({"title": title, "company": "Freelancer Client"})
            logger.warning("   ❌ Bid failed")

        time.sleep(random.uniform(12, 20))

    logger.info(f"✅ Freelancer: Placed {results['total_applied']} bids today")
    return results


def _calculate_bid(budget_str: str, fl_cfg: dict) -> int:
    """Parse budget string and calculate a competitive bid amount."""
    import re
    min_bid = fl_cfg.get("min_budget_usd", 50)
    try:
        nums = re.findall(r"[\d,]+", budget_str.replace(",", ""))
        nums = [int(n) for n in nums if n]
        if len(nums) >= 2:
            # Range like "$50 - $100" → bid at 85% of max
            return max(min_bid, int(nums[-1] * 0.85))
        elif len(nums) == 1:
            return max(min_bid, int(nums[0] * 0.9))
    except Exception:
        pass
    return min_bid


def _place_bid(driver, url: str, bid_amount: int,
               delivery_days: int, proposal: str) -> bool:
    try:
        driver.get(url)
        time.sleep(3)

        # Click "Place a Bid" button
        bid_btn = None
        for sel in [
            (By.XPATH, '//button[contains(text(),"Place a Bid")]'),
            (By.XPATH, '//a[contains(text(),"Place a Bid")]'),
            (By.CSS_SELECTOR, "app-place-bid button"),
            (By.XPATH, '//button[contains(@class,"bid-btn")]'),
        ]:
            try:
                bid_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(sel))
                break
            except Exception:
                continue

        if not bid_btn:
            logger.warning("      No bid button found.")
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", bid_btn)
        time.sleep(0.5)
        bid_btn.click()
        time.sleep(3)

        # ── Fill bid amount ──────────────────────────────────────────
        for sel in [
            'input[name="amount"]',
            'input[id*="amount"]',
            'input[placeholder*="amount" i]',
            'input[placeholder*="bid" i]',
        ]:
            try:
                amount_f = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                amount_f.clear()
                amount_f.send_keys(str(bid_amount))
                logger.info(f"      ✔ Bid amount: ${bid_amount}")
                break
            except Exception:
                continue

        # ── Fill delivery days ───────────────────────────────────────
        for sel in [
            'input[name="period"]',
            'input[id*="period"]',
            'input[placeholder*="days" i]',
        ]:
            try:
                period_f = driver.find_element(By.CSS_SELECTOR, sel)
                period_f.clear()
                period_f.send_keys(str(delivery_days))
                break
            except Exception:
                continue

        # ── Fill proposal / cover letter ─────────────────────────────
        for sel in [
            'textarea[name="description"]',
            'textarea[id*="description"]',
            'textarea[placeholder*="proposal" i]',
            'textarea[placeholder*="cover" i]',
            'fl-textarea textarea',
        ]:
            try:
                proposal_f = driver.find_element(By.CSS_SELECTOR, sel)
                proposal_f.clear()
                proposal_f.send_keys(proposal)
                logger.info("      ✔ Proposal filled")
                break
            except Exception:
                continue

        time.sleep(1)

        # ── Submit bid ───────────────────────────────────────────────
        for sel in [
            (By.XPATH, '//button[contains(text(),"Place Bid")]'),
            (By.XPATH, '//button[contains(text(),"Submit Bid")]'),
            (By.CSS_SELECTOR, 'button[type="submit"]'),
        ]:
            try:
                submit = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(sel))
                driver.execute_script("arguments[0].click();", submit)
                time.sleep(4)
                logger.info("      ✔ Bid submitted")
                return True
            except Exception:
                continue

        return False

    except Exception as e:
        logger.error(f"      Freelancer bid error: {e}")
        return False
