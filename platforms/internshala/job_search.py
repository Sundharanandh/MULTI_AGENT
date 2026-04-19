"""
platforms/internshala/job_search.py — Search Internshala for jobs
"""

import time
import logging
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


def search_jobs(driver, config: dict) -> list:
    keywords = config["job_search"]["keywords"]
    location = config["profile"]["preferred_locations"][0]

    all_jobs = []
    for keyword in keywords[:3]:
        logger.info(f"🔍 Internshala: Searching '{keyword}'...")
        jobs = _search_keyword(driver, keyword, location)
        logger.info(f"   Found {len(jobs)} listings")
        all_jobs.extend(jobs)
        time.sleep(3)

    seen, unique = set(), []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique.append(job)

    logger.info(f"📋 Internshala total unique: {len(unique)}")
    return unique


def _search_keyword(driver, keyword, location) -> list:
    jobs = []
    try:
        kw_enc  = keyword.lower().replace(" ", "-")
        loc_enc = location.lower().replace(" ", "-")
        url = f"https://internshala.com/jobs/{kw_enc}-jobs-in-{loc_enc}"
        driver.get(url)
        time.sleep(4)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".internship_meta, #internship_list_container"))
            )
        except TimeoutException:
            logger.warning(f"   ⚠️  No results for '{keyword}'")
            return []

        cards = driver.find_elements(By.CSS_SELECTOR, ".individual_internship")[:15]

        for card in cards:
            try:
                job = _extract_job(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

    except Exception as e:
        logger.error(f"   ❌ Internshala search error: {e}")

    return jobs


def _extract_job(card) -> dict:
    def safe(sel):
        try:
            return card.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            return ""

    def safe_href():
        try:
            a = card.find_element(By.CSS_SELECTOR, "a.job-title-href, h3.job-internship-name a, .view_detail_button")
            href = a.get_attribute("href") or ""
            return href if href.startswith("http") else f"https://internshala.com{href}"
        except Exception:
            return ""

    title   = safe("h3.job-internship-name, .profile")
    company = safe(".company_name, .company-name")
    loc     = safe(".location_link, .locations span")
    salary  = safe(".stipend, .salary")
    skills  = safe(".skills, .tags span")
    url     = safe_href()

    if not title or not url:
        return None

    return {
        "platform": "internshala",
        "title": title, "company": company, "location": loc,
        "exp": "", "salary": salary, "skills": skills,
        "url": url, "applied": False, "score": 0
    }
