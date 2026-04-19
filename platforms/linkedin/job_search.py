"""
platforms/linkedin/job_search.py — Search LinkedIn jobs
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
    cfg      = config["platforms"]["linkedin"]
    keywords = config["job_search"]["keywords"]
    location = config["profile"]["preferred_locations"][0]
    exp_level = cfg.get("experience_level", "2")  # 2=mid-senior, 1=entry

    all_jobs = []
    for keyword in keywords[:3]:
        logger.info(f"🔍 LinkedIn: Searching '{keyword}' in {location}...")
        jobs = _search_keyword(driver, keyword, location, exp_level)
        logger.info(f"   Found {len(jobs)} jobs")
        all_jobs.extend(jobs)
        time.sleep(3)

    seen, unique = set(), []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique.append(job)

    logger.info(f"📋 LinkedIn total unique jobs: {len(unique)}")
    return unique


def _search_keyword(driver, keyword, location, exp_level) -> list:
    jobs = []
    try:
        kw_enc  = quote_plus(keyword)
        loc_enc = quote_plus(location)
        # f_AL=true → Easy Apply only
        url = (f"https://www.linkedin.com/jobs/search/?keywords={kw_enc}"
               f"&location={loc_enc}&f_AL=true&f_E={exp_level}&sortBy=DD&f_TPR=r86400")
        driver.get(url)
        time.sleep(4)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search__results-list, .scaffold-layout__list"))
            )
        except TimeoutException:
            logger.warning(f"   ⚠️  No results for '{keyword}'")
            return []

        cards = driver.find_elements(By.CSS_SELECTOR,
            "li.jobs-search-results__list-item, .job-card-container")[:15]

        for card in cards:
            try:
                job = _extract_job(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

    except Exception as e:
        logger.error(f"   ❌ LinkedIn search error: {e}")

    return jobs


def _extract_job(card) -> dict:
    def safe(sel):
        try:
            return card.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            return ""

    def safe_href(sel):
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            href = el.get_attribute("href") or ""
            # Clean tracking params
            return href.split("?")[0] if href else ""
        except Exception:
            return ""

    title   = safe(".job-card-list__title, .jobs-unified-top-card__job-title, a.job-card-container__link")
    company = safe(".job-card-container__primary-description, .job-card-container__company-name")
    loc     = safe(".job-card-container__metadata-item, .job-card-list__footer-wrapper")
    url     = safe_href("a.job-card-container__link, a.job-card-list__title")

    if not title or not url:
        return None

    return {
        "platform": "linkedin",
        "title": title, "company": company, "location": loc,
        "exp": "", "salary": "", "skills": "",
        "url": url, "applied": False, "score": 0
    }
