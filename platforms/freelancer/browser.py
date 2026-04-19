"""
platforms/freelancer/browser.py — Freelancer.com login & profile update
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


class FreelancerBrowser:
    LOGIN_URL   = "https://www.freelancer.com/login"
    PROFILE_URL = "https://www.freelancer.com/u/me"

    def __init__(self, config: dict, headless: bool = True):
        self.config   = config
        self.email    = config["platforms"]["freelancer"]["email"]
        self.password = config["platforms"]["freelancer"]["password"]
        self.driver   = self._init_driver(headless)
        self.wait     = WebDriverWait(self.driver, 15)

    def _init_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.maximize_window()
        return driver

    def _save_screenshot(self, name: str):
        try:
            import os; os.makedirs("logs", exist_ok=True)
            self.driver.save_screenshot(f"logs/{name}")
        except Exception:
            pass

    def login(self) -> bool:
        logger.info("🔐 Freelancer: Logging in...")
        try:
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)

            email_f = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@type="email" or @name="email" or @id="username"]')
                )
            )
            email_f.clear()
            email_f.send_keys(self.email)

            pwd_f = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))
            )
            pwd_f.clear()
            pwd_f.send_keys(self.password)

            for sel in [
                (By.XPATH, '//button[@type="submit"]'),
                (By.XPATH, '//button[contains(text(),"Log In")]'),
                (By.XPATH, '//input[@type="submit"]'),
            ]:
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(sel)).click()
                    break
                except Exception:
                    continue

            time.sleep(5)
            url = self.driver.current_url

            if "login" not in url and "freelancer.com" in url:
                logger.info("✅ Freelancer login successful!")
                return True

            logger.error(f"❌ Freelancer login failed. URL: {url}")
            self._save_screenshot("freelancer_login_failed.png")
            return False

        except Exception as e:
            logger.error(f"❌ Freelancer login error: {e}")
            self._save_screenshot("freelancer_login_exception.png")
            return False

    def update_profile(self) -> bool:
        """Visit profile page to refresh online status."""
        logger.info("🔄 Freelancer: Refreshing profile activity...")
        try:
            self.driver.get(self.PROFILE_URL)
            time.sleep(4)
            logger.info("✅ Freelancer profile visited.")
            return True
        except Exception as e:
            logger.error(f"❌ Freelancer profile error: {e}")
            return False

    def close(self):
        try:
            self.driver.quit()
            logger.info("🔒 Freelancer browser closed.")
        except Exception:
            pass
