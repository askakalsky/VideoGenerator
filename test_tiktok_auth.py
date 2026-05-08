"""
Tests TikTok cookie auth without posting anything.
Loads TIKTOK_COOKIES from .env, opens TikTok in a browser with those cookies,
and checks if the user is logged in.
"""

import json
import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()


def main():
    cookies_json = os.environ.get("TIKTOK_COOKIES", "").strip()
    if not cookies_json:
        print("ERROR: TIKTOK_COOKIES not set in .env")
        sys.exit(1)

    cookies = json.loads(cookies_json)
    print(f"Loaded {len(cookies)} cookies")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies(cookies)

        page = context.new_page()
        page.goto("https://www.tiktok.com/", wait_until="networkidle")

        # Check if logged in — profile link appears when authenticated
        logged_in = page.locator('[data-e2e="nav-profile"]').count() > 0

        if logged_in:
            print("\nSUCCESS: TikTok cookies are valid, user is logged in.")
        else:
            print("\nFAILED: Not logged in. Cookies may be expired.")
            print("Run get_tiktok_session.py to refresh them.")

        input("\nPress Enter to close browser...")
        browser.close()


if __name__ == "__main__":
    main()
