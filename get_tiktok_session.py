"""
Logs into TikTok, collects all auth cookies in multiple formats,
saves to .env and GitHub Secrets.

Usage:
    python get_tiktok_session.py
"""

import json
import os
import re
import subprocess
import sys
import time
import random

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TIKTOK_EMAIL = os.environ.get("TIKTOK_EMAIL", "")
TIKTOK_PASSWORD = os.environ.get("TIKTOK_PASSWORD", "")

# Cookies known to matter for TikTok auth
AUTH_COOKIES = {
    "sessionid", "sessionid_ss", "sid_guard", "sid_tt",
    "uid_tt", "uid_tt_ss", "s_v_web_id", "ttwid",
    "tt_csrf_token", "msToken", "passport_csrf_token",
}


def slow_type(element, text: str):
    for char in text:
        element.type(char)
        time.sleep(random.uniform(0.05, 0.18))


def cookies_to_netscape(cookies: list) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", ".tiktok.com")
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expires", 0) or 0)
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
    return "\n".join(lines)


def save_to_env(key: str, value: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        if f"{key}=" in content:
            content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
        else:
            content += f"\n{key}={value}\n"
    else:
        content = f"{key}={value}\n"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)


def save_to_gh(key: str, value: str):
    result = subprocess.run(
        ["gh", "secret", "set", key, "--body", value],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ GitHub Secret {key} saved")
    else:
        print(f"  ✗ gh error for {key}: {result.stderr.strip()}")


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
        print("\nSolve captcha or enter verification code if needed.")
        print("Waiting for login (up to 120 seconds)...")

        try:
            page.wait_for_url(lambda url: "/login" not in url, timeout=120000)
        except Exception:
            input("\nStill on login page. Complete login manually, then press Enter...")

        time.sleep(3)

        all_cookies = context.cookies()
        browser.close()

    # Summary
    found = {c["name"]: c["value"] for c in all_cookies if c["name"] in AUTH_COOKIES}
    print(f"\nCollected {len(all_cookies)} total cookies")
    print(f"Auth cookies found: {list(found.keys())}")

    session_id = found.get("sessionid", "")
    if not session_id:
        print("ERROR: sessionid not found — login may have failed.")
        sys.exit(1)

    cookies_json = json.dumps(all_cookies)
    cookies_netscape = cookies_to_netscape(all_cookies)

    # Save to .env
    save_to_env("TIKTOK_COOKIES", cookies_json)
    save_to_env("TIKTOK_SESSION_ID", session_id)
    print("Saved TIKTOK_COOKIES and TIKTOK_SESSION_ID to .env")

    # Save Netscape format locally for tiktok-uploader
    netscape_path = os.path.join(os.path.dirname(__file__), "tiktok_cookies.txt")
    with open(netscape_path, "w", encoding="utf-8") as f:
        f.write(cookies_netscape)
    print(f"Saved Netscape cookies to {netscape_path}")

    # Save to GitHub Secrets
    answer = input("\nSave to GitHub Secrets? [y/N]: ").strip().lower()
    if answer == "y":
        save_to_gh("TIKTOK_COOKIES", cookies_json)
        save_to_gh("TIKTOK_SESSION_ID", session_id)


if __name__ == "__main__":
    main()
