"""
platforms/indeed/job_search.py — Search Indeed for jobs
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
        logger.info(f"🔍 Indeed: Searching '{keyword}' in {location}...")
        jobs = _search_keyword(driver, keyword, location)
        logger.info(f"   Found {len(jobs)} jobs")
        all_jobs.extend(jobs)
        time.sleep(3)

    seen, unique = set(), []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique.append(job)

    logger.info(f"📋 Indeed total unique: {len(unique)}")
    return unique


def _search_keyword(driver, keyword, location) -> list:
    jobs = []
    try:
        kw_enc  = quote_plus(keyword)
        loc_enc = quote_plus(location)
        # fromage=1 → posted last 1 day; iafilter=1 → Indeed Apply only
        url = (f"https://in.indeed.com/jobs?q={kw_enc}&l={loc_enc}"
               f"&fromage=1&iafilter=1&sort=date")
        driver.get(url)
        time.sleep(4)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job_seen_beacon, .jobsearch-ResultsList"))
            )
        except TimeoutException:
            logger.warning(f"   ⚠️  No results for '{keyword}'")
            return []

        cards = driver.find_elements(By.CSS_SELECTOR, ".job_seen_beacon")[:15]

        for card in cards:
            try:
                job = _extract_job(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

    except Exception as e:
        logger.error(f"   ❌ Indeed search error: {e}")

    return jobs


def _extract_job(card) -> dict:
    def safe(sel):
        try:
            return card.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            return ""

    def safe_href():
        try:
            a = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
            jk = a.get_attribute("data-jk") or ""
            return f"https://in.indeed.com/viewjob?jk={jk}" if jk else ""
        except Exception:
            return ""

    title   = safe("h2.jobTitle span")
    company = safe(".companyName, [data-testid='company-name']")
    loc     = safe(".companyLocation, [data-testid='text-location']")
    salary  = safe(".salary-snippet-container, .metadataContainer")
    url     = safe_href()

    if not title or not url:
        return None

    return {
        "platform": "indeed",
        "title": title, "company": company, "location": loc,
        "exp": "", "salary": salary, "skills": "",
        "url": url, "applied": False, "score": 0
    }
