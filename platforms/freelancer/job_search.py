"""
platforms/freelancer/job_search.py — Search Freelancer.com for projects
"""

import time
import logging
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


def search_projects(driver, config: dict) -> list:
    """Entry-point — named search_projects but aliased as search_jobs in agent_cloud."""
    fl_cfg   = config["platforms"]["freelancer"]
    keywords = config["job_search"]["keywords"]
    budget   = fl_cfg.get("min_budget_usd", 50)

    all_projects = []
    for keyword in keywords[:3]:
        logger.info(f"🔍 Freelancer: Searching '{keyword}'...")
        projects = _search_keyword(driver, keyword, budget)
        logger.info(f"   Found {len(projects)} projects")
        all_projects.extend(projects)
        time.sleep(3)

    seen, unique = set(), []
    for p in all_projects:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    logger.info(f"📋 Freelancer total unique: {len(unique)}")
    return unique


def _search_keyword(driver, keyword: str, min_budget: int) -> list:
    projects = []
    try:
        kw_enc = quote_plus(keyword)
        # projectsOnly=true, sort by newest
        url = (f"https://www.freelancer.com/jobs/search/?q={kw_enc}"
               f"&projectsOnly=true&sort_by=time_updated&min_budget={min_budget}")
        driver.get(url)
        time.sleep(4)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".JobSearchCard-item, .search-result-item")
                )
            )
        except TimeoutException:
            logger.warning(f"   ⚠️  No results for '{keyword}'")
            return []

        cards = driver.find_elements(
            By.CSS_SELECTOR, ".JobSearchCard-item, .search-result-item"
        )[:15]

        for card in cards:
            try:
                project = _extract_project(card)
                if project:
                    projects.append(project)
            except Exception:
                continue

    except Exception as e:
        logger.error(f"   ❌ Freelancer search error: {e}")

    return projects


def _extract_project(card) -> dict:
    def safe(sel):
        try:
            return card.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            return ""

    def safe_href():
        try:
            a = card.find_element(By.CSS_SELECTOR,
                "a.JobSearchCard-primary-heading-link, a.search-result-heading")
            href = a.get_attribute("href") or ""
            return href if href.startswith("http") else f"https://www.freelancer.com{href}"
        except Exception:
            return ""

    title       = safe(".JobSearchCard-primary-heading-link, .search-result-heading")
    budget      = safe(".JobSearchCard-primary-price, .budget")
    skills      = safe(".JobSearchCard-primary-tagsLink, .skills")
    description = safe(".JobSearchCard-secondary-description, .project-description")
    bids        = safe(".JobSearchCard-secondary-bidsInfo, .bids-count")
    url         = safe_href()

    if not title or not url:
        return None

    return {
        "platform":    "freelancer",
        "title":       title,
        "company":     "Freelancer Client",
        "budget":      budget,
        "skills":      skills,
        "description": description,
        "bids":        bids,
        "location":    "Remote",
        "exp":         "",
        "salary":      budget,
        "url":         url,
        "applied":     False,
        "score":       0
    }
