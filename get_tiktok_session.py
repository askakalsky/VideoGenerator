"""
Logs into TikTok automatically, pauses for captcha if needed,
then saves all cookies as TIKTOK_COOKIES secret for GitHub Actions.

Usage:
    python get_tiktok_session.py
"""

import json
import os
import random
import subprocess
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TIKTOK_EMAIL = os.environ.get("TIKTOK_EMAIL", "")
TIKTOK_PASSWORD = os.environ.get("TIKTOK_PASSWORD", "")


def slow_type(element, text: str):
    for char in text:
        element.type(char)
        time.sleep(random.uniform(0.05, 0.18))


def main():
    email = TIKTOK_EMAIL or input("TikTok email: ").strip()
    password = TIKTOK_PASSWORD or input("TikTok password: ").strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="ru-RU",
        )
        page = context.new_page()

        print("Opening TikTok login...")
        page.goto("https://www.tiktok.com/login", wait_until="networkidle")
        time.sleep(random.uniform(1.5, 2.5))

        page.get_by_role("link", name="Введите телефон/эл. почту/имя пользователя").click()
        time.sleep(random.uniform(0.5, 1.0))

        page.get_by_role("link", name="Войти через эл. почту или имя пользователя").click()
        time.sleep(random.uniform(0.8, 1.5))

        email_box = page.get_by_role("textbox", name="Почта или имя пользователя")
        email_box.click()
        time.sleep(random.uniform(0.3, 0.7))
        slow_type(email_box, email)
        time.sleep(random.uniform(0.5, 1.0))

        pass_box = page.get_by_role("textbox", name="Пароль")
        pass_box.click()
        time.sleep(random.uniform(0.3, 0.7))
        slow_type(pass_box, password)
        time.sleep(random.uniform(0.8, 1.5))

        page.get_by_role("button", name="Войти").click()
        print("\nIf a captcha appears — solve it manually.")
        print("Waiting for login to complete (up to 90 seconds)...")

        try:
            page.wait_for_url(lambda url: "/login" not in url, timeout=90000)
        except Exception:
            input("\nStill on login page. Solve captcha manually, then press Enter...")

        time.sleep(3)

        all_cookies = context.cookies()
        session_cookie = next((c for c in all_cookies if c["name"] == "sessionid"), None)

        if not session_cookie:
            print("\nERROR: sessionid not found. Make sure you are fully logged in.")
            browser.close()
            sys.exit(1)

        print(f"\nsessionid: {session_cookie['value'][:20]}...")
        cookies_json = json.dumps(all_cookies)
        browser.close()

    answer = input("\nSave cookies to GitHub Secret TIKTOK_COOKIES? [y/N]: ").strip().lower()
    if answer == "y":
        result = subprocess.run(
            ["gh", "secret", "set", "TIKTOK_COOKIES", "--body", cookies_json],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Saved TIKTOK_COOKIES to GitHub Secrets successfully.")
        else:
            print(f"gh error: {result.stderr}")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    main()
